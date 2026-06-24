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

"""Example menu application, used by the demo and the unit-tests."""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Callable, Coroutine, List, Optional, Union

from telegram_menu import BaseMessage, ButtonType, Context, MenuButton, NavigationHandler
from telegram_menu._version import __raw_url__

KeyboardContent = List[Union[str, List[str]]]
UpdateCallback = Union[Callable[..., None], Coroutine[None, None, None]]

ROOT_FOLDER = Path(__file__).parent.parent
PACKAGES_PICTURE = (ROOT_FOLDER / "resources" / "packages.png").resolve().as_posix()


class MyNavigationHandler(NavigationHandler):
    """Example navigation handler, extended with a custom "Back" command."""

    async def goto_back(self) -> int:
        """Do the "Go Back" logic."""
        result = await self.select_menu_button("Back")
        return result if result is not None else -1


class OptionsAppMessage(BaseMessage):
    """Options app message, showing an inlined message with buttons."""

    LABEL = "options"

    def __init__(self, navigation: NavigationHandler, update_callback: Optional[List[UpdateCallback]] = None) -> None:
        """Init OptionsAppMessage class."""
        super().__init__(navigation, OptionsAppMessage.LABEL, inlined=True)
        self.play_pause = True
        if isinstance(update_callback, list):
            update_callback.append(self.app_update_display)

    async def app_update_display(self) -> None:
        """Update message content when the callback is triggered."""
        self._toggle_play_button()
        if await self.edit_message():
            self.is_alive()

    def kill_message(self) -> None:
        """Kill the message after this callback."""
        self._toggle_play_button()

    def action_button(self) -> str:
        """Execute an action and return a notification content."""
        self._toggle_play_button()
        return "option selected!"

    def text_button(self) -> str:
        """Display some text data."""
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
        return PACKAGES_PICTURE

    def picture_button2(self) -> str:
        """Display a picture from a remote url."""
        self._toggle_play_button()
        return f"{__raw_url__}/resources/classes.png"

    def _toggle_play_button(self) -> None:
        """Toggle the first button between play and pause mode."""
        self.play_pause = not self.play_pause

    @staticmethod
    def action_poll(poll_answer: str) -> None:
        """Display the poll answer."""
        logging.info("Answer is %s", poll_answer)

    def reaction_button(self) -> str:
        """Return the emoji used to react to this message."""
        self._toggle_play_button()
        return ":thumbs_up:"

    def document_button(self) -> str:
        """Return a document url to send."""
        self._toggle_play_button()
        return f"{__raw_url__}/README.md"

    def update(self, context: Context | None = None) -> str:
        """Update message content."""
        poll_question = "Select one option:"
        poll_choices = [":play_button: Option " + str(x) for x in range(6)]
        quiz_question = "What is 2 + 2?"
        quiz_choices = ["3", "4", "5"]
        quiz_options = {"poll_type": "quiz", "correct_option_id": 1, "explanation": "2 + 2 = 4"}
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
        self.add_button(
            ":brain:", self.action_poll, btype=ButtonType.POLL, args=[quiz_question, quiz_choices, quiz_options]
        )
        self.add_button(":thumbs_up:", callback=self.reaction_button, btype=ButtonType.REACTION)
        self.add_button(":page_facing_up:", callback=self.document_button, btype=ButtonType.DOCUMENT)
        self.add_button(":clipboard:", copy_text="telegram_menu", btype=ButtonType.COPY)
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

    def update(self, context: Context | None = None) -> str:
        """Update message content."""
        content = f"[{self.shared_content}]" if self.shared_content else ""
        return f"<code>Action! {content}</code>"


class ThirdMenuMessage(BaseMessage):
    """Third level of menu."""

    LABEL = "third_message"

    def __init__(self, navigation: NavigationHandler, update_callback: Optional[List[UpdateCallback]] = None) -> None:
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
        if isinstance(navigation, MyNavigationHandler):
            self.add_button("Back2", callback=navigation.goto_back)
        self.add_button_home()
        if update_callback:
            update_callback.append(self.app_update_display)

    async def app_update_display(self) -> None:
        """Update message content when the callback is triggered."""
        if await self.edit_message():
            self.is_alive()

    def update(self, context: Context | None = None) -> str:
        """Update message content."""
        return "Third message"

    async def text_input(self, text: str, context: Context | None = None) -> None:
        """Process the text received."""
        logging.info("Text received: %s", text)
        await self.navigation.select_menu_button("Action")


class SecondMenuMessage(BaseMessage):
    """Second example of menu."""

    LABEL = "second_message"

    def __init__(self, navigation: NavigationHandler, update_callback: Optional[List[UpdateCallback]] = None) -> None:
        """Init SecondMenuMessage class."""
        super().__init__(
            navigation,
            SecondMenuMessage.LABEL,
            notification=False,
            picture=PACKAGES_PICTURE,
            expiry_period=datetime.timedelta(seconds=5),
            input_field="Enter an option",
        )
        third_menu = ThirdMenuMessage(navigation, update_callback)
        self.add_button(label="Third menu", callback=third_menu, new_row=True)
        self.add_button_back(new_row=True)
        self.add_button_home()

    def update(self, context: Context | None = None) -> str:
        """Update message content."""
        return "Second message"


class StartMessage(BaseMessage):
    """Start menu, create all app sub-menus."""

    LABEL = "start"
    URL = "https://python-telegram-bot.org/static/webappbot"

    # Bot command menu shown next to the input field, registered via
    # TelegramMenuSession.start(commands=...). Only '/start' has a handler here; add your
    # own telegram.ext handlers on the application to support additional commands.
    COMMANDS = [
        ("start", "Start the bot and show the main menu"),
    ]

    def __init__(self, navigation: NavigationHandler, message_args: Optional[List[UpdateCallback]] = None) -> None:
        """Init StartMessage class."""
        super().__init__(navigation, StartMessage.LABEL)
        action_message = ActionAppMessage(navigation)
        second_menu = SecondMenuMessage(navigation, update_callback=message_args)
        self.add_button(label="Action", callback=action_message)
        self.add_button(label="Second menu", callback=second_menu)
        self.add_button(label="webapp", callback=self.webapp_cb, web_app_url=self.URL)

    @staticmethod
    async def webapp_cb(webapp_data: str) -> str:
        """Webapp callback."""
        data = json.loads(webapp_data)
        return (
            f"You selected the color with the HEX value <code>{data['hex']}</code>. "
            f"The corresponding RGB value is <code>{tuple(data['rgb'].values())}</code>."
        )

    @staticmethod
    def run_and_notify() -> str:
        """Return a notification message."""
        return "This is a notification"

    def update(self, context: Context | None = None) -> str:
        """Update message content."""
        return "Start message!"


def format_list(args_array: KeyboardContent) -> str:
    """Format an array of strings in HTML, the first element of each line in bold."""
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
