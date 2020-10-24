#!/usr/bin/env python3
# pylint: disable=too-many-arguments

"""Messages and navigation models."""

import datetime
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, List, Optional, Union

import emoji
import telegram
from telegram import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

if TYPE_CHECKING:
    from telegram_menu import NavigationHandler

KeyboardContent = List[Union[str, List[str]]]


class ButtonType(Enum):
    """Button type enumeration."""

    NOTIFICATION = auto()
    MESSAGE = auto()
    PICTURE = auto()
    POLL = auto()


class MenuButton:  # pylint: disable=too-few-public-methods
    """Base button class, wrapper for label with callback.

    Args:
        label: button label
        callback: method called on button selection
        btype: button type
        notification: send notification to user

    """

    def __init__(
        self,
        label: str,
        callback: Any = None,
        btype: ButtonType = ButtonType.NOTIFICATION,
        args: Any = None,
        notification: bool = True,
    ):
        """Init MenuButton class."""
        self.label = label
        self.callback: Any = callback
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
    ):
        """Init BaseMessage class."""
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)

        self.keyboard: List[MenuButton] = []
        self.label = label
        self.inlined = inlined
        self.notification = notification
        self._navigation = navigation

        # previous values are used to check if it has changed, to skip sending identical message
        self.keyboard_previous: List[MenuButton] = []
        self.content_previous: str = ""

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
            Message content formatted with markdown format.

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
        return next(iter(x for x in self.keyboard if x.label == label), None)

    @staticmethod
    def emojize(emoji_name: str) -> str:
        """Get utf-16 code for emoji, defined in https://www.webfx.com/tools/emoji-cheat-sheet/.

        Args:
            emoji_name: emoji label

        Returns:
            emoji encoded as string

        """
        return emoji.emojize(f":{emoji_name}:", use_aliases=True)

    def add_button(self, label: str, callback: Any = None) -> None:
        """Add a button to keyboard attribute.

        Args:
            label: button label
            callback: method called on button selection

        """
        self.keyboard.append(MenuButton(label, callback))

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
        if inlined:
            buttons_per_line = 4 if len(self.keyboard) > 5 else 5
        else:
            buttons_per_line = 2
        for button in self._get_array_from_list(self.keyboard, buttons_per_line):
            keyboard_buttons.append(
                [button_object(text=x.label, callback_data="%s.%s" % (self.label, x.label)) for x in button]
            )
        if inlined:
            return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons, resize_keyboard=False)
        return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def _get_array_from_list(buttons: List[MenuButton], cells_per_line: int) -> List[List[MenuButton]]:
        """Convert ar array of MenuButton to a grid.

        Args:
            buttons: list of MenuButton
            cells_per_line: number of cells per line

        Returns:
            List of list of MenuButton

        """
        array = []
        array_row = []
        for item in buttons:
            array_row.append(item)
            if len(array_row) % cells_per_line == 0:
                array.append(array_row)
                array_row = []
        if array_row:
            array.append(array_row)
        return array

    def is_alive(self) -> None:
        """Update message time stamp."""
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
        self._logger.debug("Removing message '%s' (%s)", self.label, self.message_id)

    @staticmethod
    def format_list_to_html(args_array: KeyboardContent) -> str:
        """Format array of strings in html, first element bold.

        Args:
            args_array: text content

        """
        content = ""
        for line in args_array:
            if isinstance(line, list):
                if line[0] != "":
                    content += f"<b>{line[0]}</b>"
                    if line[1] != "":
                        content += ": "
                if line[1] != "":
                    content += line[1]
            else:
                content += f"<b>{line}</b>"

            content += "\n"
        return content
