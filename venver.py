#!/usr/bin/env python3
import sys
from typing import List
from configparser import ConfigParser
from argparse import ArgumentParser, Namespace
from subprocess import run, PIPE, STDOUT
from shutil import rmtree
from pathlib import Path

REPO_DEFINING_FILENAMES = ["setup.cfg", "src"]
"""For safety, this only works on src style repos. """

SUPPORTED_PYTHON_VERSIONS = ["6", "8", "11"]
""" for now """

DEFAULT_EXTRAS = ["test"]
""" This script is designed to be "drop in and edit", hence the globals. extras may also be added in setup.cfg 'venver':'extras' """


def main():
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


def _run_silent(cmd: str):
    return run(cmd.split(), stderr=STDOUT, stdout=PIPE).stdout.decode()


def _run_pass_output(cmd: str):
    return run(cmd.split())


def setup_and_process_args() -> Namespace:
    argparser = ArgumentParser()
    argparser.add_argument("python_version", nargs="?", default="3.6")
    argparser.add_argument("venv_destination", nargs="?")
    argparser.add_argument("--edit", "-E", "-e", action="store_true")
    args = argparser.parse_args()
    return args


def _get_repo_root() -> Path:
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
    return ver.strip("python").strip("py").strip("3").replace(".", "")


def is_repo_root(path: Path):
    if all(len(list(path.glob(filename))) >= 1 for filename in REPO_DEFINING_FILENAMES):
        return True
    return False


def _get_python_executable(ver: str):

    sanitized_ver = _sanitize_python_name(ver)

    if sanitized_ver not in SUPPORTED_PYTHON_VERSIONS:
        raise ValueError(f"Couldn't get supported python version out of '{ver}'")

    py_exec_name = "python3." + sanitized_ver

    try_full_name = _run_silent("which " + py_exec_name).strip()

    if try_full_name:
        return Path(try_full_name)
    else:
        try_backup = _run_silent("python3 --version").strip()
        if "3.{sanitized_ver}" in try_backup:
            return Path(try_backup)
    raise OSError(
        f"Couldn't find a suitable executable for {py_exec_name} to make a venv with"
    )


def _clear_caches(repo_root: Path):
    print("VENVER: checking and clearing pycaches: ", end="")
    caches = list(repo_root.glob("src/**/__pycache__"))
    for file in caches:
        print(".", end="")
        rmtree(file)
    print("done")


def _check_and_clear_existing_venv(venv_location: Path):
    if venv_location.exists() and venv_location.is_dir():
        print(
            f"VENVER: Found existing venv at destination directory, will delete...",
            end="",
        )
        rmtree(venv_location)
        print(" done.")


def _process_setup_cfg(repo_root: Path) -> Path:
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


def _venv_build(py_cmd: Path,
                venv_location: Path,
                repo_root: Path,
                pip_extras: List[str],
                edit_flag: bool
                ):
    venv_create_cmd = f"{py_cmd} -m venv {venv_location}"
    pip_upgrade_cmd = f"{py_cmd} -m pip install --upgrade pip"

    # build our edit/pip submodule phrasing
    edit_flag = "  --edit  " if edit_flag else ""
    extras_phrase = ""
    extra_packages = set(pip_extras + DEFAULT_EXTRAS)
    if extra_packages:
        extras_phrase = "[" + ",".join(extra_packages) + "]"

    install_package_cmd = f"{py_cmd} -m pip install {edit_flag} {repo_root}{extras_phrase}"

    print(f"VEVNER: running `{venv_create_cmd}`")
    _run_pass_output(venv_create_cmd)

    print(f"VEVNER: running `{pip_upgrade_cmd}`")
    _run_pass_output(pip_upgrade_cmd)

    print(f"VEVNER: running `{install_package_cmd}`")
    _run_pass_output(install_package_cmd)


def _die(msg: str):
    print(f"Failed. {msg}")
    sys.exit(1)


if __name__ == "__main__":
    main()
