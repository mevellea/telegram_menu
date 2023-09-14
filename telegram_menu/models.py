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

"""Messages and navigation models."""

import asyncio
import datetime
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Coroutine, List, Optional, Union

import emoji
import tzlocal
import validators
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext._callbackcontext import CallbackContext
from telegram.ext._utils.types import BD, BT, CD, UD

if TYPE_CHECKING:
    from telegram_menu import NavigationHandler


logger = logging.getLogger(__name__)

TypeCallback = Optional[Union[Callable[..., Any], Coroutine[Any, Any, None], "BaseMessage"]]
TypeKeyboard = List[List["MenuButton"]]


async def call_function_EAFP(method: TypeCallback, par: Any, *args: Any, **kwargs: Any) -> Any:
    """Call a function that could be a coroutine and could not accept an argument."""
    if asyncio.iscoroutinefunction(method):
        try:
            return await method(*args, par, **kwargs)
        except TypeError:
            return await method(*args, **kwargs)
    else:
        try:
            return method(*args, par, **kwargs)  # type: ignore
        except TypeError:
            return method(*args, **kwargs)  # type: ignore


class ButtonType(Enum):
    """Button type enumeration."""

    NOTIFICATION = auto()
    MESSAGE = auto()
    PICTURE = auto()
    STICKER = auto()
    POLL = auto()
    LINK = auto()


@dataclass
class MenuButton:
    """Base button class, wrapper for label with callback.

    Args:
        label: button label
        callback: method called on button selection
        btype: button type
        args: argument passed to the callback
        notification: send notification to user
    """

    def __init__(
        self,
        label: str,
        callback: TypeCallback = None,
        btype: ButtonType = ButtonType.NOTIFICATION,
        args: Any = None,
        notification: bool = True,
        web_app_url: str = "",
    ):
        """Init MenuButton class."""
        self.label = emoji_replace(label)
        self.callback = callback
        self.btype = btype
        self.args = args
        self.notification = notification
        self.web_app_url = web_app_url


class BaseMessage(ABC):
    """Base message class, buttons array and label updater.

    Args:
        navigation: navigation manager
        label: message label
        picture: path of the picture to send. Leave None if no picure
                 should be sent
        expiry_period: duration before the message is deleted
        inlined: create an inlined message instead of a menu message
        home_after: go back to home menu after executing the action
        notification: show a notification in Telegram interface
    """

    EXPIRING_DELAY = 12  # minutes
    SEPARATOR = "##"

    time_alive: datetime.datetime

    def __init__(
        self,
        navigation: "NavigationHandler",
        label: str = "",
        picture: str = "",
        expiry_period: Optional[datetime.timedelta] = None,
        inlined: bool = False,
        home_after: bool = False,
        notification: bool = True,
        input_field: str = "",
        **args: Any,
    ) -> None:
        """Init BaseMessage class."""
        self.keyboard: TypeKeyboard = [[]]
        self.label = emoji_replace(label)
        self.inlined = inlined
        self.picture = picture
        self.notification = notification
        self.navigation = navigation
        self.input_field = input_field

        # previous values are used to check if it has changed, to skip sending identical message
        self.keyboard_previous: TypeKeyboard = [[]]
        self.content_previous: str = ""

        # if 'home_after' is True, the navigation manager goes back to
        # the main menu after this message has been sent
        self.home_after = home_after
        self.message_id = -1
        self.expiry_period = (
            expiry_period
            if isinstance(expiry_period, datetime.timedelta)
            else datetime.timedelta(minutes=self.EXPIRING_DELAY)
        )

        self._status = None

    @abstractmethod
    def update(self, context: Optional[CallbackContext[BT, UD, CD, BD]] = None) -> str:
        """Update message content with HTML formatting. It can be also implemented as a coroutine (async) method."""
        raise NotImplementedError

    async def get_updated_content(self, context: Optional[CallbackContext[BT, UD, CD, BD]] = None) -> str:
        """Update method that detects if update is a coroutine or not and calls it doing also the emoji replacement."""
        v = await call_function_EAFP(self.update, context)
        return emoji_replace(v) if v else v

    async def text_input(self, text: str, context: Optional[CallbackContext[BT, UD, CD, BD]] = None) -> None:
        """Receive text from console. If used, this function must be instantiated in the child class."""

    def get_button(self, label: str) -> Optional[MenuButton]:
        """Get button matching given label."""
        return next(iter(y for x in self.keyboard for y in x if y.label == label), None)

    def add_button_back(self, **args: Any) -> None:
        """Add a button to go back to previous menu."""
        self.add_button(label="Back", callback=None, **args)

    def add_button_home(self, **args: Any) -> None:
        """Add a button to go back to main menu."""
        self.add_button(label="Home", callback=None, **args)

    def add_button(
        self,
        label: str,
        callback: TypeCallback = None,
        btype: ButtonType = ButtonType.NOTIFICATION,
        args: Any = None,
        notification: bool = True,
        new_row: bool = False,
        web_app_url: str = "",
    ) -> None:
        """Add a button to keyboard attribute.

        Args:
            label: button label
            callback: method called on button selection
            btype: button type
            args: argument passed to the callback
            notification: send notification to user
            new_row: add a new row
            web_app_url: URL of the web-app
        """
        # arrange buttons per row, depending on inlined property
        buttons_per_row = 2 if not self.inlined else 4

        if not isinstance(self.keyboard, list) or not self.keyboard:
            self.keyboard = [[]]

        # add new row if last row is full or append to last row
        if new_row or len(self.keyboard[-1]) == buttons_per_row:
            self.keyboard.append([MenuButton(label, callback, btype, args, notification, web_app_url)])
        else:
            self.keyboard[-1].append(MenuButton(label, callback, btype, args, notification, web_app_url))

    async def edit_message(self) -> bool:
        """Request navigation controller to update current message."""
        return await self.navigation.edit_message(self)

    def gen_keyboard_content(self) -> ReplyKeyboardMarkup:
        """Generate keyboard content."""
        keyboard_buttons = []
        for row in self.keyboard:
            if not self.input_field and row:
                self.input_field = row[0].label
            button_array: List[KeyboardButton] = []
            for btn in row:
                if btn.web_app_url and validators.url(btn.web_app_url):
                    button_array.append(KeyboardButton(text=btn.label, web_app=WebAppInfo(url=btn.web_app_url)))
                else:
                    button_array.append(KeyboardButton(text=btn.label))
            keyboard_buttons.append(button_array)
        if self.input_field and self.input_field != "<disable>":
            return ReplyKeyboardMarkup(
                keyboard=keyboard_buttons, resize_keyboard=True, input_field_placeholder=self.input_field
            )
        return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

    def gen_inline_keyboard_content(self) -> InlineKeyboardMarkup:
        """Generate keyboard content."""
        keyboard_buttons = []
        for row in self.keyboard:
            if not self.input_field and row:
                self.input_field = row[0].label
            button_array: List[InlineKeyboardButton] = []
            for btn in row:
                if self.SEPARATOR in self.label or self.SEPARATOR in btn.label:
                    raise ValueError(f"Forbidden character: {self.SEPARATOR}")
                lbl = f"{self.label}{self.SEPARATOR}{btn.label}"
                if btn.web_app_url and validators.url(btn.web_app_url):
                    if btn.btype == ButtonType.LINK:
                        button_array.append(InlineKeyboardButton(text=btn.label, url=btn.web_app_url))
                    else:
                        # do not use callback_data as it is not supported
                        button_array.append(
                            InlineKeyboardButton(text=btn.label, web_app=WebAppInfo(url=btn.web_app_url))
                        )
                else:
                    button_array.append(InlineKeyboardButton(text=btn.label, callback_data=lbl))
            keyboard_buttons.append(button_array)
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    def is_alive(self) -> None:
        """Update message timestamp."""
        self.time_alive = datetime.datetime.now(tz=tzlocal.get_localzone())

    def has_expired(self) -> bool:
        """Return True if expiry date of message has expired."""
        if self.time_alive is not None:
            return self.time_alive + self.expiry_period < datetime.datetime.now(tz=tzlocal.get_localzone())
        return False

    def kill_message(self) -> None:
        """Display status before message is destroyed."""
        logger.debug(f"Removing message '{self.label}' ({self.message_id})")


def emoji_replace(label: str) -> str:
    """Replace emoji token with utf-16 code."""
    match_emoji = re.findall(r"(:\w+:)", label)
    for item in match_emoji:
        emoji_str = emoji.emojize(item, language="alias")
        label = label.replace(item, emoji_str)
    return label
