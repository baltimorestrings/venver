#!/usr/bin/env python3
"""
The venver.

This script is meant to be run in a venv and optionally provided with a python version and a venv location

It pretty much does what tox does, for anyone like me that works out of --edit mode and likes running tests manually.

Run it with --help for a full argument explanation.

This is something I found myself doing relatively often, so it is opinionated and it just kinda does stuff.

It expects a "src" driven source directory - which is good for a bunch of reasons, but if anyone ever wants to use this who doesn't like that,
it's easy enough to add a flag and expose a setup.cfg directive, just ask.

Things it does:
    1) Recurses up from wherever it is called and finds the repo root
    2) Clears all __pycache__ folders in the actual source - this can be helpful when pip --edit caches get stuck in a few different wheel building situations
    3) Deletes any venv it finds at the provided or default location
    4) Makes a venv at repo base unless a path including "/" is provided, upgrades pip, installs repo in venv with extra [test]
    5) Also installs any other extras it finds by looking in setup.cfg section "venver", key "extras" - expects a comma separated list
"""
import os
import sys
from typing import List, Iterable
from configparser import ConfigParser
from argparse import ArgumentParser, Namespace
from subprocess import run, PIPE, STDOUT
from shutil import rmtree
from pathlib import Path

has_tomli = False

try:
    import tomli
    has_tomli = True
except ImportError:
    print("VENVER: warning: running without ability to process venver extras from toml files. install in venv with tomli if that is needed")

REPO_DEFINING_FILENAMES = ["pyproject.toml", ".git"]
"""Files whose presence confirm we're at a repo root. """

SUPPORTED_PYTHON_VERSIONS = ["6", "8", "10", "11"]
""" We still support 6 for now"""

DEFAULT_EXTRAS = ["test"]
""" pip install blah[test] - installs testing requirements """


def main():
    """Script entry point, just calls smaller task functions"""
    args = setup_and_process_args()

    exit_if_in_venv()

    try:
        # traverse up folders until we find a repo root
        repo_root: Path = _get_repo_root()

        # find a valid python executable to use
        py_cmd: Path = _get_python_executable(args.python_version)

        # generate location for venv if not provided
        venv_location = args.venv_destination
        if not venv_location:
            venv_location = f"{repo_root}/v{_sanitize_python_name(py_cmd.name)}"
        venv_location = Path(venv_location)

        # clear pycaches in reporoot/src
        _clear_caches_and_build_dir(repo_root)


        print(f"VENVER: Repo root: '{repo_root}'")
        print(f"VENVER: Will be using'{py_cmd}' to make venv at'{venv_location}'")

        # delete anything that already exists at the future venv loation
        _check_and_clear_existing_venv(venv_location)

        # load any extras from pyproject.toml
        pip_extras = _process_setup_cfg(repo_root)

        # create and set up our venv, passing along all output from pip:
        _venv_build(
            py_cmd=py_cmd,
            venv_location=venv_location,
            repo_root=repo_root,
            edit_flag=args.edit,
            pip_extras=pip_extras,
        )

    except Exception as e:
        _die(f"VENVER: {type(e).__name__} encountered:  \n{e}")

def exit_if_in_venv():
    if os.environ.get("VIRTUAL_ENV"):
        _die(f"Please exit virtualenv by running \"deactivate\" before running the venver")


def _venv_build(
    py_cmd: Path,
    venv_location: Path,
    repo_root: Path,
    pip_extras: Iterable[str],
    edit_flag: bool,
):
    """Actually builds the venv

    Args:
        py_cmd (Path): full path to a python executable we'll call to create venv
        venv_location (Path): full path to where new venv should go
        repo_root (Path): full path to the repo folder to install from
        pip_extras (Iterable[str]): array of pip extras to supply to the pip install step (pip install <package>[test,etc])
        edit_flag (bool): if enabled, pip will install in --edit mode (site-packages gets a .pth file to redirect to the actual source folder)
    """
    venv_create_cmd = f"{py_cmd} -m venv {venv_location}"
    venv_create_cmd_shortened = venv_create_cmd.replace(str(py_cmd), str(py_cmd.name))

    py_in_venv_cmd = Path(f"{venv_location}/bin/python3")
    pip_upgrade_cmd = f"{py_in_venv_cmd} -m pip install --upgrade pip"

    # build our edit/pip submodule phrasing
    edit_flag = "  --edit  " if edit_flag else ""
    extras_phrase = ""
    extra_packages = set(pip_extras + DEFAULT_EXTRAS)
    if extra_packages:
        extras_phrase = "[" + ",".join(extra_packages) + "]"

    install_package_cmd = (
        f"{py_in_venv_cmd} -m pip install {edit_flag} {repo_root}{extras_phrase}"
    )

    print(f"VENVER: running `{venv_create_cmd_shortened}`")
    _run_pass_output(venv_create_cmd)

    print(f"VENVER: running `{pip_upgrade_cmd}`")
    _run_silent(pip_upgrade_cmd)

    print(f"VENVER: running `{install_package_cmd}`")
    _run_pass_output(install_package_cmd)


def _run_silent(cmd: str) -> str:
    """Runs provided string in bash silently with a 2>&1 (captures stderr as stdout), returns text

    Returns:
        str - the output
    """
    return run(cmd.split(), stderr=STDOUT, stdout=PIPE).stdout.decode()


def _run_pass_output(cmd: str):
    """Just runs cmd and lets output print"""
    return run(cmd.split())


def setup_and_process_args() -> Namespace:
    """CLI processing"""
    argparser = ArgumentParserDisplayHelpOnError(
        prog=Path(__file__).name,
        description="A simple venv utility to rapidly reset repo venvs"
    )
    argparser.add_argument(
        "python_version",
        nargs="?",
        default="3.8",
        help=(
            "Python version: defaults to 3.8. Can be specified a few different ways including:"
            "py36, 3.6, 6, 8, python311, py3.8, etc"
        ),
    )
    argparser.add_argument(
        "venv_destination",
        nargs="?",
        help=(
            "Where to make the venv. If not supplied, will make a venv in the repo root"
            " called v#, where # is the minor version number (3, 8, 11)"
        ),
    )
    argparser.add_argument(
        "--edit",
        "-E",
        "-e",
        action="store_true",
        help=(
            "If enabled, pip install --edit will be used (the installed venv will use .pth"
            " files in site-packages, and the actual source repo files will be used"
        ),
    )
    args = argparser.parse_args()
    return args


def _get_repo_root() -> Path:
    """Recurse up from working directory if needed until we're in a repo root, returns Path of such

    Returns:
        Path - the root of the repo

    Raises:
        OSError if it runs out of "up" to recurse through
    """

    current_location = Path.cwd().expanduser().resolve()
    directory_cursor = current_location

    while not is_repo_root(directory_cursor) and str(directory_cursor) != "/":
        directory_cursor = directory_cursor.parent

    if str(directory_cursor) == "/":
        raise OSError(
            f"Couldn't find a repo at or above current location ({current_location}. Script must be run from within a repo"
        )
    return directory_cursor


def _sanitize_python_name(ver: str) -> str:
    """Turns all versions of python3 names down to just the non 3.

    Currently don't support sub-versions because I don't need to, but can be added

    Examples:
        "python38" -> "8"
        "py3.9" -> "9"
        "python2.7" -> "27" (will be rejected by the validator since it starts with 2)
        "36" -> "6"
    """
    return ver.strip("python").strip("py").strip("3").replace(".", "")


def is_repo_root(path: Path) -> bool:
    """Check if provided Path is a repo root"""
    if all(len(list(path.glob(filename))) >= 1 for filename in REPO_DEFINING_FILENAMES):
        return True
    return False


def _get_python_executable(ver: str) -> Path:
    """Tries its best to get a python executable for a string.

    Returns:
        Path - representing full path to valid python executable

    Raises:
        OSError - if it can't find a valid python

    Understands:
        'python38', 'py38', '38', '8', '3', 'py36', etc

    """
    # first, strip our input down to just the non 3 part, IE python3.8 becomes "8"
    sanitized_ver = _sanitize_python_name(ver)

    # check if we support this version
    if sanitized_ver not in SUPPORTED_PYTHON_VERSIONS:
        raise ValueError(f"Couldn't get supported python version out of '{ver}'")

    # we'll check the env for python3.#
    py_exec_name = "python3." + sanitized_ver

    try_full_name = _run_silent("which " + py_exec_name).strip()

    if try_full_name:
        return Path(try_full_name)
    else:
        # if that doesn't work, check if environment python3 matches the ver we want
        try_backup = _run_silent("python3 --version").strip()
        if "3.{sanitized_ver}" in try_backup:
            return Path(try_backup)
    raise OSError(
        f"Couldn't find a suitable executable for {py_exec_name} to make a venv with"
    )


def _clear_caches_and_build_dir(repo_root: Path):
    """Just a simple `find $REPO_ROOT/src -name "__pycache__" --type d -delete`, but in python"""
    print("VENVER: checking and clearing pycaches: ", end="")
    caches = list(repo_root.glob("src/**/__pycache__"))
    for file in caches:
        print(".", end="")
        rmtree(file)
    print("done")
    build_cache_dir = Path(repo_root, "build")
    if build_cache_dir.exists() and build_cache_dir.is_dir():
        print("VENVER: deleting repo_root/build (setuptools wheel caching)")
        rmtree(str(Path(repo_root, "build")))

def _is_venv_dir(possible_venv_location: Path) -> bool:
    """Accepts Path, returns "yes" if there's a bin/activate and a bin/python in it, IE it's a venv """
    return all((
            Path(possible_venv_location, "bin").is_dir(),
            Path(possible_venv_location, "lib").is_dir(),
            Path(possible_venv_location, "bin", "python").is_file(),
            Path(possible_venv_location, "bin", "activate").is_file()
    ))

def _check_and_clear_existing_venv(venv_location: Path):
    """If it sees a folder at venv_location, deletes it"""
    if venv_location.exists():
        if venv_location.is_dir() and _is_venv_dir(venv_location):
            print(
                f"VENVER: Found existing venv at destination directory, will delete...",
                end="",
            )
            rmtree(venv_location)
            print(" done.")
        else:
            raise OSError(f"Found an already existing file/folder at provided target '{venv_location}', and"
                          " it doesn't look like a venv."
            )


def _process_setup_cfg(repo_root: Path) -> Iterable[str]:
    """Look in repo_root/setup.cfg for a section "venver" with key "extras", returns list

    Returns:
        Iterable[str] representing additional pip "extras" IE pip install <reponame>[extras]
    """
    extras = []
    if (repo_root / "setup.cfg").exists():
        cfg = ConfigParser()
        with open(str(repo_root / "setup.cfg"), "r") as setup_cfg:
            cfg.read_file(setup_cfg)
    
        try:
            extras += cfg["venver"]["extras"].split(",")
    
        except KeyError:
            # no config specified
            pass
    if has_tomli and (repo_root / "pyproject.toml").exists():
        with open(str(repo_root / "pyproject.toml"), "rb") as pp_toml:
            data = tomli.load(pp_toml)
            if "venver" in data and "extras" in data["venver"] and isinstance(data["venver"]["extras"], Iterable):
                extras += data["venver"]["extras"]
            elif "venver" in data and "extras" in data["venver"]["extras"]:
                raise ValueError("pyproject.toml invalid venver extras config detected, must be array")


    return extras


def _die(msg: str):
    """Dead"""
    print(f"Failed. {msg}")
    sys.exit(1)


class ArgumentParserDisplayHelpOnError(ArgumentParser):
    """Convenience class, will display the full help if it encounters an error """
    def error(self, message: str) -> str:
        line = ("-" * 50) + "\n"
        sys.stderr.write(f"{line}Error: {message}\n{line}")
        self.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
