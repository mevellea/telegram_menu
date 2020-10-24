#!/usr/bin/env python3

"""telegram_menu demonstrator."""

import time

from telegram_menu import TelegramMenuSession
from tests.test_connection import API_KEY, StartMessage


def run() -> None:
    """Run the demo example."""
    print("Start the session and wait forever")
    TelegramMenuSession(API_KEY).start(StartMessage)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    run()
