from __future__ import (absolute_import, division, print_function)

import versioneer
import setuptools

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name='nslsii',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license="BSD (3-clause)",
    packages=setuptools.find_packages(),
    description='Tools for data collection and analysis at NSLS-II',
    author='Stuart B. Wilkins',
    author_email='swilkins@bnl.gov',
    install_requires=requirements,
)
