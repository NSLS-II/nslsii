from __future__ import annotations

# To use a consistent encoding
from codecs import open
from pathlib import Path

import setuptools

import versioneer

here = Path(__file__).resolve().parent

# Get the long description from the README file
with open(here.joinpath("README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(here.joinpath("requirements.txt"), encoding="utf-8") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="nslsii",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license="BSD (3-clause)",
    packages=setuptools.find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    description="Tools for data collection and analysis at NSLS-II",
    author="Brookhaven National Laboratory",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "sync-experiment = nslsii.sync_experiment:main",
            "what-is-ioc = nslsii.epics_utils:main",
            "axis-saver-ioc = nslsii.iocs.caproto_saver:start_axis_ioc",
        ],
    },
)
