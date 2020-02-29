"""telegram_menu"""

import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join("README.md"), "r") as fh:
    long_description = fh.read()

__title__ = "telegram_menu"
__version__ = "0.1.0"

setup(
    name=__title__,
    version=__version__,
    description="A python library to generate menus and messages for the Telegram Bot API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mevellea/telegram_menu",
    author="Armel Mevellec",
    author_email="mevellea@gmail.com",
    license="GNU GPLv3",
    packages=find_packages(),
    install_requires=[],
    tests_require=["tox>=3.5.0,<4.0.0"],
    platforms=["any"],
    keywords="heos",
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
    ],
)