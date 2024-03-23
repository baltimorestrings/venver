# What Is This

#### Description

This is a simple script that uses pip and python installed on the system to ease wiping and recreating a venv.

It expects to be run in a repo folder. 

It also expects "src" style directory

It will install your package with the setup.cfg extras header "test", but others can be specified in setup.cfg.

If anyone besides me uses this and wants it, the default can easily shift to "no extras"

**This is old. I have since uploaded it to pip, but it is still usable without any pip installs via the following:**

I use it like so:

```bash
curl -s https://github.com/baltimorestrings/venver/blob/main/src/baltimorestrings/venver/_venver.py | python3 -
```

No need to install, it's just a simple script I find useful and benefit from keeping simple (and not needing to re-pull every time I tweak.

**But if you want to install:**

```bash
> pip install baltimorestrings.venver
```

If you pip install, then you can run it via the command `venver


#### What it Will Do:

- Clear all `__pycache__` folders in src folder.
- Make a venv with the provided name/location and python type
- If not given a type, will default to python3.6
- If not given a location, will default to v{number} in repo root
- Install "test" and any other extras it sees in optional "venver" section of setup.cfg

#### Help Mode

Run with flag `--help` to see help:

```bash
[localhost]:~> venver --help
usage: venver [-h] [--edit] [python_version] [venv_destination]

A simple venv utility to rapidly reset repo venvs

positional arguments:
  python_version    Python version: defaults to 3.8. Can be specified a few
                    different ways including:py36, 3.6, 6, 8, python311,
                    py3.8, etc
  venv_destination  Where to make the venv. If not supplied, will make a venv
                    in the repo root called v#, where # is the minor version
                    number (3, 8, 11)

optional arguments:
  -h, --help        show this help message and exit
  --edit, -E, -e    If enabled, pip install --edit will be used (the installed
                    venv will use .pth files in site-packages, and the actual
                    source repo files will be used
```
---

### Specifying Python version

#### What Python Executable Will It Use?
venver will search the environment for the right executable to make the venv with. 

If it doesn't find one matching the version specified, it will call python3 --version and see if that matches.

once the venv is created with the right version, it doesn't matter what python made it, so this script
expects the executable to be supplied and will alarm if it doesn't see one:

#### Edit Mode

pip edit mode is cool. 

Just supply the flag `--edit`, `-e`, or `-E` and the venv built will be in edit mode. 

You can edit the code in your repo, but running it from the venv will update, since setuptools just
places a .pth file in the site-packages dir to redirect to the folder
([More Here] (https://setuptools.pypa.io/en/latest/userguide/development_mode.html))

Note that if you make changes to scripts, you'll need to reinstall, and probably  wipe caches if you're doing
weird manifest/wheel stuff, hence this script.

#### Examples 

##### Ex: No Suitable Python Interpreter Found
```bash
[localhost] new_tests (src_structure %=)> venver 3.10
Failed. VENVER: OSError encountered:
Couldn't find a suitable executable for python3.10 to make a venv with
[localhost] new_tests (src_structure %=)> venver 10
Failed. VENVER: OSError encountered:
Couldn't find a suitable executable for python3.10 to make a venv with
```


Running without arguments will make a v3.6 venv in a folder called "v6" at repo base:

##### Ex: Running With No Arguments
```bash
[localhost]:some_repo (master *=)> venver
VENVER: checking and clearing pycaches: ..............................................done
VENVER: Repo root: '/Users/bemore/zcode/some_repo'
VENVER: Will be using'/Library/Frameworks/Python.framework/Versions/3.6/bin/python3.6' to make venv at'v6'
VEVNER: running `python3.6 -m venv v6`
VEVNER: running `v6/bin/python3 -m pip install --upgrade pip`
VEVNER: running `v6/bin/python3 -m pip install  /Users/bemore/zcode/panoptes/panoptes_framework[test]
```


Note that it installs with pip install `<repo>[test]` - that is the default testing addon we use.

For additional requirements from setup.cfg, just define a section called "venver" and provide a comma separated list of `extras`

This next example is four ways you can specify python3.8. Since I don't supply a venv location, these would
all be created in a folder called "v8"

I am running it deep in the repo, but the script will find the repo source and work off there.

##### Ex: Running At Non-Base Location, Different Phrasing
```bash
[localhost] some_repo/src/folder> venver python38
[localhost] some_repo/src/folder> venver py38
[localhost] some_repo/src/folder> venver 3.8
[localhost] some_repo/src/folder> venver python3.8

# actual output
[localhost] pb_python (main *+%=)> venver py38
VENVER: Repo root: '/Users/bemore/zcode/me/pb_python'
VENVER: Will be making a venv with '/usr/local/bin/python3.8' at 'v8'
VENVER: checking and clearing pycaches: ....done
VENVER: Found existing venv at destination directory, will delete... done.
VEVNER: running `/usr/local/bin/python3.8 -m venv v8`
VEVNER: running `v8/bin/python3.8 -m pip install --upgrade pip`
VEVNER: running `v8/bin/python3.8 -m pip install  /Users/bemore/zcode/me/pb_python[test]`
```

All four of those will do the same thing

---

### Specifying Venv location

##### How to Create Venvs not at Root
In this one, I specify I want a venv one folder above the source repo. 

You can see I've specified the extra `core_open_source` in my setup.cfg

##### Ex: Specifying custom location
```bash
[localhost] plugins_official> venver 38 ../venv
VENVER: Repo root: '/Users/bemore/plugins_official'
VENVER: Will be making a venv with '/usr/local/bin/python3.8' at '../venv'
VENVER: checking and clearing pycaches: done
VENVER: Found existing venv at destination directory, will delete... done.
VEVNER: running `/usr/local/bin/python3.8 -m venv ../venv`
VEVNER: running `../venv/bin/python3.8 -m pip install  /Users/bemore/plugins_official[core_open_source,test]`
```

this one just wants a different venv name:

```bash
[localhost] plugins_official> venver 3.8 virtual_environment_folder
```

you get the idea

----

## Why Isnt This on PyPI / Doesn't it Support Poetry / Can you Add X

This is a script, not a program. It's written like one and it works like one. 

It is designed to be run directly, or via `curl <raw.github path to venver.py> | python3 - ` in a little wrapper.

It does not aim to wrap or obfuscate or add to the basic setuptools venv capability, there are far too
many of those already (see: below). It is just a convenience script that works solely with 
pip's capabilities. I don't know what a poetry is and plan on trying to maintain that, for no particular reason
at all.

<p align="center" width="100%">
<img src="https://imgs.xkcd.com/comics/standards.png" height=150 alt="XKDC: Standards"></img>
</p>

I'd be happy to add X if anyone ever actually wants, with the single precondition:

**As long as it can be added without interfering with the simple, no-arg functionality**

If it complies, I'm literally always happy to do so. This is mostly up because I'm practicing my markdown, hence simple script being way over-explained
