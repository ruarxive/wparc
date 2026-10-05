# Installation

## From PyPI

```bash
pip install wparc
```

The only runtime dependencies are `typer`, `pyyaml`, `requests`, and
`urllib3`. Python 3.8 or newer is required.

## From source

```bash
git clone https://github.com/ruarxive/wparc.git
cd wparc
pip install -e ".[dev]"
```

The `[dev]` extra pulls in `pytest`, `tox`, `black`, `flake8`, `mypy`,
and friends.

## Verifying the install

```bash
wparc --help
python -m wparc --help
```

Both invocations should print the same help screen.

## Requirements

- Python ≥ 3.8
- ~5 MB of disk space
- Network access to the target WordPress site