from __future__ import (absolute_import, division, print_function)

import versioneer
import setuptools

setuptools.setup(
	name='nsls2tools',
    version=versioneer.get_version(),
	cmdclass=versioneer.get_cmdclass(),
    license="BSD (3-clause)",
    packages=setuptools.find_packages(),
    description='Tools for data collection and analysis at NSLS-II',
	author='Stuart B. Wilkins',
    author_email='swilkins@bnl.gov',
)
