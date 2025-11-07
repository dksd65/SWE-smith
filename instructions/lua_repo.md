# Working with Lua Repositories using CustomProfile

This guide explains how to use SWE-smith with Lua repositories (or any custom repository) that have their own Dockerfile. We use **penlight** as the primary example.

## Part 1: Quick Start with penlight

### Prerequisites

1. **Clone penlight repository** (if not already done):
   ```bash
   git clone https://github.com/lunarmodules/penlight.git
   ```

2. **Activate SWE-smith environment**:
   ```bash
   cd SWE-smith
   source venv_swesmith/bin/activate
   ```

### Step 1: Create penlight Profile

First, determine the commit hash you want to use:

```bash
cd penlight
git log -1 --format="%H"
# Example output: bd26cb9e4619489cb1e9e13e282888726527d954
```

Now create a profile in `swesmith/profiles/lua.py`. In this example, we created profile `Penlightbd26cb9`.

You can either:
**Option A: Add to the existing file** (edit `swesmith/profiles/lua.py`):
- If the tests are not located in tests/ directory, then _is_test_path needs to specify the test paths.
- If the test output does not look like pytest style, then log_parser is needed.
- If use custom dockerfile or additional changes applied on top of the last commit, need to make sure the dockerfile clones from the latest mirror repo, so that the changes are reflected.

```python
@dataclass
class PenlightYourCommit(CustomProfile):
    """penlight at specific commit."""
    owner: str = "lunarmodules"
    repo: str = "penlight"
    commit: str = "1234567890abcdef1234567890abcdef12345678"  # Replace with your commit
    
    exts: list[str] = field(default_factory=lambda: [".lua"])
    test_cmd: str = "lua test-runner.lua tests"
    dockerfile_path: str = "Dockerfile"
    dockerfile_modifications: dict[str, str] = field(default_factory=lambda: {
        "WORKDIR /penlight\n\nCOPY lua/ ./lua/\nCOPY tests/ ./tests/": (
            "# Clone penlight repository from mirror\n"
            "RUN git clone https://github.com/lunarmodules/penlight.git /testbed\n"
            "WORKDIR /testbed"
        ),
        "ENV LUA_PATH=\"/penlight/lua/?.lua;/penlight/lua/?/init.lua;;\"": "ENV LUA_PATH=\"/testbed/lua/?.lua;/testbed/lua/?/init.lua;;\"",
    })
    
    def _is_test_path(self, root: str, file: str) -> bool:
        if not file.endswith(".lua"):
            return False
        return "tests/" in root or file.startswith("test_") or file.endswith("_test.lua")

    def log_parser(self, log: str) -> dict[str, str]:
        pass
```

**Option B: Create a standalone profile file** (e.g., `swesmith/profiles/penlight_custom.py`):

```python
from dataclasses import dataclass, field
from swesmith.profiles.custom import CustomProfile
from swesmith.profiles.base import registry

@dataclass
class Penlightbd26cb9(CustomProfile):
    """penlight at commit bd26cb9e..."""
    owner: str = "lunarmodules"
    repo: str = "penlight"
    commit: str = "bd26cb9e4619489cb1e9e13e282888726527d954"
    
    exts: list[str] = field(default_factory=lambda: [".lua"])
    test_cmd: str = "lua test-runner.lua tests"
    dockerfile_path: str = "Dockerfile"
    dockerfile_modifications: dict[str, str] = field(default_factory=lambda: {
        "WORKDIR /penlight\n\nCOPY lua/ ./lua/\nCOPY tests/ ./tests/": (
            "# Clone penlight repository from mirror\n"
            "RUN git clone https://github.com/lunarmodules/penlight.git /testbed\n"
            "WORKDIR /testbed"
        ),
    })

# Register the profile
registry.register_profile(Penlightbd26cb9)
```

Then import it in `swesmith/profiles/__init__.py`:
```python
from . import penlight_custom
```

### Step 2: Create GitHub Mirror from Local Repository

If Dockerfile is added or modified locally (not in the upstream repository), we must manually push the local repository to the mirror before building the image.

Make sure Dockerfile is committed before pushing.

#### Step 2a: Create GitHub mirror repo and push from local

```bash
# Navigate to your local penlight directory with the Dockerfile
cd your/local/path/to/penlight

# Load GitHub token
export $(cat .env | xargs)  # Or: export GITHUB_TOKEN=your_token

# Get the mirror name
python -c "from swesmith.profiles.lua import Penlightbd26cb9; print(Penlightbd26cb9().mirror_name)"
# Output: dksd65/lunarmodules__penlight.bd26cb9e

# Create the GitHub repository (one-time)
python << 'EOF'
from swesmith.profiles.lua import Penlightbd26cb9
profile = Penlightbd26cb9()
try:
    profile.api.repos.create_in_org(profile.org_gh, profile.repo_name)
except:
    profile.api.repos.create_for_authenticated_user(name=profile.repo_name, private=False)
print(f"Created: https://github.com/{profile.mirror_name}")
EOF

# Commit the Dockerfile to git (if not already committed)
# git add Dockerfile .dockerignore
# git commit -m "Add Dockerfile for SWE-smith"

# Push your local repository to the mirror
export $(grep GITHUB_TOKEN /path/to/SWE-smith/.env)
git remote add mirror https://github.com/dksd65/lunarmodules__penlight.bd26cb9e.git
git push -f https://${GITHUB_TOKEN}@github.com/dksd65/lunarmodules__penlight.bd26cb9e.git HEAD:main

# Verify the Dockerfile is in the mirror
# Visit: https://github.com/dksd65/lunarmodules__penlight.bd26cb9e/blob/main/Dockerfile
```

#### Step 2b: Build Docker Image

Now that the mirror contains your Dockerfile, build the image:

```bash
cd SWE-smith
source venv_swesmith/bin/activate
export $(cat .env | grep GITHUB_TOKEN)

# To get name of docker image (to be used in next step)
python -c "
from swesmith.profiles.lua import Penlightbd26cb9
profile = Penlightbd26cb9()
print('Profile name:', profile.__class__.__name__)
print('Image name:', profile.image_name)
print('Mirror name:', profile.mirror_name)
print('Repo name:', profile.repo_name)
"

# Build image (skips mirror creation since it already exists)
python -m swesmith.build_repo.create_images \
  --profiles mssun65/swesmith.arm64.lunarmodules_1776_penlight.bd26cb9e \
  -y
```

This automatically creates the mirror from GitHub and builds the image.

### Step 3: Verify Docker Image

Test that the Docker image works correctly:

```bash
# Get the image name
python -c "
from swesmith.profiles.lua import Penlightbd26cb9
profile = Penlightbd26cb9()
print(profile.image_name)
"

# Run the container
docker run -it --rm mssun65/swesmith.arm64.lunarmodules_1776_penlight.bd26cb9e

# Inside the container, verify penlight works:
cd /testbed
lua --version

# Run tests (this will run all tests)
lua test-runner.lua tests

# Run a specific test
lua test-runner.lua tests/test-tablex.lua
```

### Step 4: Generate Bugs

Now you can generate bugs using SWE-smith's bug generation methods.

#### Method A: Procedural Bug Generation

**Status**: ✅ **Working!** Basic Lua modifiers are functional.

**Implemented Modifiers**:
- `OperationChangeModifier` - Changes operators within categories (`+`↔`-`, `and`↔`or`, `==`↔`~=`)
- `OperationFlipOperatorModifier` - Flips operators to opposites (`+`→`-`, `<`→`>`)
- `OperationChangeConstantsModifier` - Modifies numeric constants (`10`→`11`, `0.5`→`0.6`)

**Files**: `swesmith/bug_gen/procedural/lua/operations.py`

```bash
python -m swesmith.bug_gen.procedural.generate \
  lunarmodules__penlight.bd26cb9e \
  --max_bugs 10
```

**Future additions**: More modifiers can be added (remove assignments, control flow inversion, etc.) following the same pattern.

#### Method B: LLM-based Bug Generation

```bash
python -m swesmith.bug_gen.llm.rewrite \
  lunarmodules__penlight.bd26cb9e \
  --model anthropic/claude-sonnet-4-5-20250929 \
  --config_file configs/bug_gen/lm_rewrite.yml \
  --max_bugs 5 \
  -w 1
  # use 1 worker to avoid rate limit
```

#### Method C: Mirror-based Bug Generation

**⚠️ WARNING: Mirror bug generation currently only supports Python repositories!**

The mirror feature is hardcoded to check for `.py` files and will skip all PRs that don't modify Python files. For Lua repositories (or any non-Python language), all PRs will be skipped with the message "No Python files changed". This is a known limitation that requires code modifications to support other languages. For now, stick with **Procedural** and **LLM-based** bug generation for Lua repositories.

---

**For reference only** (doesn't work for Lua yet):

To use mirror-based method, first need to collect raw PR data from original repository.
```bash
mkdir -p logs/prs/raw

python -m swesmith.bug_gen.mirror.collect.print_pulls \
  lunarmodules/penlight \
  logs/prs/raw/lunarmodules__penlight-pulls.jsonl \
  --max_pulls 100
```

Build PR file into dataset:
```bash
mkdir -p logs/prs/data

python -m swesmith.bug_gen.mirror.collect.build_dataset \
  logs/prs/raw/lunarmodules__penlight-pulls.jsonl \
  logs/prs/data/lunarmodules__penlight-task-instances.jsonl
```
This returns useful information about the PRs.
```
# Total 11 PRs, 9 valid instances were crated, only 1 has test patches (i.e. the PR modified test files, so mirror can validate the bug breaks tests)
[lunarmodules/Penlight] Total instances: 11, completed: 9, with tests: 1
```

Generate mirror bugs with LLM:
```bash
python -m swesmith.bug_gen.mirror.generate \
  logs/prs/data/lunarmodules__penlight-task-instances.jsonl \
  --model anthropic/claude-4-5-sonnet-latest \
  --num_processes 1
```

#### Check bug generation types
We can look at filenames of bugs under logs/bug_gen/
```
cd logs/bug_gen/lunarmodules__penlight.bd26cb9e && echo "=== Bug Count Summary ===" && echo && echo "LLM bugs: $(find . -name 'bug__lm_*.diff' | wc -l | tr -d ' ')" && echo "Procedural bugs: $(find . -name 'bug__func_pm_*.diff' | wc -l | tr -d ' ')" && echo && echo "=== Procedural Breakdown ===" && for pattern in op_change flip_operators op_change_const ctrl_invert_if ctrl_shuffle remove_cond rm_assign remove_loop; do count=$(find . -name "bug__func_pm_*${pattern}*.diff" | wc -l | tr -d ' '); echo "  $pattern: $count"; done
```
It should return counts:
```
=== Bug Count Summary ===

LLM bugs: 10
Procedural bugs: 289

=== Procedural Breakdown ===
  op_change: 80
  flip_operators: 44
  op_change_const: 35
  ctrl_invert_if: 62
  ctrl_shuffle: 28
  remove_cond: 47
  rm_assign: 0
  remove_loop: 28
```

### Step 5: Validate Bugs

Run validation to ensure bugs actually break tests:

```bash
# First collect patches
python -m swesmith.bug_gen.collect_patches logs/bug_gen/lunarmodules__penlight.bd26cb9e/

# Then validate
# Validate all - takes long...
python -m swesmith.harness.valid \
  logs/bug_gen/lunarmodules__penlight.bd26cb9e_all_patches.json

# Validate selected test instances
python -m swesmith.harness.valid \
  logs/bug_gen/lunarmodules__penlight.bd26cb9e_all_patches.json \
  -i lunarmodules__penlight.bd26cb9e.func_pm_ctrl_invert_if__4bguumy7 \
     lunarmodules__penlight.bd26cb9e.func_pm_op_change__qq1yl35v

# Use glob pattern
python -m swesmith.harness.valid \
  logs/bug_gen/lunarmodules__penlight.bd26cb9e_all_patches.json \
  -i "lunarmodules__penlight.bd26cb9e.func_pm_ctrl_invert_if__*"
```

Worth checking the result of validation using the script `validation_summary.sh`:

```bash
./scripts/validation_summary.sh logs/run_validation/lunarmodules__Penlight.bd26cb9e
```
It should return results like this:
```
=== Validation Summary ===

Overall Statistics:
  Total validated: 300
  Valid bugs (F2P > 0 and P2P > 0): 151
  Invalid bugs: 148
  Success rate: 50.50%

Valid Bugs by Type:
  ctrl_invert_if: 32
  flip_operators: 21
  op_change: 36
  op_change_const: 13
  remove_cond: 27
  remove_loop: 15
  ctrl_shuffle: 18
  lm_rewrite: 1
  lm_modify: 1
```

### Step 6: Gather Valid Instances
Can use `gather` to create branches to mirror repository, or just use `simple_gather` to collect all valid instances into a .json file only.
```bash
# Gather with a new branch per bug
# The commit & push part fails a lot - it's quite annoying, need case by case debug ¯\_(ツ)_/¯ 
python -m swesmith.harness.gather logs/run_validation/lunarmodules__Penlight.bd26cb9e

# Simple gather
python -m swesmith.harness.simple_gather logs/run_validation/lunarmodules__Penlight.bd26cb9e
```

### Step 7: Generate Issue Descriptions

Generate natural language issue descriptions:

```bash
python -m swesmith.issue_gen.generate \
  --dataset logs/bug_gen/lunarmodules__penlight.bd26cb9e/instances_validated.json \
  --config configs/issue_gen/ig_v2.yaml
```

---

## Part 2: Notes - CustomProfile Implementation for Lua

This section documents the changes made to SWE-smith to support custom repositories.

### 2.1 CustomProfile

**File**: `swesmith/profiles/custom.py`

The `CustomProfile` class provides a flexible base for repositories with existing Dockerfiles:

**Key Features**:
- **Reuses existing Dockerfiles** from repositories
- **Language-agnostic** - works with any language
- **Configurable Dockerfile path** - handles non-standard locations
- **Dockerfile modifications** - allows programmatic adjustments
- **Fallback-free** - fails explicitly if Dockerfile not found

**Required Attributes**:
```python
owner: str          # Repository owner (e.g., "lunarmodules")
repo: str           # Repository name (e.g., "penlight")
commit: str         # Full commit hash
test_cmd: str       # Command to run tests
exts: list[str]     # File extensions (e.g., [".lua"])
```

**Optional Attributes**:
```python
dockerfile_path: str = "Dockerfile"           # Path to Dockerfile in repo
dockerfile_modifications: dict[str, str] = {} # String replacements
inject_testbed_workdir: bool = False          # Standardize WORKDIR to /testbed
```

**Standard Modifications Applied**:
1. Replaces `github.com/{owner}/{repo}` with `github.com/{mirror_name}`
2. Optionally standardizes working directory to `/testbed`

**Example Usage**:
```python
from dataclasses import dataclass, field
from swesmith.profiles.custom import CustomProfile

@dataclass
class MyCustomRepo(CustomProfile):
    owner: str = "user"
    repo: str = "repo"
    commit: str = "abc123..."
    exts: list[str] = field(default_factory=lambda: [".lua"])
    test_cmd: str = "lua test.lua"
    dockerfile_path: str = "docker/Dockerfile.dev"  # Non-standard location
    dockerfile_modifications: dict[str, str] = field(default_factory=lambda: {
        "WORKDIR /app": "WORKDIR /testbed",
        "CMD [\"server\"]": "CMD [\"/bin/bash\"]",
    })
```

### 2.2 Lua Support

**File**: `swesmith/bug_gen/adapters/lua.py`

Lua entity extractor that uses **tree-sitter-lua** to parse Lua source files and identify functions for bug generation.

**Dependencies**:
- `tree-sitter-lua` - AST parser for Lua code

**Patterns Matched**:
- `function name(...)`
- `local function name(...)`
- `function module.name(...)` (dot notation)
- `function module:name(...)` (method notation)
- Anonymous functions assigned to variables

**How it Works**:
1. Uses tree-sitter to parse Lua files into an AST
2. Walks the AST looking for `function_declaration` nodes
3. Extracts function names, signatures, and locations
4. Returns `LuaEntity` objects with full metadata (indentation, line numbers, source code)

**Why tree-sitter?**
- **Robust**: Handles complex Lua syntax correctly
- **Consistent**: Same approach as C and Go adapters
- **Rich metadata**: Provides AST nodes for advanced analysis

**Example**:
```python
from swesmith.bug_gen.adapters.lua import get_entities_from_file_lua, LuaEntity

entities = []
get_entities_from_file_lua(entities, "path/to/file.lua", max_entities=-1)

for entity in entities:
    print(f"{entity.name} at {entity.file_path}:{entity.line_start}-{entity.line_end}")
    print(f"Signature: {entity.signature}")
    print(f"Stub: {entity.stub}")
```

### 2.3 Example penlight Profile

**File**: `swesmith/profiles/lua.py`

Example profile for penlight repository that directly extends `CustomProfile`.

**Key Configurations**:
- **Dockerfile**: Uses `Dockerfile` from repository root
- **Test Command**: `lua test-runner.lua tests` (can append specific test paths)
- **File Extensions**: `.lua` files
- **Dockerfile Modifications**: 
  - Replaces WORKDIR and COPY commands with git clone to pull repository into `/testbed`
  - Updates LUA_PATH environment variable to use `/testbed` instead of `/penlight`
  - **Important**: The `github.com/lunarmodules/penlight` URL in the git clone command is automatically replaced with the mirror URL by `CustomProfile._apply_standard_modifications()`

**Test Path Detection**:
Tests are identified as files:
- In the `tests/` directory
- Starting with `test_` or ending with `_test.lua`

**Log Parser**:
Parses penlight test output format:
```
✓ tests/test-tablex.lua (45 assertions)
✓ tests/test-array2d.lua (12 assertions)
✗ tests/test-app.lua (18 assertions, 1 failed)
```

**Usage** - directly subclass CustomProfile:
```python
from dataclasses import dataclass, field
from swesmith.profiles.custom import CustomProfile

@dataclass
class Penlightbd26cb9(CustomProfile):
    owner: str = "lunarmodules"
    repo: str = "penlight"
    commit: str = "bd26cb9e4619489cb1e9e13e282888726527d954"
    
    exts: list[str] = field(default_factory=lambda: [".lua"])
    test_cmd: str = "lua test-runner.lua tests"
    dockerfile_path: str = "Dockerfile"
```

### 2.4 Lua Adapter Tests

**File**: `tests/bug_gen/adapters/test_lua.py`

Comprehensive test suite for the Lua adapter following pytest patterns used in other adapter tests.

**Test Coverage**:
- Entity extraction with various function types
- Max entities limit enforcement
- Error handling (non-existent files, malformed code)
- Function name extraction for all Lua function styles
- Indentation detection
- Source code, signature, and stub generation

**Running the Tests**:

Install test dependencies:
```bash
pip install -e ".[test]"
```

Run Lua adapter tests:
```bash
# All Lua tests
pytest tests/bug_gen/adapters/test_lua.py -v

# Specific test
pytest tests/bug_gen/adapters/test_lua.py::test_get_entities_from_file_lua_count -v

# With coverage
pytest tests/bug_gen/adapters/test_lua.py --cov=swesmith.bug_gen.adapters.lua --cov-report=term-missing
```

**Key Tests**:
- `test_get_entities_from_file_lua_count` - Validates correct entity count
- `test_get_entities_from_file_lua_names` - Tests function name extraction
- `test_get_entities_from_file_lua_method` - Tests method notation (`:`)
- `test_get_entities_from_file_lua_dot_notation` - Tests dot notation (`.`)
- `test_get_entities_from_file_lua_stub` - Tests stub generation

### 2.5 Updated Imports

**File**: `swesmith/profiles/__init__.py`

Added:
```python
from .custom import CustomProfile
from . import lua
```

**File**: `swesmith/bug_gen/adapters/__init__.py`

Added:
```python
from swesmith.bug_gen.adapters.lua import get_entities_from_file_lua

get_entities_from_file = {
    # ... existing entries ...
    ".lua": get_entities_from_file_lua,
}
```

---

## Using CustomProfile for Other Repositories

### Example 1: Another Lua Project with Different Structure

```python
from dataclasses import dataclass, field
from swesmith.profiles.custom import CustomProfile

@dataclass
class MyLuaProject(CustomProfile):
    owner: str = "user"
    repo: str = "lua-project"
    commit: str = "abcdef123..."
    
    exts: list[str] = field(default_factory=lambda: [".lua"])
    test_cmd: str = "busted specs/"  # Using busted test framework
    
    # Custom dockerfile location
    dockerfile_path: str = "ci/Dockerfile"
    
    # Override test detection
    def _is_test_path(self, root: str, file: str) -> bool:
        if not file.endswith(".lua"):
            return False
        return "specs/" in root or "_spec.lua" in file
```

### Example 2: JavaScript Project with Existing Dockerfile

```python
from dataclasses import dataclass, field
from swesmith.profiles.custom import CustomProfile

@dataclass
class MyNodeProject(CustomProfile):
    owner: str = "org"
    repo: str = "node-project"
    commit: str = "xyz789..."
    
    exts: list[str] = field(default_factory=lambda: [".js", ".ts"])
    test_cmd: str = "npm test"
    
    dockerfile_path: str = "docker/Dockerfile.dev"
    dockerfile_modifications: dict[str, str] = field(default_factory=lambda: {
        "NODE_ENV=production": "NODE_ENV=test",
        "npm ci --production": "npm ci",
    })
```

### Example 3: Custom Log Parser

If your test framework has unique output format:

```python
import re
from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.custom import CustomProfile

@dataclass
class MyProject(CustomProfile):
    owner: str = "user"
    repo: str = "project"
    commit: str = "abc..."
    exts: list[str] = field(default_factory=lambda: [".lua"])
    test_cmd: str = "custom-test-runner"
    
    def log_parser(self, log: str) -> dict[str, str]:
        """Parse custom test output format."""
        test_status_map = {}
        
        # Example: "TEST: test_name => SUCCESS"
        for line in log.split("\n"):
            match = re.match(r"TEST:\s+(\S+)\s+=>\s+(SUCCESS|FAILURE)", line)
            if match:
                test_name = match.group(1)
                status = match.group(2)
                test_status_map[test_name] = (
                    TestStatus.PASSED.value if status == "SUCCESS" 
                    else TestStatus.FAILED.value
                )
        
        return test_status_map
```

---

## Troubleshooting

### Issue: "Dockerfile not found"

**Error**:
```
FileNotFoundError: Dockerfile not found at 'Dockerfile' in repository lunarmodules__penlight.bd26cb9e
```

**Solutions**:
1. Check if Dockerfile exists in the repository:
   ```bash
   cd /path/to/repo
   ls -la Dockerfile
   ```

2. If Dockerfile is in a different location, set `dockerfile_path`:
   ```python
   dockerfile_path: str = "docker/Dockerfile.dev"
   ```

3. Verify the repository was cloned correctly:
   ```python
   profile.clone()
   ```

### Issue: Mirror Creation Fails

**Error**: Permission denied or repository not found

**Solutions**:
1. Ensure `GITHUB_TOKEN` is set:
   ```bash
   export GITHUB_TOKEN="your_token"
   ```

2. Verify token has repository creation permissions

3. Check if mirror already exists:
   ```python
   profile._mirror_exists()  # Should return True if exists
   ```

### Issue: Tests Not Detected

**Problem**: No tests found during validation

**Solutions**:
1. Override `_is_test_path()` method:
   ```python
   def _is_test_path(self, root: str, file: str) -> bool:
       # Custom logic for your repository
       return "tests/" in root or file.endswith("_test.lua")
   ```

2. Check test command is correct:
   ```bash
   docker run -it <image_name>
   # Inside container:
   lua test-runner.lua tests/test-tablex.lua
   ```

### Issue: Log Parser Not Working

**Problem**: Test results not captured correctly

**Solutions**:
1. Run tests manually and examine output:
   ```bash
   docker run -it <image_name>
   lua test-runner.lua tests/test-tablex.lua > test_output.txt
   cat test_output.txt
   ```

2. Override `log_parser()` with custom patterns:
   ```python
   def log_parser(self, log: str) -> dict[str, str]:
       # Add debugging
       print(f"Parsing log:\n{log}")
       # Your custom parsing logic
       pass
   ```

### Issue: Docker Build Fails

**Problem**: Image build fails due to Dockerfile issues

**Solutions**:
1. Test Dockerfile manually:
   ```bash
   cd /path/to/repo
   docker build -t test-image -f Dockerfile .
   ```

2. Apply modifications to fix issues:
   ```python
   dockerfile_modifications: dict[str, str] = field(default_factory=lambda: {
       "broken_line": "fixed_line",
   })
   ```

3. Use `inject_testbed_workdir=True` if path issues occur
