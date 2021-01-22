#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# mypy: ignore-errors

"""telegram_menu package installer."""

from setuptools import find_packages, setup

exec(open("telegram_menu/_version.py").read())

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

requires = open("requirements.txt").read().strip().split("\n")

setup(
    name=__title__,
    version=__version__,
    description=__description__,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url=__url__,
    author=__author__,
    author_email=__author_email__,
    license=__license__,
    package_data={"telegram_menu": ["py.typed"]},
    include_package_data=True,
    packages=find_packages(),
    install_requires=requires,
    tests_require=["tox>=3.5.0,<4.0.0"],
    platforms=["any"],
    keywords="telegram",
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
