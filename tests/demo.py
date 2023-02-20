#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2023 Armel Mevellec
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

"""telegram_menu demonstrator."""

from pathlib import Path

from telegram_menu import TelegramMenuSession
from tests.test_connection import MyNavigationHandler, StartMessage, init_logger


def run() -> None:
    """Run the demo example."""
    logger = init_logger(__name__)

    with (Path.home() / ".telegram_menu" / "key.txt").open() as key_h:
        api_key = key_h.read().strip()

    logger.info(" >> Start the demo and wait forever, quit with CTRL+C...")
    TelegramMenuSession(api_key).start(start_message_class=StartMessage, navigation_handler_class=MyNavigationHandler)


if __name__ == "__main__":
    run()
