"""
Custom repository profile class for repositories with existing Dockerfiles.

This module provides a flexible profile that uses a repository's existing Dockerfile rather than generating one.
"""

import os
import re
import shutil
from dataclasses import dataclass, field
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile


@dataclass
class CustomProfile(RepoProfile):
    """
    Generic profile that uses a repository's existing Dockerfile.
    
    Use this for repositories that:
    - Already have a working Dockerfile
    - Have unique build/test requirements
    - Don't fit standard language profiles (Python, Go, Rust, etc.)
    
    Required attributes to set:
        owner: Repository owner
        repo: Repository name
        commit: Commit hash
        test_cmd: Command to run tests
        exts: File extensions for the language (e.g., [".lua"], [".js"])
    
    Optional attributes:
        dockerfile_path: Path to Dockerfile in repo (default: "Dockerfile")
        dockerfile_modifications: Dict of string replacements for the Dockerfile
        inject_testbed_workdir: Whether to standardize WORKDIR to /testbed
    
    Example:
        @dataclass
        class MyRepo(CustomProfile):
            owner: str = "user"
            repo: str = "repo"
            commit: str = "abc123"
            exts: list[str] = field(default_factory=lambda: [".lua"])
            test_cmd: str = "make test"
            dockerfile_path: str = "docker/Dockerfile.dev"
    """
    
    # Path to Dockerfile within the repository
    dockerfile_path: str = "Dockerfile"
    
    # Optional modifications to apply to the Dockerfile
    # Example: {"COPY . /app": "COPY . /testbed", "WORKDIR /app": "WORKDIR /testbed"}
    dockerfile_modifications: dict[str, str] = field(default_factory=dict)
    
    # Whether to standardize working directory to /testbed (SWE-smith convention)
    inject_testbed_workdir: bool = False
    
    @property
    def dockerfile(self) -> str:
        """Read and optionally modify the repository's existing Dockerfile."""
        dir_path, cloned = self.clone()
        dockerfile_full_path = os.path.join(dir_path, self.dockerfile_path)
        
        if not os.path.exists(dockerfile_full_path):
            if cloned:
                shutil.rmtree(dir_path)
            raise FileNotFoundError(
                f"Dockerfile not found at '{self.dockerfile_path}' in repository {self.repo_name}. "
                f"CustomProfile requires an existing Dockerfile in the repository. "
                f"Please check:\n"
                f"  1. The dockerfile_path is correct (currently: '{self.dockerfile_path}')\n"
                f"  2. The repository has been cloned successfully\n"
                f"  3. The Dockerfile exists at the specified path"
            )
        
        with open(dockerfile_full_path, 'r') as f:
            content = f.read()
        
        if cloned:
            shutil.rmtree(dir_path)
        
        # Apply standard modifications
        content = self._apply_standard_modifications(content)
        
        # Apply user-specified modifications
        for old, new in self.dockerfile_modifications.items():
            content = content.replace(old, new)
        
        return content
    
    def _apply_standard_modifications(self, dockerfile_content: str) -> str:
        """Apply standard SWE-smith modifications to the Dockerfile."""
        
        # Replace original repo references with mirror
        dockerfile_content = dockerfile_content.replace(
            f"github.com/{self.owner}/{self.repo}",
            f"github.com/{self.mirror_name}"
        )
        
        # Optionally standardize working directory to /testbed
        if self.inject_testbed_workdir:
            replacements = {
                "WORKDIR /workspace": "WORKDIR /testbed",
                "WORKDIR /app": "WORKDIR /testbed",
                "WORKDIR /src": "WORKDIR /testbed",
            }
            for old, new in replacements.items():
                dockerfile_content = dockerfile_content.replace(old, new)
        
        return dockerfile_content
    
    def log_parser(self, log: str) -> dict[str, str]:
        """
        Basic test log parser. Override this method for repository-specific parsing.
        
        This default implementation looks for common test output patterns across
        different test frameworks and languages.
        
        Args:
            log: Raw test output log string
            
        Returns:
            Dictionary mapping test names to their status (PASSED, FAILED, etc.)
        """
        test_status_map = {}
        
        # Common patterns across different test frameworks
        # Format: (regex pattern, status)
        patterns = [
            # Format: "PASS test_name" or "✓ test_name" or "ok test_name"
            (re.compile(r"^(?:PASS|✓|ok|PASSED|SUCCESS)[\s:]+(.+)$", re.IGNORECASE), TestStatus.PASSED.value),
            # Format: "FAIL test_name" or "✗ test_name" or "ERROR test_name"
            (re.compile(r"^(?:FAIL|✗|not ok|FAILED|ERROR)[\s:]+(.+)$", re.IGNORECASE), TestStatus.FAILED.value),
            # Format: "test_name ... ok" or "test_name ... PASS"
            (re.compile(r"^(.+?)\s+\.\.\.\s+(?:ok|PASS|passed)$", re.IGNORECASE), TestStatus.PASSED.value),
            # Format: "test_name ... FAIL" or "test_name ... ERROR"
            (re.compile(r"^(.+?)\s+\.\.\.\s+(?:FAIL|ERROR|failed)$", re.IGNORECASE), TestStatus.FAILED.value),
            # Format: "[PASS] test_name" or "[✓] test_name"
            (re.compile(r"^\[(?:PASS|✓|OK)\]\s+(.+)$", re.IGNORECASE), TestStatus.PASSED.value),
            # Format: "[FAIL] test_name" or "[✗] test_name"
            (re.compile(r"^\[(?:FAIL|✗|ERROR)\]\s+(.+)$", re.IGNORECASE), TestStatus.FAILED.value),
        ]
        
        for line in log.split("\n"):
            line = line.strip()
            if not line:
                continue
                
            for pattern, status in patterns:
                match = pattern.match(line)
                if match:
                    # Extract test name (the captured group)
                    test_name = match.group(1).strip()
                    test_status_map[test_name] = status
                    break
        
        return test_status_map

