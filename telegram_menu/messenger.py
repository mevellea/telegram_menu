#!/usr/bin/env python
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

"""Telegram messenger interface."""

import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.utils.request import Request


class TelegramMenuClient:
    """Interface for Telegram Menu client.
    
    Args:
        navigation_handler (telegram_menu.navigation.NavigationManager): navigation manager
        api_key (str): Bot API key
        logging_level (int): logging level

    Raises:
        AttributeError: incorrect API key

    """

    CONNECTION_POOL_SIZE = 8

    def __init__(self, navigation_handler, api_key, logging_level=logging.INFO):
        """Start the bot."""
        # Enable logging
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging_level)
        self._logger.info("Start Telegram client")

        self._navigation = navigation_handler
        request = Request(con_pool_size=self.CONNECTION_POOL_SIZE)
        self._bot = Bot(token=api_key, request=request)

    def send_popup(self, content, callback_id):
        """Send popup message following a _callback query.
        
        Args:
            content (str): popup content
            callback_id (str): _callback identifier
        
        """
        self._bot.answer_callback_query(callback_id, text=content)

    def send_message(self, chat_id, content, keyboard):
        """Send a message, include label and keyboard.
        
        Args:
            chat_id (int): chat identifier
            content (str): message content
            keyboard (telegram.replykeyboardmarkup.ReplyKeyboardMarkup): keyboard
        
        Returns:
            int: message identifier

        """
        message = self._bot.send_message(chat_id=chat_id, text=content, parse_mode="HTML", reply_markup=keyboard)
        return message.message_id

    def send_picture(self, chat_id, picture_file):
        """Send a picture.
        
        Args:
            chat_id (int): chat identifier
            picture_file (str): picture file path
        
        Returns:
            int: message identifier

        """
        message = self._bot.send_photo(chat_id=chat_id, photo=open(picture_file, "rb"))
        return message.message_id

    def edit_message(self, chat_id, message_id, message_content, keyboard):
        """Edit the content of an inline essage.
        
        Args:
            chat_id (int): chat identifier
            message_id (int): message identifier
            content (str): message content
            keyboard (telegram.replykeyboardmarkup.ReplyKeyboardMarkup): keyboard
        
        Returns:
            int: message identifier

        """
        self._bot.edit_message_text(
            text=message_content, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=keyboard
        )

    def msg_delete(self, chat_id, message_id):
        """Delete given message.
        
        Args:
            chat_id (int): chat identifier
            message_id (int): message identifier
            
        """
        self._bot.delete_message(chat_id=chat_id, message_id=message_id)

    @staticmethod
    def gen_keyboard_content(label, buttons, inlined):
        """Generate keyboard, base or inlined.
        
        Args:
            label (str): keyboard label
            buttons (list): list of MenuButton
            inlined (bool): True of is inlined eyboard
            
        Returns:
            ReplyKeyboardMarkup: keyboard

        """
        keyboard_buttons = []
        button_object = InlineKeyboardButton if inlined else KeyboardButton
        if inlined:
            buttons_per_line = 4 if len(buttons) > 5 else 5
        else:
            buttons_per_line = 2
        for button in TelegramMenuClient._get_array_from_list(buttons, buttons_per_line):
            keyboard_buttons.append(
                [button_object(text=x.label, callback_data="%s.%s" % (label, x.label)) for x in button]
            )
        if inlined:
            return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons, resize_keyboard=True)
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
