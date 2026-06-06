#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 Armel Mevellec
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

"""Unit-tests for telegram_menu.models (no network needed)."""

from __future__ import annotations

import datetime

import pytest
from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup

from telegram_menu import ButtonType, MenuButton
from telegram_menu.models import call_callback, emoji_replace

from .example_app import OptionsAppMessage, SecondMenuMessage, StartMessage


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("lbl", "lbl"),
        (":lbl:", ":lbl:"),
        ("", ""),
        (":robot:", "🤖"),
        (":robot:-:robot::", "🤖-🤖:"),
        (":robot: , :ghost:", "🤖 , 👻"),
    ],
)
def test_emoji_replace(text: str, expected: str) -> None:
    """Emoji aliases are expanded, unknown tokens left untouched."""
    assert emoji_replace(text) == expected


def test_menu_button_defaults() -> None:
    """MenuButton expands emoji in label and keeps default attributes."""
    button = MenuButton(":robot:")
    assert button.label == "🤖"
    assert button.callback is None
    assert button.btype == ButtonType.NOTIFICATION
    assert button.notification is True
    assert button.web_app_url == ""


def test_get_button(navigation) -> None:
    """get_button finds a button by its (emoji-expanded) label."""
    message = StartMessage(navigation)
    assert message.get_button("Action") is not None
    assert message.get_button("does-not-exist") is None


@pytest.mark.parametrize(
    ("count", "rows"),
    [(1, [1]), (2, [2]), (3, [2, 1]), (4, [2, 2]), (7, [2, 2, 2, 1])],
)
def test_reply_keyboard_row_packing(navigation, count: int, rows: list[int]) -> None:
    """Non-inlined messages pack two buttons per row."""
    message = StartMessage(navigation)
    message.keyboard = [[]]
    for index in range(count):
        message.add_button(label=str(index), callback=StartMessage.run_and_notify)
    content = message.gen_keyboard_content()
    assert isinstance(content, ReplyKeyboardMarkup)
    assert [len(row) for row in content.keyboard] == rows


@pytest.mark.parametrize(
    ("count", "rows"),
    [(2, [2]), (4, [4]), (6, [4, 2])],
)
def test_inline_keyboard_row_packing(navigation, count: int, rows: list[int]) -> None:
    """Inlined messages pack four buttons per row."""
    message = OptionsAppMessage(navigation)
    message.keyboard = [[]]
    for index in range(count):
        message.add_button(label=str(index), callback=StartMessage.run_and_notify)
    content = message.gen_inline_keyboard_content()
    assert isinstance(content, InlineKeyboardMarkup)
    assert [len(row) for row in content.inline_keyboard] == rows


def test_new_row_forces_break(navigation) -> None:
    """new_row starts a fresh row even when the current one is not full."""
    message = StartMessage(navigation)
    message.keyboard = [[]]
    message.add_button("a")
    message.add_button("b", new_row=True)
    assert [len(row) for row in message.keyboard] == [1, 1]


def test_inline_callback_data_format(navigation) -> None:
    """Inline buttons encode '<message-label>##<button-label>' as callback data."""
    message = OptionsAppMessage(navigation)
    message.keyboard = [[]]
    message.add_button(label="press", callback=StartMessage.run_and_notify)
    markup = message.gen_inline_keyboard_content()
    button = markup.inline_keyboard[0][0]
    assert button.callback_data == f"options{message.SEPARATOR}press"


def test_separator_in_label_raises(navigation) -> None:
    """A forbidden separator in a label raises ValueError when generating inline content."""
    message = OptionsAppMessage(navigation)
    message.keyboard = [[]]
    message.add_button(label=f"bad{message.SEPARATOR}label")
    with pytest.raises(ValueError):
        message.gen_inline_keyboard_content()


def test_web_app_reply_button(navigation) -> None:
    """A button with a valid web_app_url becomes a web-app KeyboardButton."""
    message = StartMessage(navigation)
    button = next(row[0] for row in message.gen_keyboard_content().keyboard if row[0].text == "webapp")
    assert button.web_app is not None
    assert button.web_app.url == StartMessage.URL


def test_web_app_inline_link_button(navigation) -> None:
    """An inline LINK button with a url is rendered as a url button (not callback)."""
    message = OptionsAppMessage(navigation)
    message.keyboard = [[]]
    message.add_button(label="link", btype=ButtonType.LINK, web_app_url="https://example.com")
    button = message.gen_inline_keyboard_content().inline_keyboard[0][0]
    assert button.url == "https://example.com"
    assert button.callback_data is None


def test_input_field_defaults_to_first_label(navigation) -> None:
    """When no input field is set, it defaults to the first button label."""
    message = StartMessage(navigation)
    message.input_field = ""
    message.gen_keyboard_content()
    assert message.input_field == "Action"


def test_input_field_disable(navigation) -> None:
    """The '<disable>' sentinel leaves the input-field placeholder unset."""
    message = StartMessage(navigation)
    message.input_field = "<disable>"
    content = message.gen_keyboard_content()
    assert content.input_field_placeholder is None


def test_has_expired() -> None:
    """has_expired reflects the time_alive timestamp and expiry period."""
    message = SecondMenuMessageStub()
    assert message.has_expired() is False  # time_alive not set yet
    message.is_alive()
    assert message.has_expired() is False
    message.time_alive -= datetime.timedelta(seconds=10)
    assert message.has_expired() is True


class SecondMenuMessageStub(SecondMenuMessage):
    """A SecondMenuMessage with a short expiry, built without a navigation handler."""

    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        # bypass the parent constructor to avoid needing a navigation handler
        from telegram_menu.models import BaseMessage

        BaseMessage.__init__(self, navigation=None, label="stub", expiry_period=datetime.timedelta(seconds=5))


@pytest.mark.asyncio
async def test_call_callback_sync_with_and_without_arg() -> None:
    """call_callback handles sync callbacks that do or do not accept the argument."""

    def with_arg(value: int) -> int:
        return value + 1

    def without_arg() -> str:
        return "ok"

    assert await call_callback(with_arg, 41) == 42
    assert await call_callback(without_arg, "ignored") == "ok"


@pytest.mark.asyncio
async def test_call_callback_async_with_and_without_arg() -> None:
    """call_callback handles async callbacks that do or do not accept the argument."""

    async def with_arg(value: int) -> int:
        return value * 2

    async def without_arg() -> str:
        return "async-ok"

    assert await call_callback(with_arg, 21) == 42
    assert await call_callback(without_arg, "ignored") == "async-ok"


@pytest.mark.asyncio
async def test_call_callback_not_callable_raises() -> None:
    """A non-callable callback raises TypeError."""
    with pytest.raises(TypeError):
        await call_callback(None, "x")
