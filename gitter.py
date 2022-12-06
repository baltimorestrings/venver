from typing import *
from dataclasses import dataclass
from pathlib import Path
import sys

@dataclass
class RepoTarget:
    path: str
    repo: str

def _die(msg: str, returncode: int = 1):
    print(msg)
    sys.exit(returncode)

def _process_args() -> Path:
    """Return a valid path target """
    if len(sys.argv) < 2:
        _die("need a folder target")
    if (path := Path(sys.argv[1]).resolve()).is_dir():
        return path
    _die("path needs to exist")

def _trim_path(target_path: Path) -> Path:
    # record how many folders deep from / we are
    working_dir_length = len(Path.cwd().parts)
    # pop that many off the absolute path of our target
    target_path_absolute = target_path.parent.parent.resolve()
    return Path(*target_path_absolute.parts[working_dir_length:])
    
def _get_list_of_targets(target_folder: Path) -> List[RepoTarget]:
    repos: List[RepoTarget] = []
    for config in target_folder.glob("**/.git/config"):
        with open(str(config), "r") as git_config:
            lines = git_config.readlines()
            i = 0
            while "origin" not in lines[i]:
                i += 1
            while "url" not in lines[i]:
                i += 1
        repo_folder = _trim_path(config)
        repo_url = lines[i].split("=")[1].strip()
        repos.append(RepoTarget(repo_folder, repo_url))
    return repos

def _ensure_folders_and_generate_git_commands(repos: List[RepoTarget]):
    parent_folders = set(repo.path for repo in repos)
    for folder in parent_folders:
        print(f"mkdir -p {folder} &>/dev/null")
    for repo in repos:
        print(f"git clone {repo.repo} {repo.path}")



def main():
    target_folder = _process_args()

    try:
        repos: List[RepoTarget] = _get_list_of_targets(target_folder)
    except Exception as e:
        phrase = "couldn't find valid remote origin" if type(e) == KeyError else repr(e)
        die("error processing " + config + ": " + phrase)
    _ensure_folders_and_generate_git_commands(repos)







if "__main__" == __name__: main()
