#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 Armel Mevellec
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

"""Lightweight image-format detection.

The standard-library ``imghdr`` module was removed in Python 3.13, so this
module provides the small subset of functionality the package relies on:
recognising an image file from its magic-number header.
"""

from __future__ import annotations

from pathlib import Path

# Number of header bytes required to recognise any of the supported formats.
_HEADER_SIZE = 32


def what_bytes(header: bytes) -> str | None:
    """Return the image format detected from a header, or None if unrecognised."""
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    if header[:2] == b"BM":
        return "bmp"
    if header[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    return None


def what(path: str | Path) -> str | None:
    """Return the image format of a file, or None if it is not a recognised image."""
    try:
        with open(path, "rb") as file_h:
            header = file_h.read(_HEADER_SIZE)
    except OSError:
        return None
    return what_bytes(header)
