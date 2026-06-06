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

"""Unit-tests for TelegramMenuSession construction and validation (no network)."""

from __future__ import annotations

import pytest

from telegram_menu import BaseMessage, MenuButton, NavigationException, TelegramMenuSession

from .example_app import StartMessage

DUMMY_TOKEN = "123456789:AAFakeTokenForTestingPurposesOnly0000000"


@pytest.fixture
def session(tmp_path) -> TelegramMenuSession:
    """A session backed by a temporary persistence file (never starts polling)."""
    return TelegramMenuSession(DUMMY_TOKEN, persistence_path=str(tmp_path / "persistence"))


def test_api_key_must_be_string() -> None:
    """A non-string API key raises KeyError."""
    with pytest.raises(KeyError):
        TelegramMenuSession(None)  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        TelegramMenuSession(1234)  # type: ignore[arg-type]


def test_session_registers_handlers(session: TelegramMenuSession) -> None:
    """A constructed session has a job-queue scheduler and registered handlers."""
    assert session.scheduler is not None
    assert session.sessions == []
    assert session.application.handlers  # at least one handler group registered


def test_start_rejects_non_basemessage(session: TelegramMenuSession) -> None:
    """start() requires a BaseMessage subclass as the start message class."""
    with pytest.raises(NavigationException):
        session.start(MenuButton, polling=False)  # type: ignore[arg-type]


def test_start_rejects_bad_args(session: TelegramMenuSession) -> None:
    """start() requires start_message_args to be a list."""
    with pytest.raises(NavigationException):
        session.start(StartMessage, start_message_args=1, polling=False)  # type: ignore[arg-type]


def test_start_rejects_bad_navigation_class(session: TelegramMenuSession) -> None:
    """start() requires navigation_handler_class to subclass NavigationHandler."""
    with pytest.raises(NavigationException):
        session.start(StartMessage, navigation_handler_class=BaseMessage, polling=False)  # type: ignore[arg-type]


def test_start_without_polling_does_not_start_scheduler_off_loop(session: TelegramMenuSession) -> None:
    """start(polling=False) must not raise when no event loop is running.

    Regression test: modern APScheduler's AsyncIOScheduler.start() requires a running
    loop, so the scheduler must not be started eagerly outside of one.
    """
    session.start(StartMessage, polling=False)
    assert session.scheduler.running is False
