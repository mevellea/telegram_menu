#!/usr/bin/env python3

"""telegram_menu demonstrator."""

import os
import time

from telegram_menu import TelegramMenuSession
from tests.test_connection import StartMessage


def run() -> None:
    """Run the demo example."""
    key_file = os.path.join(os.path.expanduser("~"), ".telegram_menu", "key.txt")
    with open(key_file, "r") as key_h:
        api_key = key_h.read().strip()

    print("Start the session and wait forever")
    TelegramMenuSession(api_key).start(StartMessage)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    run()
