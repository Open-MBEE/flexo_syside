# flexo_syside

This repository provide a SysIDE based library to serialize SysMLv2 textual notatation as file or string so, it can
be committed to OpenMBEE Flexo SysML v2 repository.
It also provides functions to deserialiize Flexo respomses in JSON to SySIDE python objects, that are then accessible by API or SysML v2 textual notation.

Look at examples/basic_notebook.ipynb for how to use the API

It uses [SysML v2 Python client][https://github.com/Open-MBEE/sysmlv2-python-client] to access SysML v2 models with the standard API and has been tested
with [OpenMBEE Flexo][https://openmbee.atlassian.net/wiki/x/AYAeEw]

You can install Flexo easily yourself using docker compose:
[Flexo MMS SysML v2 Microservice][https://github.com/Open-MBEE/flexo-mms-sysmlv2/tree/develop/docker-compose]
[Flexo MMS docker-compose][https://github.com/Open-MBEE/flexo-mms-deployment/tree/develop/docker-compose]


## Installation

```bash
pip install .

Check requirements.txt for dependencies

## Installation

This package depends on [sysmlv2-python-client](https://github.com/Open-MBEE/sysmlv2-python-client), which is **not available on PyPI** and must be installed directly from GitHub.

It also depends on sysIDE automator library: https://sensmetry.com/syside/

### Recommended install (development or production):

```bash
pip install syside-license syside --index-url https://gitlab.com/api/v4/projects/69960816/packages/pypi/simple --upgrade
pip install -e .
