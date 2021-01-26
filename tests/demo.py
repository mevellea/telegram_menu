#!/usr/bin/env python3

"""telegram_menu demonstrator."""

import logging
import os
import time
from pathlib import Path

from telegram_menu import TelegramMenuSession
from tests.test_connection import StartMessage, init_logger


def run() -> None:
    """Run the demo example."""
    init_logger()
    with (Path.home() / ".telegram_menu" / "key.txt").open() as key_h:
        api_key = key_h.read().strip()

    logging.info(" >> Start the demo and wait forever, quit with CTRL+C...")
    TelegramMenuSession(api_key).start(StartMessage)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    run()
