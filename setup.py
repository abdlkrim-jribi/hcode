"""hcode package setup configuration.

This module uses :mod:`setuptools` to define the package metadata,
its dependencies, entry points, and other configuration required for
building and distributing the *hcode* project.

Typical usage:
    python -m pip install .
    python -m build
    python -m twine upload dist/*

Attributes:
    long_description (str): Content of ``README.md`` if present,
        used as the long description on PyPI.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="hcode",
    version="0.1.0",
    author="Hcode Team",
    author_email="contact@hcode.dev",
    description="Universal AI Coding Assistant supporting Anthropic Claude and OpenAI GPT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/hcode",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "anthropic>=0.34.0",
        "openai>=1.40.0",
        "click>=8.0",
        "rich>=13.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0",
        "watchdog>=4.0",
        "gitpython>=3.1",
        "pathspec>=0.11",
        "pygments>=2.15",
        "tiktoken>=0.5",
        "tenacity>=8.2",
        "httpx>=0.25",
        "aiofiles>=23.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0",
            "pytest-asyncio>=0.23.0",
            "black>=24.0",
            "pylint>=3.0",
            "mypy>=1.0",
        ],
        "docker": [
            "docker>=7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hcode=hcode.cli_enhanced:main",
        ],
    },
    include_package_data=True,
    package_data={
        "hcode": [
            "examples/*.example",
            "examples/*.py",
        ],
    },
    keywords="ai coding assistant claude gpt openai anthropic code-generation",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/hcode/issues",
        "Source": "https://github.com/yourusername/hcode",
        "Documentation": "https://github.com/yourusername/hcode#readme",
    },
)
