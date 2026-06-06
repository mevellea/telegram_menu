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

"""Messages and navigation models."""

from __future__ import annotations

import asyncio
import datetime
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional, Union

import emoji
import tzlocal
import validators
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from telegram_menu import NavigationHandler

logger = logging.getLogger(__name__)

#: Public alias for the Telegram callback context passed to ``update`` methods.
Context = ContextTypes.DEFAULT_TYPE

#: A button callback: a plain function, a coroutine function, or a sub-message to open.
TypeCallback = Optional[Union[Callable[..., Any], Coroutine[Any, Any, None], "BaseMessage"]]
#: A keyboard, organised as a list of rows of buttons.
TypeKeyboard = list[list["MenuButton"]]

_EMOJI_PATTERN = re.compile(r":\w+:")


def emoji_replace(label: str) -> str:
    """Replace emoji aliases (e.g. ``:robot:``) with their unicode characters."""
    return _EMOJI_PATTERN.sub(lambda match: emoji.emojize(match.group(), language="alias"), label)


async def call_callback(method: TypeCallback, argument: Any, *args: Any, **kwargs: Any) -> Any:
    """Call a callback that may be sync or async and may or may not accept ``argument``.

    The callback signature is not known in advance, so this follows the "easier to ask
    forgiveness than permission" approach: try calling it with the extra argument and
    fall back to calling it without if a ``TypeError`` is raised.
    """
    if asyncio.iscoroutinefunction(method):
        try:
            return await method(*args, argument, **kwargs)
        except TypeError:
            return await method(*args, **kwargs)
    if not callable(method):
        raise TypeError(f"Callback {method!r} is not callable")
    try:
        return method(*args, argument, **kwargs)
    except TypeError:
        return method(*args, **kwargs)


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
    """Wrapper for a label with its callback.

    Args:
        label: button label (emoji aliases are expanded automatically)
        callback: method called on button selection
        btype: button type
        args: argument passed to the callback
        notification: send a notification to the user
        web_app_url: URL of an associated web-app
    """

    label: str
    callback: TypeCallback = None
    btype: ButtonType = ButtonType.NOTIFICATION
    args: Any = None
    notification: bool = True
    web_app_url: str = ""

    def __post_init__(self) -> None:
        """Expand emoji aliases in the label."""
        self.label = emoji_replace(self.label)


class BaseMessage(ABC):
    """Base message class, holding a keyboard of buttons and a content updater.

    Args:
        navigation: navigation manager
        label: message label
        picture: path of the picture to send, leave empty if no picture should be sent
        expiry_period: duration before the message is deleted
        inlined: create an inlined message instead of a menu message
        home_after: go back to home menu after executing the action
        notification: show a notification in the Telegram interface
        input_field: placeholder shown in the input field
    """

    EXPIRING_DELAY = 12  # minutes
    SEPARATOR = "##"

    time_alive: datetime.datetime

    def __init__(
        self,
        navigation: "NavigationHandler",
        label: str = "",
        picture: str = "",
        expiry_period: datetime.timedelta | None = None,
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
    def update(self, context: Context | None = None) -> str:
        """Update message content with HTML formatting. May also be implemented as a coroutine."""
        raise NotImplementedError

    async def get_updated_content(self, context: Context | None = None) -> str:
        """Call ``update`` (sync or async) and expand emoji aliases in the result."""
        content = await call_callback(self.update, context)
        return emoji_replace(content) if content else content

    async def text_input(self, text: str, context: Context | None = None) -> None:
        """Receive text from the user. Override in a child class to handle free text input."""

    def get_button(self, label: str) -> MenuButton | None:
        """Get the first button matching the given label."""
        return next((button for row in self.keyboard for button in row if button.label == label), None)

    def add_button_back(self, **args: Any) -> None:
        """Add a button to go back to the previous menu."""
        self.add_button(label="Back", callback=None, **args)

    def add_button_home(self, **args: Any) -> None:
        """Add a button to go back to the main menu."""
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
        """Add a button to the keyboard.

        Args:
            label: button label
            callback: method called on button selection
            btype: button type
            args: argument passed to the callback
            notification: send a notification to the user
            new_row: start a new row before adding this button
            web_app_url: URL of an associated web-app
        """
        # arrange buttons per row, depending on the inlined property
        buttons_per_row = 4 if self.inlined else 2

        if not isinstance(self.keyboard, list) or not self.keyboard:
            self.keyboard = [[]]

        button = MenuButton(label, callback, btype, args, notification, web_app_url)
        # add a new row if requested or if the last row is full, otherwise append to the last row
        if new_row or len(self.keyboard[-1]) == buttons_per_row:
            self.keyboard.append([button])
        else:
            self.keyboard[-1].append(button)

    async def edit_message(self) -> bool:
        """Request the navigation controller to update the current message."""
        return await self.navigation.edit_message(self)

    def gen_keyboard_content(self) -> ReplyKeyboardMarkup:
        """Generate the content of a reply (menu) keyboard."""
        keyboard_buttons: list[list[KeyboardButton]] = []
        for row in self.keyboard:
            if not self.input_field and row:
                self.input_field = row[0].label
            button_array: list[KeyboardButton] = []
            for button in row:
                if button.web_app_url and validators.url(button.web_app_url):
                    button_array.append(KeyboardButton(text=button.label, web_app=WebAppInfo(url=button.web_app_url)))
                else:
                    button_array.append(KeyboardButton(text=button.label))
            keyboard_buttons.append(button_array)
        if self.input_field and self.input_field != "<disable>":
            return ReplyKeyboardMarkup(
                keyboard=keyboard_buttons, resize_keyboard=True, input_field_placeholder=self.input_field
            )
        return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

    def gen_inline_keyboard_content(self) -> InlineKeyboardMarkup:
        """Generate the content of an inline keyboard."""
        keyboard_buttons: list[list[InlineKeyboardButton]] = []
        for row in self.keyboard:
            if not self.input_field and row:
                self.input_field = row[0].label
            button_array: list[InlineKeyboardButton] = []
            for button in row:
                if self.SEPARATOR in self.label or self.SEPARATOR in button.label:
                    raise ValueError(f"Forbidden character: {self.SEPARATOR}")
                if button.web_app_url and validators.url(button.web_app_url):
                    if button.btype == ButtonType.LINK:
                        button_array.append(InlineKeyboardButton(text=button.label, url=button.web_app_url))
                    else:
                        # web-app buttons do not support callback_data
                        button_array.append(
                            InlineKeyboardButton(text=button.label, web_app=WebAppInfo(url=button.web_app_url))
                        )
                else:
                    callback_data = f"{self.label}{self.SEPARATOR}{button.label}"
                    button_array.append(InlineKeyboardButton(text=button.label, callback_data=callback_data))
            keyboard_buttons.append(button_array)
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    def is_alive(self) -> None:
        """Update the message timestamp."""
        self.time_alive = datetime.datetime.now(tz=tzlocal.get_localzone())

    def has_expired(self) -> bool:
        """Return True if the message has expired."""
        if getattr(self, "time_alive", None) is not None:
            return self.time_alive + self.expiry_period < datetime.datetime.now(tz=tzlocal.get_localzone())
        return False

    def kill_message(self) -> None:
        """Display status before the message is destroyed."""
        logger.debug("Removing message '%s' (%s)", self.label, self.message_id)


# Backwards-compatible alias for the previous internal helper name.
call_function_EAFP = call_callback
