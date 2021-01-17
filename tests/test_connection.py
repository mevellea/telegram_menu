#!/usr/bin/env python3

"""Test telegram_menu package."""

import datetime
import logging
import os
import time
import unittest
from typing import Any, List, Optional, Union

from telegram_menu import BaseMessage, ButtonType, MenuButton, NavigationHandler, TelegramMenuSession

KeyboardContent = List[Union[str, List[str]]]


class OptionsAppMessage(BaseMessage):
    """Options app message, show an example of a button with inline buttons."""

    LABEL = "options"

    def __init__(self, navigation: NavigationHandler, update_callback: Optional[List[Any]] = None) -> None:
        """Init OptionsAppMessage class."""
        super().__init__(navigation, OptionsAppMessage.LABEL, inlined=True)

        self.play_pause = True
        if update_callback:
            update_callback.append(self.app_update_display)

    def app_update_display(self) -> None:
        """Update message content when callback triggered."""
        self.play_pause = not self.play_pause
        edited = self.edit_message()
        if edited:
            self.is_alive()

    def kill_message(self) -> None:
        """Kill message after this callback."""
        self.play_pause = not self.play_pause

    def action_button(self) -> str:
        """Execute an action and return notification content."""
        self.play_pause = not self.play_pause
        return "option selected!"

    def text_button(self) -> str:
        """Display any text data."""
        self.play_pause = not self.play_pause
        data: KeyboardContent = [["text1", "value1"], ["text2", "value2"]]
        return format_list(data)

    def picture_button(self) -> str:
        """Display a picture."""
        self.play_pause = not self.play_pause
        return "resources/stats_default.png"

    def picture_button2(self) -> None:
        """Display an undefined picture."""
        self.play_pause = not self.play_pause

    @staticmethod
    def action_poll(poll_answer: str) -> None:
        """Display poll answer."""
        logging.info("Answer is %s", poll_answer)

    def update(self) -> str:
        """Update message content."""
        poll_question = "Select one option:"
        poll_choices = [":play_button: Option " + str(x) for x in range(6)]
        play_pause_button = ":play_button:" if self.play_pause else ":pause_button:"
        self.keyboard = [
            MenuButton(play_pause_button, callback=self.action_button),
            MenuButton(":twisted_rightwards_arrows:", callback=self.action_button),
            MenuButton(":chart_with_upwards_trend:", callback=self.picture_button, btype=ButtonType.PICTURE),
            MenuButton(":chart_with_downwards_trend:", callback=self.picture_button2, btype=ButtonType.PICTURE),
            MenuButton(":door:", callback=self.text_button, btype=ButtonType.MESSAGE),
            MenuButton(":speaker_medium_volume:", callback=self.action_button),
            MenuButton(
                ":question:",
                callback=self.action_poll,
                btype=ButtonType.POLL,
                args=[poll_question, poll_choices],
            ),
        ]
        return "Status updated!"


class ActionAppMessage(BaseMessage):
    """Single action message."""

    LABEL = "action"

    def __init__(self, navigation: NavigationHandler) -> None:
        """Init ActionAppMessage class."""
        super().__init__(
            navigation,
            ActionAppMessage.LABEL,
            expiry_period=datetime.timedelta(seconds=5),
            inlined=True,
            home_after=True,
        )

    def update(self) -> str:
        """Update message content."""
        return "<code>Action!</code>"


class SecondMenuMessage(BaseMessage):
    """Second example of menu."""

    LABEL = "second_message"

    def __init__(self, navigation: NavigationHandler, update_callback: Optional[List[Any]] = None) -> None:
        """Init SecondMenuMessage class."""
        super().__init__(
            navigation, SecondMenuMessage.LABEL, notification=False, expiry_period=datetime.timedelta(seconds=5)
        )

        action_message = ActionAppMessage(self._navigation)
        option_message = OptionsAppMessage(self._navigation, update_callback)
        self.add_button(label="Option", callback=option_message)
        self.add_button(label="Action", callback=action_message)
        self.add_button(label="Back")
        self.add_button(label="Home")
        if update_callback:
            update_callback.append(self.app_update_display)

    def app_update_display(self) -> None:
        """Update message content when callback triggered."""
        edited = self.edit_message()
        if edited:
            self.is_alive()

    def update(self) -> str:
        """Update message content."""
        return "Second message"


class StartMessage(BaseMessage):
    """Start menu, create all app sub-menus."""

    LABEL = "start"

    def __init__(self, navigation: NavigationHandler, update_callback: Optional[List[Any]] = None) -> None:
        """Init StartMessage class."""
        super().__init__(navigation, StartMessage.LABEL)

        # define menu buttons
        action_message = ActionAppMessage(navigation)
        second_menu = SecondMenuMessage(navigation, update_callback)
        self.add_button(label="Action", callback=action_message)
        self.add_button(label="Second menu", callback=second_menu)

    def update(self) -> str:
        """Update message content."""
        return "Start message!"


class Test(unittest.TestCase):
    """The basic class that inherits unittest.TestCase."""

    def setUp(self) -> None:
        key_file = os.path.join(os.path.expanduser("~"), ".telegram_menu", "key.txt")
        with open(key_file, "r") as key_h:
            self.api_key = key_h.read().strip()

    def test_1_wrong_api_key(self) -> None:
        """Test starting a client with wrong key."""
        with self.assertRaises(AttributeError):
            TelegramMenuSession(None)  # type: ignore

        with self.assertRaises(AttributeError):
            TelegramMenuSession(1234)  # type: ignore

        with self.assertRaises(AttributeError):
            TelegramMenuSession("1234:5678")

    def test_2_label_emoji(self) -> None:
        """Check replacement of emoji."""
        vectors = [
            {"input": "lbl", "output": "lbl"},
            {"input": ":lbl:", "output": ":lbl:"},
            {"input": "", "output": ""},
            {"input": ":play_button:", "output": "▶"},
            {"input": ":play_button:-:play_button::", "output": "▶-▶:"},
            {"input": ":play_button: , :pause_button:", "output": "▶ , ⏸"},
        ]
        for vector in vectors:
            button = MenuButton(label=vector["input"])
            self.assertEqual(button.label, vector["output"])

    def test_3_bad_start_message(self) -> None:
        """Test starting a client with bad start message."""
        manager = TelegramMenuSession(self.api_key)

        with self.assertRaises(AttributeError):
            manager.start(MenuButton)

        with self.assertRaises(AttributeError):
            manager.start(StartMessage, 1)

        manager.updater.stop()

    def test_4_client_connection(self) -> None:
        """Run the client test."""
        init_logger()

        update_callback: List[Any] = []
        session: Optional["NavigationHandler"] = None

        manager = TelegramMenuSession(api_key=self.api_key)
        manager.start(start_message_class=StartMessage, start_message_args=update_callback)
        while not session:
            session = manager.get_session()
            time.sleep(1)

        manager.broadcast_message("Broadcast message")
        manager.broadcast_picture("picture_path")
        msg_id = session.select_menu_button("Action")
        self.assertGreater(msg_id, 1)

        time.sleep(0.5)
        manager.broadcast_message("Test message")
        time.sleep(0.5)
        session.select_menu_button("Action")
        time.sleep(0.5)
        session.select_menu_button("Second menu")
        time.sleep(0.5)
        session.select_menu_button("Back")
        time.sleep(0.5)
        session.select_menu_button("Second menu")
        time.sleep(0.5)
        session.select_menu_button("Home")
        time.sleep(0.5)
        session.select_menu_button("Second menu")
        time.sleep(0.5)
        session.goto_home()
        time.sleep(0.5)
        session.select_menu_button("Second menu")
        time.sleep(0.5)
        session.select_menu_button("Option")
        time.sleep(0.5)

        # run the update callback to trigger edition
        for callback in update_callback:
            callback()

        time.sleep(20)

        manager.updater.stop()


def init_logger() -> None:
    """Initialize logger properties."""
    log_formatter = logging.Formatter(
        fmt="%(asctime)s [%(name)s] [%(levelname)s]  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    root_logger = logging.getLogger()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # start scheduler
    logging.getLogger("apscheduler.scheduler").setLevel(logging.ERROR)
    logging.getLogger("apscheduler.executors").setLevel(logging.ERROR)


def format_list(args_array: KeyboardContent) -> str:
    """Format array of strings in html, first element bold.

    Args:
        args_array: text content

    Returns:
        Message content as formatted string

    """
    content = ""
    for line in args_array:
        if not isinstance(line, list):
            content += f"<b>{line}</b>"
            continue
        if line[0]:
            content += f"<b>{line[0]}</b>"
            if line[1]:
                content += ": "
        if line[1]:
            content += line[1]
        content += "\n"
    return content
