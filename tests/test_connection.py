#!/usr/bin/env python3

"""Test telegram_menu package."""

import datetime
import logging
import os
import re
import time
import unittest
from pathlib import Path
from typing import IO, Any, Dict, List, Optional, Union

import telegram
from typing_extensions import TypedDict

from telegram_menu import BaseMessage, ButtonType, MenuButton, NavigationHandler, TelegramMenuSession
from telegram_menu._version import __raw_url__, __url__

KeyboardContent = List[Union[str, List[str]]]
KeyboardTester = TypedDict("KeyboardTester", {"buttons": int, "output": List[int]})

ROOT_FOLDER = Path(__file__).parent.parent

UnitTestDict = TypedDict("UnitTestDict", {"description": str, "input": str, "output": str})
TypePackageLogger = TypedDict("TypePackageLogger", {"package": str, "level": int})


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
        return f"{__raw_url__}/resources/classes.png"

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
        self.shared_content: str = ""

    def update(self) -> str:
        """Update message content."""
        content = f"[{self.shared_content}]" if self.shared_content else ""
        return f"<code>Action! {content}</code>"


class ThirdMenuMessage(BaseMessage):
    """Third level of menu."""

    LABEL = "third_message"

    def __init__(self, navigation: NavigationHandler, update_callback: Optional[List[Any]] = None) -> None:
        """Init ThirdMenuMessage class."""
        super().__init__(
            navigation, ThirdMenuMessage.LABEL, notification=False, expiry_period=datetime.timedelta(seconds=5)
        )

        self.action_message = ActionAppMessage(self._navigation)
        option_message = OptionsAppMessage(self._navigation, update_callback)
        self.add_button(label="Option", callback=option_message)
        self.add_button("Action", self.action_message)
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
        return "Third message"

    def text_input(self, text: str) -> None:
        """Process text received."""
        self.action_message.shared_content = text
        self._navigation.select_menu_button("Action")


class SecondMenuMessage(BaseMessage):
    """Second example of menu."""

    LABEL = "second_message"

    def __init__(self, navigation: NavigationHandler, update_callback: Optional[List[Any]] = None) -> None:
        """Init SecondMenuMessage class."""
        super().__init__(
            navigation, SecondMenuMessage.LABEL, notification=False, expiry_period=datetime.timedelta(seconds=5)
        )

        third_menu = ThirdMenuMessage(navigation, update_callback)
        self.add_button(label="Third menu", callback=third_menu, new_row=True)
        self.add_button_back(new_row=True)
        self.add_button_home()

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

    session: TelegramMenuSession
    navigation: NavigationHandler
    update_callback: List[Any] = []

    def setUp(self) -> None:
        """Initialize the test session, create the telegram instance if it does not exist."""
        with (Path.home() / ".telegram_menu" / "key.txt").open() as key_h:
            self.api_key = key_h.read().strip()

        if not hasattr(Test, "session"):
            init_logger()
            Test.session = TelegramMenuSession(api_key=self.api_key)

            # create the session with the start message, 'update_callback' is used to testing prupose only here.
            Test.session.start(start_message_class=StartMessage, start_message_args=Test.update_callback)

            print("\n### Waiting for a manual request to start the Telegram session...\n")
            while not hasattr(Test, "navigation") or Test.navigation is None:
                nav = Test.session.get_session()
                if nav is not None:
                    Test.navigation = nav
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
            f"{__raw_url__}/resources/classes.png",
            f"{__raw_url__}/setup.py",
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
            content = msg_test.gen_keyboard_content()
            self.assertTrue(isinstance(content, telegram.ReplyKeyboardMarkup))
            if isinstance(content, telegram.ReplyKeyboardMarkup):
                self.assertEqual([len(x) for x in content.keyboard], vector["output"], str(vector["buttons"]))

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
            content = msg_test.gen_keyboard_content()
            self.assertTrue(isinstance(content, telegram.InlineKeyboardMarkup))
            if isinstance(content, telegram.InlineKeyboardMarkup):
                self.assertEqual([len(x) for x in content.inline_keyboard], vector["output"], str(vector["buttons"]))

    def test_6_client_connection(self) -> None:
        """Run the client test."""
        if not hasattr(Test, "session") or not hasattr(Test, "navigation"):
            self.fail("Telegram session not available")
        _navigation = Test.navigation

        # try broadcasting a message to all opened sessions
        msg_h = Test.session.broadcast_message("Broadcast message")
        self.assertIsInstance(msg_h[0], telegram.message.Message)

        # select 'Action' menu from home, check thay level is still 'Home' since flag 'home_after' is True
        msg_home = _navigation.select_menu_button("Action")
        self.assertEqual(msg_home, -1)
        time.sleep(0.5)

        self.go_check_id(label="Home", expected_id=msg_home)

        # Open second menu and check that message id has increased
        msg_menu2_id = _navigation.select_menu_button("Second menu")
        self.assertGreater(msg_menu2_id, 1)
        time.sleep(0.5)

        # Open third menu and check that message id has increased
        msg_menu3_id = _navigation.select_menu_button("Third menu")
        self.assertGreater(msg_menu3_id, msg_menu2_id)
        time.sleep(0.5)

        # Select option button and check that message id has increased
        msg_option_id = _navigation.select_menu_button("Option")
        self.assertGreater(msg_option_id, msg_menu3_id)
        time.sleep(0.5)

        # go back from each sub-menu
        self.go_check_id(label="Back")
        self.go_check_id(label="Back")

        # go home from heach sub-menu
        self.go_check_id(label="Second menu")
        self.go_check_id(label="Home")

        self.go_check_id(label="Second menu")
        self.go_check_id(label="Third menu")
        self.go_check_id(label="Home")

        self.go_check_id(label="Second menu")
        self.go_check_id(label="Third menu")
        self.go_check_id(label="Option")
        time.sleep(0.5)

        # run the update callback to trigger edition
        for callback in Test.update_callback:
            callback()

        Test.session.updater.stop()
        logging.info("Test finished")

    def go_check_id(self, label: str, expected_id: Optional[int] = None) -> None:
        msg_id = Test.navigation.select_menu_button(label)
        if expected_id is not None:
            self.assertEqual(msg_id, expected_id)
        time.sleep(0.2)


def init_logger() -> None:
    """Initialize logger properties."""
    _packages: List[TypePackageLogger] = [
        {"package": "apscheduler", "level": logging.WARNING},
        {"package": "telegram_menu", "level": logging.DEBUG},
    ]
    log_formatter = logging.Formatter(
        fmt="%(asctime)s [%(name)s] [%(levelname)s]  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    for _package in _packages:
        _logger = logging.getLogger(_package["package"])
        _logger.setLevel(_package["level"])
        _logger.addHandler(console_handler)
        _logger.propagate = False


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
