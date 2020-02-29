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

from .models import MenuButton


class TelegramMenuClient:
    """Interface for Telegram Menu client."""

    CONNECTION_POOL_SIZE = 8

    def __init__(self, navigation_handler, api_key, logging_level=logging.INFO):
        """Start the bot."""
        # Enable logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging_level)
        self.logger.info("Start Telegram client")

        self.navigation = navigation_handler
        request = Request(con_pool_size=self.CONNECTION_POOL_SIZE)
        self.bot = Bot(token=api_key, request=request)

    def msg_error_handler(self, update, context):
        """Log Errors caused by Updates."""
        self.logger.warning('Update "%s" caused error "%s"', update, context.error)

    def button_inline_select_callback(self, update, _):
        """Execute callback of a message."""
        self.navigation.app_message_button_callback(
            update.callback_query.data, update.callback_query.id, update.callback_query.message.message_id
        )

    def button_select_callback(self, update, _):
        """Menu message main entry point."""
        self.navigation.menu_button_callback(update.message.text)

    def send_popup(self, content: str, callback_id: str):
        """Send popup message following a callback query."""
        self.bot.answer_callback_query(callback_id, text=content)

    def send_message(self, chat_id, content, keyboard) -> int:
        """Send a message, include label and keyboard."""
        message = self.bot.send_message(chat_id=chat_id, text=content, parse_mode="HTML", reply_markup=keyboard)
        return message.message_id

    def send_picture(self, chat_id, picture_file) -> int:
        """Send a picture."""
        message = self.bot.send_photo(chat_id=chat_id, photo=open(picture_file, "rb"))
        return message.message_id

    def edit_message(self, chat_id, message_id, message_content, keyboard):
        """Edit the content of an inline essage."""
        self.bot.edit_message_text(
            text=message_content, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=keyboard
        )

    def msg_delete(self, chat_id, message_id):
        """Delete given message."""
        self.bot.delete_message(chat_id=chat_id, message_id=message_id)

    @staticmethod
    def gen_keyboard_content(label: str, buttons: [MenuButton], is_inline):
        """Generate keyboard, base or inlined."""
        keyboard_buttons = []
        button_object = InlineKeyboardButton if is_inline else KeyboardButton
        if is_inline:
            buttons_per_line = 4 if len(buttons) > 5 else 5
        else:
            buttons_per_line = 2
        for button in TelegramMenuClient.get_array_from_list(buttons, buttons_per_line):
            keyboard_buttons.append(
                [button_object(text=x.label, callback_data="%s.%s" % (label, x.label)) for x in button]
            )
        if is_inline:
            return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons, resize_keyboard=True)
        return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

    @staticmethod
    def get_array_from_list(buttons: [MenuButton], cells_per_line: int) -> [[MenuButton]]:
        """Convert ar array of MenuButton to a grid."""
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
