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

"""Unit-tests for telegram_menu.navigation (mocked bot, no network)."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import telegram

from telegram_menu import BaseMessage, ButtonType
from telegram_menu._version import __raw_url__

from .example_app import ROOT_FOLDER, ActionAppMessage, MyNavigationHandler, StartMessage

WEBP_STICKER = (ROOT_FOLDER / "resources" / "stats_default.webp").resolve().as_posix()
LOCAL_PICTURE = (ROOT_FOLDER / "resources" / "packages.png").resolve().as_posix()


# --------------------------------------------------------------------------- menus


@pytest.mark.asyncio
async def test_goto_menu_text(navigation, bot) -> None:
    """goto_menu sends a text message and queues the menu."""
    message = StartMessage(navigation)
    msg_id = await navigation.goto_menu(message)
    assert msg_id == message.message_id > 0
    bot.send_message.assert_awaited_once()
    bot.send_photo.assert_not_called()
    assert navigation._menu_queue[-1] is message


@pytest.mark.asyncio
async def test_goto_menu_with_picture_uses_send_photo(navigation, bot) -> None:
    """A menu with a picture is sent through send_photo."""
    start = StartMessage(navigation)
    await navigation.goto_menu(start)
    second = next(b.callback for row in start.keyboard for b in row if b.label == "Second menu")
    await navigation.goto_menu(second)
    bot.send_photo.assert_awaited()


@pytest.mark.asyncio
async def test_goto_home_collapses_queue(navigation) -> None:
    """goto_home re-sends the home menu and collapses the queue to a single entry."""
    start = StartMessage(navigation)
    await navigation.goto_menu(start)
    await navigation.select_menu_button("Second menu")
    assert len(navigation._menu_queue) == 2
    await navigation.goto_home()
    assert len(navigation._menu_queue) == 1
    assert navigation._menu_queue[0].label == StartMessage.LABEL


@pytest.mark.asyncio
async def test_back_at_home_returns_home_id(navigation) -> None:
    """Selecting Back at the home level keeps the home message."""
    start = StartMessage(navigation)
    home_id = await navigation.goto_menu(start)
    assert await navigation.select_menu_button("Back") == home_id


@pytest.mark.asyncio
async def test_full_navigation_flow(navigation) -> None:
    """Walk down sub-menus, into an inline message, then back home."""
    start = StartMessage(navigation)
    await navigation.goto_menu(start)
    second_id = await navigation.select_menu_button("Second menu")
    third_id = await navigation.select_menu_button("Third menu")
    option_id = await navigation.select_menu_button("Option")
    assert second_id and third_id and option_id
    assert third_id > second_id
    assert option_id > third_id
    assert navigation.get_message("options_Option") is not None

    await navigation.select_menu_button("Back")
    assert navigation._menu_queue[-1].label == "second_message"
    await navigation.select_menu_button("Home")
    assert len(navigation._menu_queue) == 1


@pytest.mark.asyncio
async def test_select_action_with_home_after(navigation) -> None:
    """An inlined message with home_after returns to the home menu."""
    start = StartMessage(navigation)
    await navigation.goto_menu(start)
    await navigation.select_menu_button("Action")
    assert len(navigation._menu_queue) == 1


# --------------------------------------------------------------------------- callbacks


@pytest.mark.asyncio
async def test_function_callback_executed(navigation) -> None:
    """A plain function button callback is executed and returns 0."""
    triggered = AsyncMock()

    class Menu(StartMessage):
        def update(self, context=None) -> str:  # type: ignore[no-untyped-def]
            self.keyboard = [[]]
            self.add_button("Press", callback=triggered)
            return "menu"

    menu = Menu(navigation)
    await navigation.goto_menu(menu)
    result = await navigation.select_menu_button("Press")
    assert result == 0
    triggered.assert_awaited()


@pytest.mark.asyncio
async def test_capture_user_input_routes_to_text_input(navigation) -> None:
    """An unrecognised label is forwarded to the latest message's text_input."""
    received: list[str] = []

    class Menu(StartMessage):
        async def text_input(self, text, context=None) -> None:  # type: ignore[no-untyped-def]
            received.append(text)

    menu = Menu(navigation)
    await navigation.goto_menu(menu)
    assert await navigation.select_menu_button("free text") is None
    assert received == ["free text"]


# --------------------------------------------------------------------------- editing


@pytest.mark.asyncio
async def test_edit_message_unknown_returns_false(navigation) -> None:
    """Editing a message that is not queued returns False."""
    message = ActionAppMessage(navigation)
    assert await navigation.edit_message(message) is False


def test_message_check_changes(navigation) -> None:
    """_message_check_changes detects content/keyboard changes and stores the new state."""
    message = StartMessage(navigation)
    message.content_previous = "same"
    message.keyboard_previous = message.keyboard
    assert navigation._message_check_changes(message, "same") is False
    assert navigation._message_check_changes(message, "different") is True
    # after a detected change the new content is stored
    assert message.content_previous == "different"


# --------------------------------------------------------------------------- picture / sticker


def test_picture_check_replace_url_image(navigation) -> None:
    """A valid image url is kept as-is."""
    url = "https://example.com/photo.png"
    assert navigation._picture_check_replace(url) == url


def test_picture_check_replace_url_not_image(navigation) -> None:
    """A non-image url is replaced by the default picture."""
    result = navigation._picture_check_replace("https://example.com/page.txt")
    assert result == f"{__raw_url__}/resources/stats_default.png"


def test_picture_check_replace_local_file(navigation) -> None:
    """A local image file is read into bytes."""
    result = navigation._picture_check_replace(LOCAL_PICTURE)
    assert isinstance(result, bytes) and result.startswith(b"\x89PNG")


def test_picture_check_replace_invalid(navigation) -> None:
    """An invalid path is replaced by the default picture."""
    result = navigation._picture_check_replace("not-a-real-path")
    assert result == f"{__raw_url__}/resources/stats_default.png"


def test_sticker_check_replace_local_file(navigation) -> None:
    """A local .webp sticker is read into bytes."""
    result = navigation._sticker_check_replace(WEBP_STICKER)
    assert isinstance(result, bytes) and result.startswith(b"RIFF")


def test_sticker_check_replace_not_webp(navigation) -> None:
    """A non-webp sticker path is replaced by the default sticker."""
    result = navigation._sticker_check_replace(LOCAL_PICTURE)
    assert result == f"{__raw_url__}/resources/stats_default.webp"


def test_sticker_check_replace_url(navigation) -> None:
    """A .webp url is kept as-is."""
    url = "https://example.com/sticker.webp"
    assert navigation._sticker_check_replace(url) == url


@pytest.mark.asyncio
async def test_send_photo_bad_request_returns_none(navigation, bot) -> None:
    """send_photo swallows a BadRequest and returns None."""
    bot.send_photo = AsyncMock(side_effect=telegram.error.BadRequest("boom"))
    assert await navigation.send_photo(LOCAL_PICTURE) is None


# --------------------------------------------------------------------------- polls


@pytest.mark.asyncio
async def test_send_poll(navigation, bot) -> None:
    """send_poll expands emoji, calls the bot and schedules a deletion job."""
    await navigation.send_poll(question=":question: Pick", options=[":robot: a", "b"])
    bot.send_poll.assert_awaited_once()
    kwargs = bot.send_poll.await_args.kwargs
    assert kwargs["question"].startswith("❓")
    assert kwargs["options"][0].startswith("🤖")
    navigation.scheduler.add_job.assert_called()


@pytest.mark.asyncio
async def test_poll_answer_triggers_callback(navigation, bot, monkeypatch) -> None:
    """poll_answer calls the stored callback with the chosen option and cleans up."""
    monkeypatch.setattr("telegram_menu.navigation.asyncio.sleep", AsyncMock())
    answers: list[str] = []
    navigation._poll = SimpleNamespace(
        message_id=7,
        poll=SimpleNamespace(question="q", options=[SimpleNamespace(text="A"), SimpleNamespace(text="B")]),
    )
    navigation._poll_callback = answers.append
    await navigation.poll_answer(1)
    assert answers == ["B"]
    assert navigation._poll is None
    bot.delete_message.assert_awaited()


@pytest.mark.asyncio
async def test_poll_answer_without_poll_is_noop(navigation) -> None:
    """poll_answer is a no-op when no poll is active."""
    navigation._poll = None
    await navigation.poll_answer(0)  # must not raise


# --------------------------------------------------------------------------- misc


def test_filter_unicode(navigation) -> None:
    """filter_unicode strips non-ascii characters."""
    assert navigation.filter_unicode("héllo 🤖!") == "hllo !"


@pytest.mark.asyncio
async def test_expiry_checker_deletes_expired(navigation, bot) -> None:
    """The expiry checker deletes expired messages from the queue."""
    message = ActionAppMessage(navigation)
    message.message_id = 99
    message.is_alive()
    message.time_alive -= datetime.timedelta(minutes=30)
    navigation._message_queue.append(message)
    await navigation._expiry_date_checker()
    assert message not in navigation._message_queue
    bot.delete_message.assert_awaited_with(chat_id=navigation.chat_id, message_id=99)


def test_custom_navigation_handler(bot, chat, scheduler) -> None:
    """The handler can be subclassed (MyNavigationHandler) without breaking init."""
    handler = MyNavigationHandler(bot, chat, scheduler)
    assert handler.chat_id == chat.id
    assert handler.user_name == chat.first_name


def test_separator_constant() -> None:
    """The reserved separator is exposed on BaseMessage and ButtonType is an enum."""
    assert BaseMessage.SEPARATOR == "##"
    assert ButtonType.POLL in ButtonType
