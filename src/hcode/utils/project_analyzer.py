"""
Project analysis utilities for Hcode.
Detects languages, frameworks, and project structure.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
import re


class ProjectAnalyzer:
    """Analyzes project structure and characteristics"""

    # File patterns for language detection
    LANGUAGE_PATTERNS = {
        "python": ["*.py", "requirements.txt", "setup.py", "pyproject.toml"],
        "javascript": ["*.js", "package.json", "*.jsx"],
        "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
        "rust": ["*.rs", "Cargo.toml"],
        "go": ["*.go", "go.mod"],
        "java": ["*.java", "pom.xml", "build.gradle"],
        "c++": ["*.cpp", "*.hpp", "*.cc", "CMakeLists.txt"],
        "c": ["*.c", "*.h", "Makefile"],
        "ruby": ["*.rb", "Gemfile"],
        "php": ["*.php", "composer.json"],
        "swift": ["*.swift", "Package.swift"],
        "kotlin": ["*.kt", "build.gradle.kts"],
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "django": ["manage.py", "settings.py"],
        "flask": ["app.py", "application.py"],
        "fastapi": ["main.py"],  # + import check
        "react": ["package.json"],  # + dependencies check
        "vue": ["vue.config.js"],
        "angular": ["angular.json"],
        "express": ["package.json"],  # + dependencies check
        "spring": ["pom.xml", "build.gradle"],
        "rails": ["Gemfile", "config/application.rb"],
        "laravel": ["artisan", "composer.json"],
    }

    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize project analyzer.

        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir or Path.cwd())

    def analyze(self) -> Dict:
        """
        Perform complete project analysis.

        Returns:
            Analysis results dictionary
        """
        return {
            "root_dir": str(self.root_dir),
            "languages": self.detect_languages(),
            "frameworks": self.detect_frameworks(),
            "build_system": self.detect_build_system(),
            "test_framework": self.detect_test_framework(),
            "dependencies": self.get_dependencies(),
            "structure": self.analyze_structure(),
            "stats": self.get_statistics(),
        }

    def detect_languages(self) -> List[str]:
        """
        Detect programming languages used in project.

        Returns:
            List of detected languages
        """
        detected = set()

        for language, patterns in self.LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if list(self.root_dir.glob(f"**/{pattern}")):
                    detected.add(language)
                    break

        return sorted(detected)

    def detect_frameworks(self) -> List[str]:
        """
        Detect frameworks used in project.

        Returns:
            List of detected frameworks
        """
        detected = set()

        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if list(self.root_dir.glob(f"**/{pattern}")):
                    # Additional checks for ambiguous cases
                    if framework == "react":
                        if self._has_react_dependency():
                            detected.add(framework)
                    elif framework == "express":
                        if self._has_express_dependency():
                            detected.add(framework)
                    elif framework == "fastapi":
                        if self._has_fastapi_dependency():
                            detected.add(framework)
                    else:
                        detected.add(framework)
                    break

        return sorted(detected)

    def detect_build_system(self) -> Optional[str]:
        """
        Detect build system.

        Returns:
            Build system name or None
        """
        build_systems = {
            "make": ["Makefile"],
            "cmake": ["CMakeLists.txt"],
            "npm": ["package.json"],
            "yarn": ["yarn.lock"],
            "cargo": ["Cargo.toml"],
            "gradle": ["build.gradle", "build.gradle.kts"],
            "maven": ["pom.xml"],
            "poetry": ["pyproject.toml"],  # + check tool.poetry section
        }

        for system, files in build_systems.items():
            for file in files:
                if (self.root_dir / file).exists():
                    return system

        return None

    def detect_test_framework(self) -> Optional[str]:
        """
        Detect test framework.

        Returns:
            Test framework name or None
        """
        # Check for Python test frameworks
        if (self.root_dir / "pytest.ini").exists() or (self.root_dir / "pyproject.toml").exists():
            return "pytest"

        # Check for JavaScript test frameworks
        package_json = self.root_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                    if "jest" in deps:
                        return "jest"
                    if "mocha" in deps:
                        return "mocha"
                    if "jasmine" in deps:
                        return "jasmine"
            except:
                pass

        # Check for other frameworks
        if list(self.root_dir.glob("**/*_test.go")):
            return "go test"

        if (self.root_dir / "Cargo.toml").exists():
            return "cargo test"

        return None

    def get_dependencies(self) -> Dict[str, List[str]]:
        """
        Extract project dependencies.

        Returns:
            Dictionary mapping dependency types to lists of dependencies
        """
        dependencies = {}

        # Python dependencies
        requirements_file = self.root_dir / "requirements.txt"
        if requirements_file.exists():
            with open(requirements_file) as f:
                dependencies["python"] = [
                    line.strip() for line in f if line.strip() and not line.startswith("#")
                ]

        # JavaScript dependencies
        package_json = self.root_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    dependencies["javascript"] = list(data.get("dependencies", {}).keys())
                    dependencies["javascript_dev"] = list(data.get("devDependencies", {}).keys())
            except:
                pass

        # Rust dependencies
        cargo_toml = self.root_dir / "Cargo.toml"
        if cargo_toml.exists():
            # Parse TOML (simple extraction)
            dependencies["rust"] = self._parse_cargo_dependencies(cargo_toml)

        return dependencies

    def analyze_structure(self) -> Dict:
        """
        Analyze project directory structure.

        Returns:
            Structure analysis
        """
        structure = {
            "total_files": 0,
            "total_dirs": 0,
            "by_extension": {},
            "largest_files": [],
        }

        files = []

        for item in self.root_dir.rglob("*"):
            # Skip hidden and common ignore patterns
            if any(part.startswith(".") for part in item.parts):
                continue
            if "node_modules" in item.parts or "__pycache__" in item.parts:
                continue

            if item.is_file():
                structure["total_files"] += 1

                ext = item.suffix or "no_extension"
                structure["by_extension"][ext] = structure["by_extension"].get(ext, 0) + 1

                files.append((item, item.stat().st_size))

            elif item.is_dir():
                structure["total_dirs"] += 1

        # Get largest files
        files.sort(key=lambda x: x[1], reverse=True)
        structure["largest_files"] = [
            {"path": str(f[0].relative_to(self.root_dir)), "size": f[1]} for f in files[:10]
        ]

        return structure

    def get_statistics(self) -> Dict:
        """
        Get code statistics.

        Returns:
            Statistics dictionary
        """
        stats = {
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
        }

        # Common code file extensions
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".rs",
            ".go",
            ".rb",
            ".php",
            ".swift",
            ".kt",
        }

        for ext in code_extensions:
            for file_path in self.root_dir.rglob(f"*{ext}"):
                # Skip common ignore patterns
                if any(part.startswith(".") for part in file_path.parts):
                    continue
                if "node_modules" in file_path.parts or "__pycache__" in file_path.parts:
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            stats["total_lines"] += 1

                            stripped = line.strip()
                            if not stripped:
                                stats["blank_lines"] += 1
                            elif stripped.startswith("#") or stripped.startswith("//"):
                                stats["comment_lines"] += 1
                            else:
                                stats["code_lines"] += 1
                except:
                    pass

        return stats

    def _has_react_dependency(self) -> bool:
        """Check if project has React dependency"""
        package_json = self.root_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    return "react" in deps
            except:
                pass
        return False

    def _has_express_dependency(self) -> bool:
        """Check if project has Express dependency"""
        package_json = self.root_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    return "express" in deps
            except:
                pass
        return False

    def _has_fastapi_dependency(self) -> bool:
        """Check if project has FastAPI dependency"""
        requirements_file = self.root_dir / "requirements.txt"
        if requirements_file.exists():
            with open(requirements_file) as f:
                content = f.read()
                return "fastapi" in content.lower()
        return False

    def _parse_cargo_dependencies(self, cargo_toml: Path) -> List[str]:
        """Parse dependencies from Cargo.toml"""
        dependencies = []

        try:
            with open(cargo_toml) as f:
                in_dependencies = False

                for line in f:
                    if line.strip() == "[dependencies]":
                        in_dependencies = True
                        continue
                    elif line.strip().startswith("[") and in_dependencies:
                        break

                    if in_dependencies and "=" in line:
                        dep_name = line.split("=")[0].strip()
                        if dep_name:
                            dependencies.append(dep_name)
        except:
            pass

        return dependencies

    def generate_summary(self) -> str:
        """
        Generate a human-readable project summary.

        Returns:
            Summary string
        """
        analysis = self.analyze()

        summary = f"Project: {self.root_dir.name}\n"
        summary += f"Location: {self.root_dir}\n\n"

        summary += f"Languages: {', '.join(analysis['languages']) or 'None detected'}\n"
        summary += f"Frameworks: {', '.join(analysis['frameworks']) or 'None detected'}\n"
        summary += f"Build System: {analysis['build_system'] or 'None detected'}\n"
        summary += f"Test Framework: {analysis['test_framework'] or 'None detected'}\n\n"

        stats = analysis["stats"]
        summary += f"Code Statistics:\n"
        summary += f"  Total Lines: {stats['total_lines']}\n"
        summary += f"  Code Lines: {stats['code_lines']}\n"
        summary += f"  Comment Lines: {stats['comment_lines']}\n"
        summary += f"  Blank Lines: {stats['blank_lines']}\n\n"

        structure = analysis["structure"]
        summary += f"Files: {structure['total_files']}\n"
        summary += f"Directories: {structure['total_dirs']}\n"

        return summary
