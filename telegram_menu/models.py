#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=too-many-arguments

"""Messages and navigation models."""

import datetime
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Union

import emoji
import telegram
from telegram import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

if TYPE_CHECKING:
    from telegram_menu import NavigationHandler


logger = logging.getLogger(__name__)

TypeCallback = Optional[Union[Callable[..., Any], "BaseMessage"]]
TypeKeyboard = List[List["MenuButton"]]


class ButtonType(Enum):
    """Button type enumeration."""

    NOTIFICATION = auto()
    MESSAGE = auto()
    PICTURE = auto()
    POLL = auto()


@dataclass
class MenuButton:  # pylint: disable=too-few-public-methods
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
    ):
        """Init MenuButton class."""
        self.label = emoji_replace(label)
        self.callback = callback
        self.btype = btype
        self.args = args
        self.notification = notification


class BaseMessage(ABC):  # pylint: disable=too-many-instance-attributes
    """Base message class, buttons array and label updater.

    Args:
        navigation: navigation manager
        label: message label
        expiry_period: duration before the message is deleted
        inlined: create an inlined message instead of a menu message
        home_after: go back to home menu after executing the action
        notification: show a notification in Telegram interface
    """

    EXPIRING_DELAY = 12  # minutes

    time_alive: datetime.datetime

    def __init__(
        self,
        navigation: "NavigationHandler",
        label: str,
        expiry_period: Optional[datetime.timedelta] = None,
        inlined: bool = False,
        home_after: bool = False,
        notification: bool = True,
    ) -> None:
        """Init BaseMessage class."""
        self.keyboard: TypeKeyboard = [[]]
        self.label = emoji_replace(label)
        self.inlined = inlined
        self.notification = notification
        self._navigation = navigation

        # previous values are used to check if it has changed, to skip sending identical message
        self.keyboard_previous: TypeKeyboard = [[]]
        self.content_previous: str = ""

        # if 'home_after' is True, the navigation manager goes back to
        # the main menu after this message has been sent
        self.home_after = home_after
        self.message_id = -1
        self._expiry_period = (
            expiry_period
            if isinstance(expiry_period, datetime.timedelta)
            else datetime.timedelta(minutes=self.EXPIRING_DELAY)
        )

        self._status = None

    @abstractmethod
    def update(self) -> str:
        """Update message content.

        Returns:
            Message content formatted with HTML formatting.
        """
        raise NotImplementedError

    def get_button(self, label: str) -> Optional[MenuButton]:
        """Get button matching given label.

        Args:
            label: message label
        Returns:
            button matching label
        Raises:
            EnvironmentError: too many buttons matching label
        """
        return next(iter(y for x in self.keyboard for y in x if y.label == label), None)

    def add_button_back(self) -> None:
        """Add a button to go back to previous menu."""
        self.add_button("Back", None)

    def add_button_home(self) -> None:
        """Add a button to go back to main menu."""
        self.add_button("Home", None)

    def add_button(
        self,
        label: str,
        callback: TypeCallback = None,
        btype: ButtonType = ButtonType.NOTIFICATION,
        args: Any = None,
        notification: bool = True,
        new_row: bool = False,
    ) -> None:
        """Add a button to keyboard attribute.

        Args:
            label: button label
            callback: method called on button selection
            btype: button type
            args: argument passed to the callback
            notification: send notification to user
            new_row: add a new row
        """
        # arrange buttons per row, depending on inlined property
        buttons_per_row = 2 if not self.inlined else 4

        if not isinstance(self.keyboard, list) or not self.keyboard:
            self.keyboard = [[]]

        # add new row if last row is full or append to last row
        if new_row or len(self.keyboard[-1]) == buttons_per_row:
            self.keyboard.append([MenuButton(label, callback, btype, args, notification)])
        else:
            self.keyboard[-1].append(MenuButton(label, callback, btype, args, notification))

    def edit_message(self) -> bool:
        """Request navigation controller to update current message.

        Returns:
            True if message was edited
        """
        return self._navigation.edit_message(self)

    def gen_keyboard_content(self, inlined: Optional[bool] = None) -> Union[ReplyKeyboardMarkup, InlineKeyboardMarkup]:
        """Generate keyboard.

        Args:
            inlined: inlined keyboard

        Returns:
            Generated keyboard
        """
        if inlined is None:
            inlined = self.inlined
        keyboard_buttons = []
        button_object = telegram.InlineKeyboardButton if inlined else KeyboardButton

        for row in self.keyboard:
            keyboard_buttons.append(
                [button_object(text=x.label, callback_data="%s.%s" % (self.label, x.label)) for x in row]
            )
        if inlined:
            return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons, resize_keyboard=False)
        return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

    def is_alive(self) -> None:
        """Update message timestamp."""
        self.time_alive = datetime.datetime.now()

    def has_expired(self) -> bool:
        """Return True if expiry date of message has expired.

        Returns:
            True if timer has expired
        """
        if self.time_alive is not None:
            return self.time_alive + self._expiry_period < datetime.datetime.now()
        return False

    def kill_message(self) -> None:
        """Display status before message is destroyed."""
        logger.debug("Removing message '%s' (%s)", self.label, self.message_id)


def emoji_replace(label: str) -> str:
    """Replace emoji token with utf-16 code."""
    match_emoji = re.findall(r"(:\w+:)", label)
    for item in match_emoji:
        emoji_str = emoji.emojize(item, use_aliases=True)
        label = label.replace(item, emoji_str)
    return label
