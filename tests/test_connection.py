#!/usr/bin/env python3

"""Test telegram_menu package."""

import datetime
import logging
import os
import re
import time
import unittest
from pathlib import Path
from typing import IO, Any, Dict, List, Optional, TypedDict, Union

import telegram
from typing_extensions import TypedDict

from telegram_menu import BaseMessage, ButtonType, MenuButton, NavigationHandler, TelegramMenuSession
from telegram_menu._version import __url__

KeyboardContent = List[Union[str, List[str]]]
KeyboardTester = TypedDict("KeyboardTester", {"buttons": int, "output": List[int]})

ROOT_FOLDER = Path(__file__).parent.parent

UnitTestDict = TypedDict("UnitTestDict", {"description": str, "input": str, "output": str})


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
        self._toggle_play_button()
        if self.edit_message():
            self.is_alive()

    def kill_message(self) -> None:
        """Kill message after this callback."""
        self._toggle_play_button()

    def action_button(self) -> str:
        """Execute an action and return notification content."""
        self._toggle_play_button()
        return "option selected!"

    def text_button(self) -> str:
        """Display any text data."""
        self._toggle_play_button()
        data: KeyboardContent = [["text1", "value1"], ["text2", "value2"]]
        return format_list(data)

    def picture_default(self) -> str:
        """Display the deafult picture."""
        self._toggle_play_button()
        return "invalid_picture_path"

    def picture_button(self) -> str:
        """Display a local picture."""
        self._toggle_play_button()
        return (ROOT_FOLDER / "resources" / "packages.png").resolve().as_posix()

    def picture_button2(self) -> str:
        """Display a picture from a remote url."""
        self._toggle_play_button()
        return r"https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/classes.png"

    def _toggle_play_button(self) -> None:
        """Toogle the first button between play and pause mode."""
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
            [
                MenuButton(play_pause_button, callback=self.action_button),
                MenuButton(":twisted_rightwards_arrows:", callback=self.picture_default, btype=ButtonType.PICTURE),
                MenuButton(":chart_with_upwards_trend:", callback=self.picture_button, btype=ButtonType.PICTURE),
                MenuButton(":chart_with_downwards_trend:", callback=self.picture_button2, btype=ButtonType.PICTURE),
            ]
        ]
        self.add_button(":door:", callback=self.text_button, btype=ButtonType.MESSAGE)
        self.add_button(":speaker_medium_volume:", callback=self.action_button)
        self.add_button(":question:", self.action_poll, btype=ButtonType.POLL, args=[poll_question, poll_choices])
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
        self.add_button("Action", action_message)
        self.add_button_back()
        self.add_button_home()
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

    @staticmethod
    def run_and_notify() -> str:
        """Update message content."""
        return "This is a notification"

    def update(self) -> str:
        """Update message content."""
        return "Start message!"


class Test(unittest.TestCase):
    """The basic class that inherits unittest.TestCase."""

    session: Optional["TelegramMenuSession"] = None
    navigation: Optional["NavigationHandler"] = None
    update_callback: List[Any] = []

    def setUp(self) -> None:
        """Initialize the test session, create the telegram instance if it does not exist."""
        init_logger()
        with (Path.home() / ".telegram_menu" / "key.txt").open() as key_h:
            self.api_key = key_h.read().strip()

        if Test.session is None:
            Test.session = TelegramMenuSession(api_key=self.api_key)
            Test.session.start(start_message_class=StartMessage, start_message_args=Test.update_callback)

            print("\n### Waiting for a manual request to start the Telegram session...\n")
            while not Test.navigation:
                Test.navigation = Test.session.get_session()
                time.sleep(1)

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
        vectors: List[UnitTestDict] = [
            {"description": "No emoji", "input": "lbl", "output": "lbl"},
            {"description": "Invalid emoji", "input": ":lbl:", "output": ":lbl:"},
            {"description": "Empty string", "input": "", "output": ""},
            {"description": "Valid emoji", "input": ":play_button:", "output": "▶"},
            {"description": "Consecutive emoji", "input": ":play_button:-:play_button::", "output": "▶-▶:"},
            {"description": "Consecutive emoji 2", "input": ":play_button: , :pause_button:", "output": "▶ , ⏸"},
        ]
        for vector in vectors:
            button = MenuButton(label=vector["input"])
            self.assertEqual(button.label, vector["output"], vector["description"])

    def test_3_bad_start_message(self) -> None:
        """Test starting a client with bad start message."""
        manager = TelegramMenuSession(self.api_key)

        with self.assertRaises(AttributeError):
            manager.start(MenuButton)

        with self.assertRaises(AttributeError):
            manager.start(StartMessage, 1)

        manager.updater.stop()

    def test_4_picture_path(self) -> None:
        """Test sending valid and invalid pictures."""
        if Test.session is None:
            self.fail("Telegram session not available")

        # test sending local files, valid and invalid
        vectors_local: List[str] = [
            (ROOT_FOLDER / "resources" / "packages.png").resolve().as_posix(),
            (ROOT_FOLDER / "setup.py").resolve().as_posix(),
        ]
        for vector in vectors_local:
            messages = Test.session.broadcast_picture(vector)
            self.assertIsInstance(messages, List)
            self.assertEqual(len(messages), 1)
            self.assertIsInstance(messages[0], telegram.Message)

        # test sending remote urls, valid and invalid
        vectors_urls: List[str] = [
            "https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/classes.png",
            "https://raw.githubusercontent.com/mevellea/telegram_menu/master/setup.py",
        ]
        for vector in vectors_urls:
            messages = Test.session.broadcast_picture(vector)
            self.assertIsInstance(messages, List)
            self.assertEqual(len(messages), 1)
            self.assertIsInstance(messages[0], telegram.Message)

    def test_5_keyboard_combinations(self) -> None:
        """Run the client test."""
        if Test.session is None or Test.navigation is None:
            self.fail("Telegram session not available")
        vectors_inlined: List[KeyboardTester] = [
            {"buttons": 2, "output": [2]},
            {"buttons": 4, "output": [2, 2]},
            {"buttons": 7, "output": [2, 2, 2, 1]},
        ]
        for vector in vectors_inlined:
            msg_test = StartMessage(Test.navigation)
            msg_test.keyboard = []
            for x in range(vector["buttons"]):
                msg_test.add_button(label=str(x), callback=StartMessage.run_and_notify)
            self.assertEqual(
                [len(x) for x in msg_test.gen_keyboard_content().keyboard],
                vector["output"],
                str(vector["buttons"]),
            )

    def test_5_keyboard_combinations_inlined(self) -> None:
        """Run the client test."""
        if Test.session is None or Test.navigation is None:
            self.fail("Telegram session not available")
        vectors_inlined: List[KeyboardTester] = [
            {"buttons": 2, "output": [2]},
            {"buttons": 4, "output": [4]},
            {"buttons": 6, "output": [4, 2]},
        ]
        for vector in vectors_inlined:
            msg_test = ActionAppMessage(Test.navigation)
            msg_test.keyboard = []
            for x in range(vector["buttons"]):
                msg_test.add_button(label=str(x), callback=StartMessage.run_and_notify)
            self.assertEqual(
                [len(x) for x in msg_test.gen_keyboard_content().inline_keyboard],
                vector["output"],
                str(vector["buttons"]),
            )

    def test_6_client_connection(self) -> None:
        """Run the client test."""
        if Test.session is None or Test.navigation is None:
            self.fail("Telegram session not available")
        _navigation = Test.navigation

        Test.session.broadcast_message("Broadcast message")
        msg_id = _navigation.select_menu_button("Action")
        self.assertGreater(msg_id, 1)

        time.sleep(0.5)
        Test.session.broadcast_message("Test message")
        time.sleep(0.5)
        _navigation.select_menu_button("Action")
        time.sleep(0.5)
        _navigation.select_menu_button("Second menu")
        time.sleep(0.5)
        _navigation.select_menu_button("Back")
        time.sleep(0.5)
        _navigation.select_menu_button("Second menu")
        time.sleep(0.5)
        _navigation.select_menu_button("Home")
        time.sleep(0.5)
        _navigation.select_menu_button("Second menu")
        time.sleep(0.5)
        _navigation.goto_home()
        time.sleep(0.5)
        _navigation.select_menu_button("Second menu")
        time.sleep(0.5)
        _navigation.select_menu_button("Option")
        time.sleep(0.5)

        # run the update callback to trigger edition
        for callback in Test.update_callback:
            callback()

        Test.session.updater.stop()
        logging.info("Test finished")


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
