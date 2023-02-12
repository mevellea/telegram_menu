#!/usr/bin/env python3

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
