# -*- coding: utf-8 -*-
#
# A python library for generating Telegram menus
# Copyright (C) 2020
# Armel MEVELLEC <mevellea@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.
#
# You should have received a copy of the GNU Lesser Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].

"""Messages and navigation models."""

import datetime
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto

import emoji
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


class ButtonType(Enum):
    """Button type enumeration."""

    NOTIFICATION = auto()
    MESSAGE = auto()
    PICTURE = auto()


class MenuButton:  # pylint: disable=too-few-public-methods
    """Base button class, wrapper for label with _callback.
    
    Args:
        label (str): button label
        callback (obj, optional): method called on button selection
        btype (ButtonType, optional): button type
    
    """

    def __init__(self, label, callback=None, btype=ButtonType.NOTIFICATION, args=None):
        """Init MenuButton class."""
        self.label = label
        self.callback = callback
        self.btype = btype
        self.args = args


class BaseMessage(ABC):  # pylint: disable=too-many-instance-attributes
    """Base message class, buttons array and label updater.
    
    Args:
        navigation (telegram_menu.navigation.NavigationManager): navigation manager
        label (str): message label
    
    """

    EXPIRING_DELAY = 120  # seconds

    def __init__(self, navigation, label, expiry_period=None):
        """Init BaseMessage class."""
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)

        self.keyboard = []
        self.label = label
        self.is_inline = False
        self._navigation = navigation

        # previous values are used to check if it has changed, to skip sending identical message
        self._keyboard_previous: [MenuButton] = []
        self._content_previous = None

        self.home_after = False
        self.message_id = None
        self.expiry_period = (
            expiry_period if expiry_period is not None else datetime.timedelta(seconds=self.EXPIRING_DELAY)
        )

        self._status = None
        self._time_alive = None

    def get_button(self, label):
        """Get button matching given label.
        
        Args:
            label (str): message label
    
        Returns:
            MenuButton: button matching label

        Raises:
            EnvironmentError: too many buttons matching label

        """
        buttons = [x for x in self.keyboard if x.label == label]
        if len(buttons) > 1:
            raise EnvironmentError("More than one button with same label")
        if not buttons:
            return None
        return buttons[0]

    @staticmethod
    def emojize(emoji_name):
        """Get utf-16 code for emoji, defined in https://www.webfx.com/tools/emoji-cheat-sheet/.

        Args:
            emoji_name (str): emoji label
    
        Returns:
            str: emoji encoded as string

        """
        return emoji.emojize(f":{emoji_name}:", use_aliases=True)

    def add_button(self, label, callback=None):
        """Add a button to keyboard attribute.

        Args:
            label (str): button label
            callback (obj, optional): method called on button selection
    
        """
        self.keyboard.append(MenuButton(label, callback))

    def edit_message(self):
        """Request navigation controller to update current message.
        
        Returns:
            bool: True if message was edited
        
        """
        return self._navigation.edit_message(self)

    @abstractmethod
    def content_updater(self):
        """Update message content."""
        raise NotImplementedError

    def gen_keyboard_content(self, inlined=None):
        """Generate keyboard.
            
        Args:
            inlined (bool, optional): inlined keyboard

        Returns:
            ReplyKeyboardMarkup, InlineKeyboardMarkup: generated keyboard

        """
        if inlined is None:
            inlined = self.is_inline
        keyboard_buttons = []
        button_object = InlineKeyboardButton if inlined else KeyboardButton
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
    def _get_array_from_list(buttons, cells_per_line):
        """Convert ar array of MenuButton to a grid.
        
        Args:
            buttons (list): list of MenuButton
            cells_per_line (int): number of cells per line
            
        Returns:
            list: list of list of MenuButton

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

    def is_alive(self):
        """Update message time stamp."""
        self._time_alive = datetime.datetime.now()

    def has_expired(self):
        """Return True if expiry date of message has expired.
        
        Returns:
            bool: True if timer has expired
        
        """
        return self._time_alive + self.expiry_period < datetime.datetime.now()

    def kill_message(self):
        """Display status before message is destroyed."""
        self._logger.debug("Removing message '%s' (%s)", self.label, self.message_id)

    @staticmethod
    def format_list_to_html(args_array):
        """Format array of strings in html, first element bold.

        Args:
            args_array (list): text content

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
