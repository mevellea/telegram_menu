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

"""Test telegram_menu package."""

import asyncio
import datetime
import json
import logging
import unittest
from logging import Logger
from pathlib import Path
from typing import Any, Callable, Coroutine, List, Optional, Union

from telegram import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict

from telegram.ext._callbackcontext import CallbackContext
from telegram.ext._utils.types import BD, BT, CD, UD

import telegram_menu
from telegram_menu import BaseMessage, ButtonType, MenuButton, NavigationHandler, TelegramMenuSession
from telegram_menu._version import __raw_url__

KeyboardContent = List[Union[str, List[str]]]
UpdateCallback = Union[Callable[[Any], None], Coroutine[Any, Any, None]]
KeyboardTester = TypedDict("KeyboardTester", {"buttons": int, "output": List[int]})

ROOT_FOLDER = Path(__file__).parent.parent

UnitTestDict = TypedDict("UnitTestDict", {"description": str, "input": str, "output": str})
TypePackageLogger = TypedDict("TypePackageLogger", {"package": str, "level": int})


class MyNavigationHandler(NavigationHandler):
    """Example of navigation handler, extended with a custom "Back" command."""

    async def goto_back(self) -> int:
        """Do Go Back logic."""
        return await self.select_menu_button("Back")


class OptionsAppMessage(BaseMessage):
    """Options app message, show an example of a button with inline buttons."""

    LABEL = "options"

    def __init__(self, navigation: MyNavigationHandler, update_callback: Optional[List[UpdateCallback]] = None) -> None:
        """Init OptionsAppMessage class."""
        super().__init__(navigation, OptionsAppMessage.LABEL, inlined=True)

        self.play_pause = True
        if isinstance(update_callback, list):
            update_callback.append(self.app_update_display)

    async def app_update_display(self) -> None:
        """Update message content when callback triggered."""
        self._toggle_play_button()
        if await self.edit_message():
            self.is_alive()

    def kill_message(self) -> None:
        """Kill the message after this callback."""
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

    def sticker_default(self) -> str:
        """Display the default sticker."""
        self._toggle_play_button()
        return f"{__raw_url__}/resources/stats_default.webp"

    def picture_default(self) -> str:
        """Display the default picture."""
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
        """Toggle the first button between play and pause mode."""
        self.play_pause = not self.play_pause

    @staticmethod
    def action_poll(poll_answer: str) -> None:
        """Display poll answer."""
        logging.info(f"Answer is {poll_answer}")

    def update(self) -> str:
        """Update message content."""
        poll_question = "Select one option:"
        poll_choices = [":play_button: Option " + str(x) for x in range(6)]
        play_pause_button = ":play_button:" if self.play_pause else ":pause_button:"
        self.keyboard = [
            [
                MenuButton(play_pause_button, callback=self.sticker_default, btype=ButtonType.STICKER),
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

    def __init__(self, navigation: MyNavigationHandler) -> None:
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

    def __init__(self, navigation: MyNavigationHandler, update_callback: Optional[List[UpdateCallback]] = None) -> None:
        """Init ThirdMenuMessage class."""
        super().__init__(
            navigation,
            ThirdMenuMessage.LABEL,
            notification=False,
            expiry_period=datetime.timedelta(seconds=5),
            input_field="<disable>",  # use '<disable>' to leave the input field empty
        )

        self.action_message = ActionAppMessage(navigation)
        option_message = OptionsAppMessage(navigation, update_callback)
        self.add_button(label="Option", callback=option_message)
        self.add_button("Action", self.action_message)
        self.add_button_back()
        self.add_button("Back2", callback=navigation.goto_back)
        self.add_button_home()
        if update_callback:
            update_callback.append(self.app_update_display)

    async def app_update_display(self) -> None:
        """Update message content when callback triggered."""
        edited = await self.edit_message()
        if edited:
            self.is_alive()

    def update(self) -> str:
        """Update message content."""
        return "Third message"

    async def text_input(self, text: str, context: Optional[CallbackContext[BT, UD, CD, BD]] = None) -> None:
        """Process text received."""
        logging.info(f"Text received: {text}")
        await self.navigation.select_menu_button("Action")


class SecondMenuMessage(BaseMessage):
    """Second example of menu."""

    LABEL = "second_message"

    def __init__(self, navigation: MyNavigationHandler, update_callback: Optional[List[UpdateCallback]] = None) -> None:
        """Init SecondMenuMessage class."""
        super().__init__(
            navigation,
            SecondMenuMessage.LABEL,
            notification=False,
            picture=(ROOT_FOLDER / "resources" / "packages.png").resolve().as_posix(),
            expiry_period=datetime.timedelta(seconds=5),
            input_field="Enter an option",
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
    URL = "https://python-telegram-bot.org/static/webappbot"

    def __init__(self, navigation: MyNavigationHandler, message_args: Optional[List[UpdateCallback]] = None) -> None:
        """Init StartMessage class."""
        super().__init__(navigation, StartMessage.LABEL)

        # define menu buttons
        action_message = ActionAppMessage(navigation)
        second_menu = SecondMenuMessage(navigation, update_callback=message_args)
        self.add_button(label="Action", callback=action_message)
        self.add_button(label="Second menu", callback=second_menu)
        self.add_button(label="webapp", callback=self.webapp_cb, web_app_url=self.URL)

    @staticmethod
    async def webapp_cb(webapp_data):
        """Webapp callback."""
        data = json.loads(webapp_data)
        return (
            f"You selected the color with the HEX value <code>{data['hex']}</code>. "
            f"The corresponding RGB value is <code>{tuple(data['rgb'].values())}</code>."
        )

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
    navigation: MyNavigationHandler
    update_callback: List[UpdateCallback] = []

    def setUp(self) -> None:
        """Set-up the unit-test."""
        self.logger = init_logger(__name__)
        with (Path.home() / ".telegram_menu" / "key.txt").open() as key_h:
            self.api_key = key_h.read().strip()
        Test.session = TelegramMenuSession(api_key=self.api_key)

    def test_all(self):
        """Create the session, tests start once the client has opened the session."""
        asyncio.ensure_future(self.get_session(), loop=asyncio.get_event_loop())
        Test.session.start(StartMessage, Test.update_callback, navigation_handler_class=MyNavigationHandler)

    async def get_session(self):
        """Get the session."""
        self.logger.info("\n### Waiting for a manual request to start the Telegram session...\n")
        while not hasattr(Test, "navigation") or Test.navigation is None:
            nav = Test.session.get_session()
            if nav is not None:
                Test.navigation = nav
            else:
                await asyncio.sleep(1)
        await self.run_all()
        asyncio.get_event_loop().stop()

    async def run_all(self):
        """Run all unit-tests."""
        self._test_1_wrong_api_key()
        self._test_2_label_emoji()
        self._test_3_bad_start_message()
        await self._test_4_picture_path()
        self._test_5_keyboard_combinations()
        self._test_6_keyboard_combinations_inlined()
        await self._test_7_client_connection()

    def _test_1_wrong_api_key(self) -> None:
        """Test starting a client with wrong key."""
        with self.assertRaises(KeyError):
            TelegramMenuSession(None)  # type: ignore

        with self.assertRaises(KeyError):
            TelegramMenuSession(1234)  # type: ignore

    def _test_2_label_emoji(self) -> None:
        """Check replacement of emoji."""
        vectors: List[UnitTestDict] = [
            {"description": "No emoji", "input": "lbl", "output": "lbl"},
            {"description": "Invalid emoji", "input": ":lbl:", "output": ":lbl:"},
            {"description": "Empty string", "input": "", "output": ""},
            {"description": "Valid emoji", "input": ":robot:", "output": "🤖"},
            {"description": "Consecutive emoji", "input": ":robot:-:robot::", "output": "🤖-🤖:"},
            {"description": "Consecutive emoji 2", "input": ":robot: , :ghost:", "output": "🤖 , 👻"},
        ]
        for vector in vectors:
            button = MenuButton(label=vector["input"])
            self.assertEqual(button.label, vector["output"], vector["description"])

    # noinspection PyTypeChecker
    def _test_3_bad_start_message(self) -> None:
        """Test starting a client with bad start message."""
        manager = TelegramMenuSession(self.api_key)

        with self.assertRaises(telegram_menu.NavigationException):
            manager.start(MenuButton)

        with self.assertRaises(telegram_menu.NavigationException):
            manager.start(StartMessage, 1)

    async def _test_4_picture_path(self) -> None:
        """Test sending valid and invalid pictures."""
        if Test.session is None:
            self.fail("Telegram session not available")

        # test sending local files, valid and invalid
        vectors_local: List[str] = [
            (ROOT_FOLDER / "resources" / "packages.png").resolve().as_posix(),
            (ROOT_FOLDER / "setup.py").resolve().as_posix(),
        ]
        for vector in vectors_local:
            messages = await Test.session.broadcast_picture(vector)
            self.assertIsInstance(messages, List)
            self.assertEqual(len(messages), 1)
            self.assertIsInstance(messages[0], Message)

        # test sending remote urls, valid and invalid
        vectors_urls: List[str] = [
            f"{__raw_url__}/resources/classes.png",
            f"{__raw_url__}/setup.py",
        ]
        for vector in vectors_urls:
            messages = await Test.session.broadcast_picture(vector)
            self.assertIsInstance(messages, List)
            self.assertEqual(len(messages), 1)
            self.assertIsInstance(messages[0], Message)

        sticker_path = (ROOT_FOLDER / "resources" / "stats_default.webp").resolve().as_posix()
        messages = await Test.session.broadcast_sticker(sticker_path=sticker_path)
        self.assertIsInstance(messages, List)
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], Message)

    def _test_5_keyboard_combinations(self) -> None:
        """Run the client test."""
        if Test.session is None:
            self.fail("Telegram session not available")
        vectors_inlined: List[KeyboardTester] = [
            {"buttons": 2, "output": [2]},
            {"buttons": 4, "output": [2, 2]},
            {"buttons": 7, "output": [2, 2, 2, 1]},
        ]
        for vector in vectors_inlined:
            msg_test = StartMessage(Test.navigation)
            msg_test.keyboard = []
            for _ in range(vector["buttons"]):
                msg_test.add_button(label=str(_), callback=StartMessage.run_and_notify)
            if msg_test.inlined:
                content = msg_test.gen_inline_keyboard_content()
            else:
                content = msg_test.gen_keyboard_content()
            self.assertTrue(isinstance(content, ReplyKeyboardMarkup))
            if isinstance(content, ReplyKeyboardMarkup):
                self.assertEqual([len(x) for x in content.keyboard], vector["output"], str(vector["buttons"]))

    def _test_6_keyboard_combinations_inlined(self) -> None:
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
            for _ in range(vector["buttons"]):
                msg_test.add_button(label=str(_), callback=StartMessage.run_and_notify)
            if msg_test.inlined:
                content = msg_test.gen_inline_keyboard_content()
            else:
                content = msg_test.gen_keyboard_content()
            self.assertTrue(isinstance(content, InlineKeyboardMarkup))
            if isinstance(content, InlineKeyboardMarkup):
                self.assertEqual([len(x) for x in content.inline_keyboard], vector["output"], str(vector["buttons"]))

    async def _test_7_client_connection(self) -> None:
        """Run the client test."""
        if not hasattr(Test, "session") or not hasattr(Test, "navigation"):
            self.fail("Telegram session not available")
        _navigation = Test.navigation

        # try broadcasting a message to all opened sessions
        msg_h = await Test.session.broadcast_message("Broadcast message")
        self.assertIsInstance(msg_h[0], Message)

        # select 'Action' menu from home, check that level is still 'Home' since flag 'home_after' is True
        msg_home = await _navigation.select_menu_button("Action")
        self.assertNotEqual(msg_home, -1)
        await asyncio.sleep(0.5)

        await self.go_check_id(label="Home", expected_id=msg_home)

        # Open second menu and check that message id has increased
        msg_menu2_id = await _navigation.select_menu_button("Second menu")
        self.assertGreater(msg_menu2_id, 1)
        await asyncio.sleep(0.5)

        # Open third menu and check that message id has increased
        msg_menu3_id = await _navigation.select_menu_button("Third menu")
        self.assertGreater(msg_menu3_id, msg_menu2_id)
        await asyncio.sleep(0.5)

        # Select option button and check that message id has increased
        msg_option_id = await _navigation.select_menu_button("Option")
        self.assertGreater(msg_option_id, msg_menu3_id)
        await asyncio.sleep(0.5)

        # go back from each sub-menu
        await self.go_check_id(label="Back")
        await self.go_check_id(label="Back")

        # go home from each sub-menu
        await self.go_check_id(label="Second menu")
        await self.go_check_id(label="Home")

        await self.go_check_id(label="Second menu")
        await self.go_check_id(label="Third menu")
        await self.go_check_id(label="Home")

        await self.go_check_id(label="Second menu")
        await self.go_check_id(label="Third menu")
        await self.go_check_id(label="Option")
        await asyncio.sleep(0.5)

        # run the update callback to trigger edition
        for callback in Test.update_callback:
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()

    async def go_check_id(self, label: str, expected_id: Optional[int] = None) -> None:
        """Select an entry."""
        msg_id = await Test.navigation.select_menu_button(label)
        if expected_id is not None:
            self.assertEqual(msg_id, expected_id)
        await asyncio.sleep(0.2)


def init_logger(current_logger) -> Logger:
    """Initialize logger properties."""
    _packages: List[TypePackageLogger] = [
        {"package": "apscheduler", "level": logging.WARNING},
        {"package": "telegram_menu", "level": logging.DEBUG},
        {"package": current_logger, "level": logging.DEBUG},
    ]
    log_formatter = logging.Formatter(
        fmt="%(asctime)s [%(name)s] [%(levelname)s]  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    _logger = logging.getLogger(current_logger)
    for _package in _packages:
        _logger = logging.getLogger(_package["package"])
        _logger.setLevel(_package["level"])
        _logger.addHandler(console_handler)
        _logger.propagate = False
    return _logger


def format_list(args_array: KeyboardContent) -> str:
    """Format array of strings in html, first element bold."""
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
