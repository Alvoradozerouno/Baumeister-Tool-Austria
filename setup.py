"""
Setup script for ORION Architekt-AT
Backwards compatibility with older Python packaging tools
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")


# Read requirements
def read_requirements(filename):
    filepath = Path(__file__).parent / filename
    with open(filepath) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


setup(
    name="orion-architekt-at",
    version="2.1.0",
    description="Comprehensive Austrian building regulations tool with OIB-RL compliance",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Elisabeth Steurer, Gerhard Hirschmann",
    author_email="",
    url="https://github.com/Alvoradozerouno/ORION-Architekt-AT",
    project_urls={
        "Bug Reports": "https://github.com/Alvoradozerouno/ORION-Architekt-AT/issues",
        "Source": "https://github.com/Alvoradozerouno/ORION-Architekt-AT",
        "Documentation": "https://github.com/Alvoradozerouno/ORION-Architekt-AT/blob/main/README.md",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.11",
    install_requires=read_requirements("requirements.txt")[:10],  # Core dependencies only
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "black>=24.0.0",
            "flake8>=7.0.0",
            "isort>=5.13.0",
        ],
        "all": read_requirements("requirements.txt"),
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Architecture",
    ],
    keywords="austrian-building-regulations oib-richtlinien oenorm building-compliance architecture construction",
    license="MIT",
    include_package_data=True,
    zip_safe=False,
)
