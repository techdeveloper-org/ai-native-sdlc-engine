"""
Setup configuration for AI-Native SDLC Engine
"""

from pathlib import Path

from setuptools import find_packages, setup

# Single source of truth: VERSION file
version_file = Path(__file__).parent / "VERSION"
VERSION = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "0.0.0"

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="ai-native-sdlc-engine",
    version=VERSION,
    description="Universal AI-Native SDLC Framework for Autonomous Zero-Debt Engineering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="TechDeveloper",
    author_email="",
    url="https://github.com/techdeveloper-org/ai-native-sdlc-engine",
    license="MIT",
    # Package configuration
    packages=find_packages(where=".", include=["sdlc_engine", "sdlc_engine.*"]),
    include_package_data=True,
    # Dependencies
    install_requires=requirements,
    python_requires=">=3.8",
    # Entry points
    entry_points={
        "console_scripts": [
            "sdlc=sdlc_engine.adapters.cli.cli_handler:main",
            "ai-sdlc=sdlc_engine.adapters.cli.cli_handler:main",
            "ai-sdlc-engine=sdlc_engine.adapters.cli.main:main",
            "claude-workflow=sdlc_engine.adapters.cli.main:main",
            "cwe=sdlc_engine.adapters.cli.cli_handler:main",
        ],
    },
    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Build Tools",
    ],
    keywords="ai sdlc automation langgraph orchestration gemini openai claude ollama quality",
    project_urls={
        "Documentation": "https://github.com/techdeveloper-org/ai-native-sdlc-engine",
        "Source": "https://github.com/techdeveloper-org/ai-native-sdlc-engine",
        "Tracker": "https://github.com/techdeveloper-org/ai-native-sdlc-engine/issues",
    },
)
