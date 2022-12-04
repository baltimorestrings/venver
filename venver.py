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
    4) Makes a venv, upgrades pip, installs repo in venv with extra [test]
    5) Also installs any other extras it finds by looking in setup.cfg section "venver", key "extras" - expects a comma separated list
"""
import sys
from typing import List
from configparser import ConfigParser
from argparse import ArgumentParser, Namespace
from subprocess import run, PIPE, STDOUT
from shutil import rmtree
from pathlib import Path

REPO_DEFINING_FILENAMES = ["setup.cfg", "src"]
"""For now, this only works on src style repos. """

SUPPORTED_PYTHON_VERSIONS = ["6", "8", "10", "11"]
""" I only need these 3"""

DEFAULT_EXTRAS = ["test"]
""" pip install blah[test] - installs testing requirements """


def main():
    """Script entry point, just calls smaller task functions"""
    args = setup_and_process_args()
    try:
        # traverse up folders until we find a repo root
        repo_root: Path = _get_repo_root()

        # find a valid python executable to use
        py_cmd: Path = _get_python_executable(args.python_version)

        # generate location for venv if not provided
        venv_location = args.venv_destination
        if not venv_location:
            venv_location = f"v{_sanitize_python_name(py_cmd.name)}"
        venv_location = Path(venv_location)

        print(f"VENVER: Repo root: '{repo_root}'")
        print(f"VENVER: Will be making a venv with '{py_cmd}' at '{venv_location}'")

        # clear pycaches in reporoot/src
        _clear_caches(repo_root)

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


def _venv_build(
    py_cmd: Path,
    venv_location: Path,
    repo_root: Path,
    pip_extras: List[str],
    edit_flag: bool,
):
    """Actually builds the venv

    Args:
        py_cmd (Path): full path to a python executable we'll call to create venv
        venv_location (Path): full path to where new venv should go
        repo_root (Path): full path to the repo folder to install from
        pip_extras (List[str]): array of pip extras to supply to the pip install step (pip install <package>[test,etc])
        edit_flag (bool): if enabled, pip will install in --edit mode (site-packages gets a .pth file to redirect to the actual source folder)
    """
    venv_create_cmd = f"{py_cmd} -m venv {venv_location}"
    venv_create_cmd_shortened = venv_create_cmd.replace(str(py_cmd), str(py_cmd.name))
    pip_upgrade_cmd = f"{py_cmd} -m pip install --upgrade pip"
    pip_upgrade_cmd_shortened = pip_upgrade_cmd.replace(str(py_cmd), str(py_cmd.name))

    # build our edit/pip submodule phrasing
    edit_flag = "  --edit  " if edit_flag else ""
    extras_phrase = ""
    extra_packages = set(pip_extras + DEFAULT_EXTRAS)
    if extra_packages:
        extras_phrase = "[" + ",".join(extra_packages) + "]"

    install_package_cmd = (
        f"{py_cmd} -m pip install {edit_flag} {repo_root}{extras_phrase}"
    )
    install_package_cmd_shortened = install_package_cmd.replace(str(py_cmd), str(py_cmd.name))

    print(f"VEVNER: running `{venv_create_cmd_shortened}`")
    _run_pass_output(venv_create_cmd)

    print(f"VEVNER: running `{pip_upgrade_cmd_shortened}`")
    _run_silent(pip_upgrade_cmd)

    print(f"VEVNER: running `{install_package_cmd_shortened}`")
    _run_pass_output(install_package_cmd)


def _run_silent(cmd: str):
    """Runs provided string in bash silently with a 2>&1 (captures stderr as stdout), returns text"""
    return run(cmd.split(), stderr=STDOUT, stdout=PIPE).stdout.decode()


def _run_pass_output(cmd: str):
    """Just runs cmd and lets output print"""
    return run(cmd.split())


def setup_and_process_args() -> Namespace:
    """CLI processing"""
    argparser = ArgumentParserDisplayHelpOnError(
        prog=__file__, description="A simple venv utility to rapidly reset repo venvs"
    )
    argparser.add_argument(
        "python_version",
        nargs="?",
        default="3.6",
        help=(
            "Python version: defaults to 3.6. Can be specified a few different ways including:"
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


def _sanitize_python_name(ver: str):
    """Turns all versions of python3 names down to just the non 3.

    Currently don't support sub-versions because I don't need to, but can be added
    """
    return ver.strip("python").strip("py").strip("3").replace(".", "")


def is_repo_root(path: Path) -> bool:
    """Check if provided Path is a repo root"""
    if all(len(list(path.glob(filename))) >= 1 for filename in REPO_DEFINING_FILENAMES):
        return True
    return False


def _get_python_executable(ver: str):
    """Tries its best to get a python executable for a string.

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


def _clear_caches(repo_root: Path):
    """Just a simple `find $REPO_ROOT/src -name "__pycache__" --type d -delete`, but in python"""
    print("VENVER: checking and clearing pycaches: ", end="")
    caches = list(repo_root.glob("src/**/__pycache__"))
    for file in caches:
        print(".", end="")
        rmtree(file)
    print("done")


def _check_and_clear_existing_venv(venv_location: Path):
    """If it sees a folder at venv_location, deletes it"""
    if venv_location.exists() and venv_location.is_dir():
        print(
            f"VENVER: Found existing venv at destination directory, will delete...",
            end="",
        )
        rmtree(venv_location)
        print(" done.")


def _process_setup_cfg(repo_root: Path) -> Path:
    """Look in repo_root/setup.cfg for a section "venver" with key "extras", returns list"""
    extras = []
    cfg = ConfigParser()
    with open(str(repo_root / "setup.cfg"), "r") as setup_cfg:
        cfg.read_file(setup_cfg)

    try:
        extras += cfg["venver"]["extras"].split(",")

    except KeyError:
        # no config specified
        pass
    return extras


def _die(msg: str):
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
