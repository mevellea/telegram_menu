"""telegram_menu package installer."""

import os

from setuptools import find_packages, setup

with open(os.path.join("README.md"), "r") as fh:
    LONG_DESCRIPTION = fh.read()

__title__ = "telegram_menu"
__version__ = "0.2.1"

setup(
    name=__title__,
    version=__version__,
    description="A python library to generate navigation menus using Telegram Bot API",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/mevellea/telegram_menu",
    author="Armel MEVELLEC",
    author_email="mevellea@gmail.com",
    license="GNU GPLv3",
    packages=find_packages(),
    install_requires=[],
    tests_require=["tox>=3.5.0,<4.0.0"],
    platforms=["any"],
    keywords="telegram",
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Home Automation",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
