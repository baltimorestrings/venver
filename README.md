# What is this

This is a simple script that uses pip and python installed on the system to ease wiping and recreating a venv.

It expects to be run in a repo folder. 

It also expects "src" style directory

It will install your package with the setup.cfg extras header "test", but others can be specified in setup.cfg.

If anyone besides me uses this and wants it, the default can easily shift to "no extras"

It will:

- Clear all `__pycache__` folders in src folder.
- Make a venv with the provided name/location and python type
- If not given a type, will default to python3.6
- If not given a location, will default to v{number} in repo root
- Install "test" and any other extras it sees in optional "venver" section of setup.cfg


so:

### Specifying Python version

```bash
snmp_sim (master %=)> venver
VENVER: Repo root: '/Users/bemore/snmp_sim'
VENVER: Will be making a venv with '/Library/Frameworks/Python.framework/Versions/3.6/bin/python3.6' at 'v6'
VENVER: checking and clearing pycaches: done
VEVNER: running `/Library/Frameworks/Python.framework/Versions/3.6/bin/python3.6 -m venv v6`
VEVNER: running `/Library/Frameworks/Python.framework/Versions/3.6/bin/python3.6 -m pip install --upgrade pip`
Looking in indexes: https://edge.artifactory.ouroath.com:4443/artifactory/api/pypi/pypi-mirror/simple
Requirement already satisfied: pip in /Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages (21.3.1)
VEVNER: running `/Library/Frameworks/Python.framework/Versions/3.6/bin/python3.6 -m pip install  /Users/bemore/snmp_sim[test]`
```

will make a venv in a folder called v6, upgrade pip, clear caches, install itself into the venv with extras
addon `test`

For additional requirements from setup.cfg, just define a section called "venver" and provide a comma separated list of `extras`

This example is four ways you can specify python3.8. Since I don't supply a venv location, these would
all be created in a folder called "v8"

I am running it deep in the repo, but the script will find the repo source and work off there.

```bash
some_repo/src/folder> venver python38
some_repo/src/folder> venver py38
some_repo/src/folder> venver 3.8
some_repo/src/folder> venver python3.8

# actual output
snmp_sim (master %=)> venver 38
VENVER: Repo root: '/Users/bemore/snmp_sim'
VENVER: Will be making a venv with '/usr/local/bin/python3.8' at 'v8'
VENVER: checking and clearing pycaches: done
VEVNER: running `/usr/local/bin/python3.8 -m venv v8`
```

All four of those will do the same thing

### Specifying Venv location

In this one, I specify I want a venv one folder above the source repo. 

You can see I've specified the extra `core_open_source` in my setup.cfg

```bash
plugins_official> venver 38 ../venv
VENVER: Repo root: '/Users/bemore/plugins_official'
VENVER: Will be making a venv with '/usr/local/bin/python3.8' at '../venv'
VENVER: checking and clearing pycaches: done
VENVER: Found existing venv at destination directory, will delete... done.
VEVNER: running `/usr/local/bin/python3.8 -m venv ../venv`
VEVNER: running `/usr/local/bin/python3.8 -m pip install  /Users/bemore/plugins_official[core_open_source,test]`
```

this one just wants a different venv name:

```bash
plugins_official> venver 3.8 virtual_environment_folder
```

you get the idea
