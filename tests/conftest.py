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

"""Shared pytest fixtures: a fully mocked Telegram bot and scheduler, no network needed."""

from __future__ import annotations

import itertools
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat

from telegram_menu import NavigationHandler


def make_message(message_id: int) -> SimpleNamespace:
    """Build a minimal stand-in for a telegram.Message."""
    return SimpleNamespace(message_id=message_id, poll=None)


@pytest.fixture
def message_ids() -> itertools.count:
    """Counter producing increasing message ids."""
    return itertools.count(1)


@pytest.fixture
def bot(message_ids: itertools.count) -> MagicMock:
    """A mock Telegram Bot whose send_* methods return messages with increasing ids."""
    mock_bot = MagicMock(name="Bot")

    async def _send(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return make_message(next(message_ids))

    mock_bot.send_message = AsyncMock(side_effect=_send)
    mock_bot.send_photo = AsyncMock(side_effect=_send)
    mock_bot.send_sticker = AsyncMock(side_effect=_send)
    mock_bot.send_poll = AsyncMock(side_effect=_send)
    mock_bot.edit_message_text = AsyncMock(return_value=make_message(0))
    mock_bot.edit_message_caption = AsyncMock(return_value=make_message(0))
    mock_bot.delete_message = AsyncMock(return_value=True)
    mock_bot.answer_callback_query = AsyncMock(return_value=True)
    mock_bot.send_chat_action = AsyncMock(return_value=True)
    return mock_bot


@pytest.fixture
def scheduler() -> MagicMock:
    """A mock APScheduler scheduler."""
    mock_scheduler = MagicMock(name="Scheduler")
    mock_scheduler.get_job.return_value = None
    mock_scheduler.running = False
    return mock_scheduler


@pytest.fixture
def chat() -> Chat:
    """A private chat for the test user."""
    return Chat(id=123456, type=Chat.PRIVATE, first_name="Tester")


@pytest.fixture
def navigation(bot: MagicMock, chat: Chat, scheduler: MagicMock) -> NavigationHandler:
    """A NavigationHandler wired to the mock bot/scheduler."""
    return NavigationHandler(bot, chat, scheduler)
