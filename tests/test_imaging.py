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

"""Unit-tests for the image-format sniffer that replaces stdlib imghdr."""

from __future__ import annotations

import pytest

from telegram_menu import _imaging

from .example_app import ROOT_FOLDER


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8, "png"),
        (b"\xff\xd8\xff\xe0", "jpeg"),
        (b"GIF89a....", "gif"),
        (b"GIF87a....", "gif"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "webp"),
        (b"BM\x00\x00", "bmp"),
        (b"II*\x00", "tiff"),
        (b"MM\x00*", "tiff"),
        (b"not an image", None),
        (b"", None),
    ],
)
def test_what_bytes(header: bytes, expected: str | None) -> None:
    """The header sniffer recognises supported formats and rejects others."""
    assert _imaging.what_bytes(header) == expected


def test_what_real_files() -> None:
    """The file-based sniffer recognises the bundled resources."""
    assert _imaging.what(ROOT_FOLDER / "resources" / "packages.png") == "png"
    assert _imaging.what(ROOT_FOLDER / "resources" / "stats_default.webp") == "webp"


def test_what_missing_file_returns_none() -> None:
    """A missing or unreadable file yields None instead of raising."""
    assert _imaging.what(ROOT_FOLDER / "does-not-exist.png") is None


def test_what_non_image_file_returns_none() -> None:
    """A non-image file (this test source) is not recognised as an image."""
    assert _imaging.what(__file__) is None
