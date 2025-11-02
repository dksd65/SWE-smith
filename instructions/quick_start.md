# Quick Start for Python Repositories

A revised version without conda. Using pandas repository as an example.

## Build environment

Create venv for swesmith
```bash
python3 -m venv venv_swesmith
source venv_swesmith/bin/activate
pip install --upgrade pip 
pip install -e .
```

Create script to install repository:
```bash
python -m swesmith.build_repo.try_install_py pandas-dev/pandas install_py_repo_venv.sh --commit latest --no_cleanup
```

This creates: `logs/build_images/env/pandas-dev__pandas.8f359f8e/requirements_pandas-dev__pandas.8f359f8e.txt`

Update `profiles/python.py` with the repository commit to be created. For pandas, need to handle build dependencies and test dependencies. Example:
```python
@dataclass
class Pandas8f359f8e(PythonProfile):
    owner: str = "pandas-dev"
    repo: str = "pandas"
    commit: str = "8f359f8e"  # Short commit hash - will be resolved to full hash
    install_cmds: list = field(
        default_factory=lambda: [
            # Build backend and tools (required for --no-build-isolation)
            "pip install meson-python meson ninja 'versioneer[toml]' cython numpy",
            # Remove pyarrow if present (optional dependency causing version check issues)
            "pip uninstall -y pyarrow || true",
            "python -m pip install -ve . --no-build-isolation -Ceditable-verbose=true",
            # Install test dependencies (hypothesis is required by conftest.py)
            "pip install pytest 'hypothesis>=6.116.0' pytest-xdist",
        ]
    )
```

**Note:** The build script automatically handles:
- Cloning from mirror (or original repo if mirror doesn't exist)
- Fetching git tags from upstream (needed for versioneer, since mirror has no git history)
- Creating venv and installing requirements

Build the image using registered profile:
```
python -m swesmith.build_repo.create_images \
  --profiles mssun65/swesmith.arm64.pandas-dev_1776_pandas.8f359f8e \
  -y
```

Verify the image works:
```bash
# Note: When using bash -c, you need to activate venv manually
# But in interactive mode (docker run -it), venv auto-activates via .bashrc
docker run --rm mssun65/swesmith.arm64.pandas-dev_1776_pandas.8f359f8e bash -c "source /venv/testbed/bin/activate && python -c 'import pandas as pd; print(f\"Pandas version: {pd.__version__}\"); print(\"✓ Pandas imported successfully!\")'"

# Test pandas functionality
docker run --rm mssun65/swesmith.arm64.pandas-dev_1776_pandas.8f359f8e \
  bash -c "source /venv/testbed/bin/activate && python -c 'import pandas as pd; df = pd.DataFrame({\"a\": [1, 2, 3]}); print(df)'"
```

(Optional) Push the image to docker hub for future use
```bash
docker push mssun65/swesmith.arm64.pandas-dev_1776_pandas.8f359f8e
```

Verify the docker image can run:
```bash
# Run the docker (venv auto-activates via .bashrc in interactive mode)
docker run -it --rm mssun65/swesmith.arm64.pandas-dev_1776_pandas.8f359f8e

# Inside the container, venv is already activated (you'll see (testbed) in prompt)
# Verify git remote (should point to the mirror repo)
git remote -v

# Run pytest (venv auto-activated, hypothesis and test deps installed)
pytest
```

Changes made:
- Convert from conda to venv: Modified `PythonProfile.build_image()` to use venv instead of conda
- Modified `try_install_py.py` to export `pip freeze` instead of `conda env export`
- Updated `.bashrc` in Docker image to activate venv (instead of conda) 
- Mirror repository creation: Support for GitHub user accounts (not just orgs)
- Use HTTPS cloning for public repositories instead of SSH
- Automatic tag fetching: When using mirror, fetch tags from upstream for versioneer compatibility 

### Troubleshooting

#### Incompatible packages
The `try_install_py.py` script automatically filters out known incompatible packages:
- `pyyaml-ft` (Python 3.13+ only)
- `types-certifi`, `types-toml` (version conflicts)
- `pyarrow` (optional dependency that can cause version check issues with pandas)

If you encounter other incompatible packages, add them to the `incompatible_packages` list in `swesmith/build_repo/try_install_py.py`.

#### Version generation issues
If versioneer reports version as `0+untagged.1.g<commit>`, this is normal when using mirrors. The mirror has no git history, but tags are fetched from upstream during build. Functionality works correctly despite the version string.

#### Missing test dependencies
If `pytest` fails with `ModuleNotFoundError`, check if the repository's `conftest.py` requires optional test dependencies. Add them to the profile's `install_cmds` (e.g., `hypothesis` for pandas).

## Generate bugs

### Procedural modifications

```bash
# In venv_swesmith:
python swesmith/bug_gen/procedural/generate.py pandas-dev__pandas.8f359f8e --max_bugs 100
# note that max_bugs is by modifier, not total bugs
```

This should create a directory in `logs/bug_gen/pandas-dev__pandas.8f359f8e`.
Each bug candidate should have a `.diff` file and a `.json` metafile.

### LM Rewrite
Need API key in .env. For example, `ANTHROPIC_API_KEY=your-api-key`.
```bash
python swesmith/bug_gen/llm/rewrite.py pandas-dev__pandas.8f359f8e --model anthropic/claude-3-7-sonnet-20250219 --config_fil
e configs/bug_gen/lm_rewrite.yml --max_bugs 100
```

It should show progress and files the bugs are written into. Beware of rate limit. 
```
Wrote bug to logs/bug_gen/pandas-dev__pandas.8f359f8e/pandas-dev__pandas.8f359f8e__pandas__core__arrays__timedeltas.py/sequence_to_td64ns_baeb0075/bug__lm_rewrite__95kp07t0.diff
```

## Validate task instances
To see if bug candidates fail the unit tests (i.e. are qualified bugs).

First, collect all .diff files into a single .json file.
```bash
python swesmith/bug_gen/collect_patches.py logs/bug_gen/pandas-dev__pandas.8f359f8e/
```
It should show where the output .json is:
```
Saved 1023 patches to logs/bug_gen/pandas-dev__pandas.8f359f8e_all_patches.json
```

Run the candidates through all tests (can be very time consuming!)
```
python swesmith/harness/valid/py logs/bug_gen/pandas-dev__pandas.8f359f8e_all_patches.json
```

To run only selected instances (added functionality to save time):
```
python -m swesmith.harness.valid logs/bug_gen/pandas-dev__pandas.8f359f8e_all_patches.json --instance_ids "pandas-dev__pandas.8f359f8e.lm_rewrite__95kp07t0"
```

To run through only selected tests:
```bash
python -m swesmith.harness.valid logs/bug_gen/pandas-dev__pandas.8f359f8e_all_patches.json \
  --instance_ids "pandas-dev__pandas.8f359f8e.lm_rewrite__95kp07t0" \
  --test_filter "pandas/tests/arrays/test_timedeltas.py" \
  --redo_existing
# redo existing required to force re-test
```

The result should show number of valid bugs (fail to pass):
```
Validation: 100%|█| 1/1 [00:19<00:00, 19.23s/it, fail=0, timeout=0, 0_f2p=0, 
All instances run.
Total instances: 2
- Timed out: 0
- Collection errors (too broken): 0
- Fail to pass: 0 (0); 1+ (1)
- Other: 0
```

To gather valid bugs and push to mirror repo as branches:
```bash
python -m swesmith.harness.gather logs/run_validation/pandas-dev__pandas.8f359f8e
```

To simply gather valid bugs into a .json file:
```bash
python -m swesmith.harness.simple_gather logs/run_validation/pandas-dev__pandas.8f359f8e
```