"""
Lua repository profiles using CustomProfile.

This module provides example profiles for Lua-based repositories.
"""

import re
from dataclasses import dataclass, field
from swebench.harness.constants import TestStatus
from swesmith.profiles.custom import CustomProfile
from swesmith.profiles.base import registry
from swesmith.constants import ORG_NAME_GH



# Penlight - a set of pure Lua libraries
# https://github.com/lunarmodules/penlight
@dataclass
class Penlightbd26cb9(CustomProfile):
    owner: str = "lunarmodules"
    repo: str = "Penlight"
    commit: str = "bd26cb9e4619489cb1e9e13e282888726527d954"
    
    exts: list[str] = field(default_factory=lambda: [".lua"])
    test_cmd: str = "lua test-runner.lua tests"
    timeout: int = 300
    dockerfile_path: str = "Dockerfile"
    
    # Modifications for SWE-smith:
    # Clone the repository from mirror into /testbed instead of copying files
    # Note: All the COPY commands must be included in the search string because:
    # 1. They would fail (files don't exist in Docker build context)
    # 2. Git clone makes them unnecessary (files already in /testbed)
    # 3. We replace the entire block (WORKDIR + all COPYs) in one operation
    dockerfile_modifications: dict[str, str] = field(default_factory=lambda: {
        "WORKDIR /penlight\n\nCOPY lua/ ./lua/\nCOPY tests/ ./tests/\nCOPY spec/ ./spec/\nCOPY examples/ ./examples/\nCOPY docs/ ./docs/\nCOPY run.lua ./\nCOPY test-runner.lua ./\nCOPY show-coverage.lua ./": (
            "# Clone penlight repository from mirror - all files included\n"
            f"RUN git clone https://github.com/{ORG_NAME_GH}/lunarmodules__penlight.bd26cb9e.git /testbed\n"
            "WORKDIR /testbed"
        ),
        "RUN chmod +x show-coverage.lua": "# chmod not needed - files from git clone",
        "ENV LUA_PATH=\"/penlight/lua/?.lua;/penlight/lua/?/init.lua;;\"": "ENV LUA_PATH=\"/testbed/lua/?.lua;/testbed/lua/?/init.lua;;\"",
    })

    def log_parser(self, log: str) -> dict[str, str]:
        """
        Parse penlight test output.

        penlight test output format:
        ✓ tests/test-__vector.lua (2 assertions)
        ✗ tests/test-app.lua (18 assertions, 1 failed)
        """
        test_status_map = {}
        for line in log.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("✓"):
                test_name = line.split(" ")[1]
                test_status_map[test_name] = TestStatus.PASSED.value
            elif line.startswith("✗"):
                test_name = line.split(" ")[1]
                test_status_map[test_name] = TestStatus.FAILED.value
        return test_status_map


# xmake - a Lua-based build system
# https://github.com/xmake-io/xmake
@dataclass
class Xmakeb3a2dba93(CustomProfile):
    owner: str = "xmake-io"
    repo: str = "xmake"
    commit: str = "b3a2dba93a185f205dbd18a154e42da72fdd4881"  # short commit hash: b3a2dba93
    
    # Lua file extensions
    exts: list[str] = field(default_factory=lambda: [".lua"])
    
    # xmake's test command (can append specific test paths)
    test_cmd: str = "xmake l tests/run.lua"
    
    # Increase timeout for full test suite (177 tests take ~144s)
    timeout: int = 300  # 5 minutes
    
    # Use existing Dockerfile from repo root (created after cloning the repo)
    dockerfile_path: str = "Dockerfile.simple"
    
    # Modifications for SWE-smith:
    # 1. Clone the repository from mirror into /testbed
    # 2. Ensure xmake can run as root in Docker
    # Note: github.com/xmake-io/xmake will be replaced with mirror by _apply_standard_modifications()
    dockerfile_modifications: dict[str, str] = field(default_factory=lambda: {
        "WORKDIR /workspace": (
            "# Clone xmake repository from mirror\n"
            "RUN git clone https://github.com/xmake-io/xmake.git /testbed\n"
            "WORKDIR /testbed"
        ),
        "CMD [\"/bin/bash\"]": "ENV XMAKE_ROOT=y\nCMD [\"/bin/bash\"]",
    })
    
    def _is_test_path(self, root: str, file: str) -> bool:
        """Identify xmake test files."""
        if not file.endswith(".lua"):
            return False
        
        # xmake tests are in the tests/ directory
        if "tests/" in root or root.endswith("tests"):
            return True
        
        # Additional patterns for test files
        if file.startswith("test_") or file.endswith("_test.lua"):
            return True
        
        return False
    
    def log_parser(self, log: str) -> dict[str, str]:
        """
        Parse xmake test output.
        
        xmake test output format:
        >> [N/TOTAL]: testing tests/path/to/test ...
        
        Tests that pass have no explicit status - they just move to the next test.
        Tests that fail show:
        >>     test failed: error message
        error: aborting because of unhandled error ...
        """
        # Strip ANSI color codes from the entire log
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        log = ansi_escape.sub('', log)
        
        test_status_map = {}
        lines = log.split("\n")
        
        # Pattern to match test start: >> [N/TOTAL]: testing TEST_PATH ...
        pattern_test_start = re.compile(r"^>>\s+\[\d+/\d+\]:\s+testing\s+(.+?)\s+\.\.\.")
        
        current_test = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Check if this is a test start
            match = pattern_test_start.match(line)
            if match:
                test_path = match.group(1).strip()
                
                # If there was a previous test without failure, it passed
                if current_test is not None:
                    if current_test not in test_status_map:
                        test_status_map[current_test] = TestStatus.PASSED.value
                
                # Start tracking new test
                current_test = test_path
                continue
            
            # Check for test failure indicators
            if current_test and ("test failed:" in line or 
                                 line.startswith("error:") or 
                                 ">>     test failed:" in line):
                test_status_map[current_test] = TestStatus.FAILED.value
                current_test = None  # Reset so we don't mark it as passed later
                continue
        
        # Handle the last test if it didn't fail
        if current_test is not None:
            if current_test not in test_status_map:
                test_status_map[current_test] = TestStatus.PASSED.value
        
        return test_status_map


# Register all profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, CustomProfile)
        and obj.__name__ != "CustomProfile"
    ):
        registry.register_profile(obj)
