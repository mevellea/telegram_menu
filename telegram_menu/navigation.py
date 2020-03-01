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

"""Telegram menu navigation."""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from telegram.error import Unauthorized
from telegram.ext import CallbackQueryHandler, CommandHandler, Filters, MessageHandler, Updater

from .messenger import TelegramMenuClient
from .models import AppMessage, BaseMessage, ButtonType, MenuMessage


class SessionManager:
    """Session manager, send start message to each new user connecting to the bot.
    
    Args:
        api_key (str): Bot API key
        start_message_class (MenuMessage): class of the start menu message
        start_message_args (array, optional): arguments passed to the start message
            
    """

    # delays in seconds
    SESSION_READ_TIMEOUT = 6
    SESSION_CONNECT_TIMEOUT = 7

    def __init__(self, api_key, start_message_class, start_message_args=None):
        """Init navigation dispatcher."""
        if not isinstance(api_key, str):
            raise AttributeError("API_KEY must be a string!")
        if not issubclass(start_message_class, MenuMessage):
            raise AttributeError("start_message_class must be a MenuMessage!")
        if start_message_args is not None and not isinstance(start_message_args, list):
            raise AttributeError("start_message_args is not a list!")

        self.updater = Updater(
            api_key,
            use_context=True,
            request_kwargs={"read_timeout": self.SESSION_READ_TIMEOUT, "connect_timeout": self.SESSION_CONNECT_TIMEOUT},
        )
        dispatcher = self.updater.dispatcher
        bot = self.updater.bot

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        try:
            self.logger.info("Connected with Telegram bot %s (%s)", bot.name, bot.first_name)
        except Unauthorized:
            raise AttributeError("No bot found matching given API_KEY")

        self.api_key = api_key
        self.scheduler = BackgroundScheduler()
        self.sessions = []
        self.start_message_class = start_message_class
        self.start_message_args = start_message_args

        # on different commands - answer in Telegram
        dispatcher.add_handler(CommandHandler("start", self.send_start_message))
        dispatcher.add_handler(MessageHandler(Filters.text, self.button_select_callback))
        dispatcher.add_handler(CallbackQueryHandler(self.button_inline_select_callback))
        dispatcher.add_error_handler(self.msg_error_handler)

        self.scheduler.start()
        self.updater.start_polling()

    def send_start_message(self, update, _):
        """Start main message, app choice."""
        chat = update.effective_chat
        self.logger.info("Opening %s chat with user %s", chat.type, chat.first_name)
        existing_session = self.get_session(chat.id)
        if existing_session is not None:
            return

        session = NavigationManager(self.api_key, chat.id, self.scheduler)
        self.sessions.append(session)
        if self.start_message_args is not None:
            start_message = self.start_message_class(session, self.start_message_args)
        else:
            start_message = self.start_message_class(session)
        session.goto_menu(start_message)

    def get_session(self, chat_id):
        """Get session from list."""
        sessions = [x for x in self.sessions if x.chat_id == chat_id]
        if not sessions:
            return None
        return sessions[0]

    def button_select_callback(self, update, _):
        """Menu message main entry point."""
        session = self.get_session(update.effective_chat.id)
        if session is None:
            self.send_start_message(update, _)
            return
        session.menu_button_callback(update.message.text)

    def button_inline_select_callback(self, update, _):
        """Execute callback of a message."""
        session = self.get_session(update.effective_chat.id)
        if session is None:
            self.send_start_message(update, _)
            return
        session.app_message_button_callback(
            update.callback_query.data, update.callback_query.id, update.callback_query.message.message_id
        )

    def msg_error_handler(self, update, context):
        """Log Errors caused by Updates."""
        self.logger.warning('Update "%s" caused error "%s"', update, context.error)


class NavigationManager:
    """Navigation manager for Telegram application."""

    MESSAGE_CHECK_TIMEOUT = 10

    PICTURE_DEFAULT = "resources/stats_default.png"

    def __init__(self, api_key, chat_id, scheduler):
        """Init Navigation manager class."""
        self.messenger = TelegramMenuClient(self, api_key)

        self.chat_id = chat_id

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.menu_queue: [MenuMessage] = []  # list of menus selected by user
        self.message_queue: [MenuMessage] = []  # list of application messages sent

        # check if messages have expired every MESSAGE_CHECK_TIMEOUT seconds
        scheduler.add_job(
            self.expiry_date_checker,
            "interval",
            id="state_nav_update",
            seconds=self.MESSAGE_CHECK_TIMEOUT,
            replace_existing=True,
        )

    def expiry_date_checker(self):
        """Check expiry date of message and delete if expired."""
        for message in self.message_queue:
            if message.has_expired():
                self.delete_message(message)

    def delete_message(self, message):
        """Delete a message, remove from queue."""
        message.kill_message()
        if message in self.message_queue:
            self.message_queue.remove(message)
            self.messenger.msg_delete(self.chat_id, message.message_id)
        del message

    def goto_menu(self, menu: MenuMessage):
        """Send menu message and add to queue."""
        title = menu.content_updater()
        self.logger.info("Opening menu %s", menu.label)
        keyboard = self.messenger.gen_keyboard_content(menu.label, menu.keyboard, is_inline=False)
        self.messenger.send_message(self.chat_id, title, keyboard)
        self.menu_queue.append(menu)

    def goto_home(self):
        """Go to home menu, empty menu_queue."""
        menu_previous = self.menu_queue.pop()
        while self.menu_queue:
            menu_previous = self.menu_queue.pop()
        self.goto_menu(menu_previous)

    def send_message(self, message: AppMessage, label: str):
        """Send an application message."""
        title = message.content_updater()
        # if message with this label already exist in message_queue, delete it and replace it
        self.logger.info("Send message %s: %s", message.label, label)
        if "_" not in message.label:
            message.label = f"{message.label}_{label}"

        # delete message if already displayed
        message_existing = self.get_message(message.label)
        if message_existing is not None:
            self.delete_message(message)

        message.is_alive()

        keyboard = self.messenger.gen_keyboard_content(message.label, message.keyboard, is_inline=True)
        message.message_id = self.messenger.send_message(self.chat_id, title, keyboard)
        self.message_queue.append(message)

        message.content_previous = title
        message.keyboard_previous = message.keyboard.copy()

    def edit_message(self, message: BaseMessage):
        """Edit an inline message asynchronously."""
        message = self.get_message(message.label)
        if message is None:
            return False

        # check if content and keyboard have changed since previous message
        content = message.content_updater()
        if not self.message_check_changes(message, content):
            return False

        keyboard_format = TelegramMenuClient.gen_keyboard_content(message.label, message.keyboard, message.is_inline)
        self.messenger.edit_message(self.chat_id, message.message_id, content, keyboard_format)
        return True

    @staticmethod
    def message_check_changes(message, content):
        """Check is message content and keyboard has changed since last edit."""
        content_identical = content == message.content_previous
        keyboard_identical = [x.label for x in message.keyboard_previous] == [x.label for x in message.keyboard]
        if content_identical and keyboard_identical:
            return False
        message.content_previous = content
        message.keyboard_previous = message.keyboard.copy()
        return True

    def menu_button_callback(self, label: str):
        """Entry point to execute a callback after button selection."""
        if label == "Back":
            menu_previous = self.menu_queue.pop()  # delete actual menu
            if self.menu_queue:
                menu_previous = self.menu_queue.pop()
            self.goto_menu(menu_previous)
            return
        if label == "Home":
            self.goto_home()
            return
        for menu_item in self.menu_queue:
            button_found = menu_item.get_button(label)
            if button_found:
                message_callback = button_found.callback
                if message_callback.is_inline:
                    self.send_message(message_callback, label)
                    if message_callback.home_after:
                        self.goto_home()
                else:
                    self.goto_menu(message_callback)
                return

    def app_message_button_callback(self, callback_label: str, callback_id: str, message_id: str):
        """Entry point to execute an action after message button selection."""
        label_message, label_action = callback_label.split(".")
        self.logger.info("Received action request from %s: %s", label_message, label_action)
        message = self.get_message(label_message)
        button_found = message.get_button(label_action)
        action_status = button_found.callback()

        # send picture if custom label found
        if button_found.btype == ButtonType.PICTURE:
            picture_path = action_status
            if picture_path is None or not os.path.isfile(picture_path):
                picture_path = self.PICTURE_DEFAULT
                self.logger.error("Picture not defined, replacing with default %s", picture_path)
            self.messenger.send_picture(self.chat_id, picture_path)
            self.messenger.send_popup("Picture sent!", callback_id)
            return
        if button_found.btype == ButtonType.MESSAGE:
            self.messenger.send_message(self.chat_id, action_status, None)
            self.messenger.send_popup("Message sent!", callback_id)
            return
        self.messenger.send_popup(action_status, callback_id)

        # update expiry period
        message.is_alive()

        content = message.content_updater()
        if not self.message_check_changes(message, content):
            return

        keyboard_format = TelegramMenuClient.gen_keyboard_content(message.label, message.keyboard, True)
        self.messenger.edit_message(self.chat_id, message_id, content, keyboard_format)

    def get_message(self, label_message: str):
        """Get message from message_queue matching attribute label_message."""
        buttons = [x for x in self.message_queue if x.label == label_message]
        if not buttons:
            return None
        return buttons[0]

    def get_menu(self, label_menu: str):
        """Get message from message_queue matching attribute label_message."""
        buttons = [x for x in self.menu_queue if x.label == label_menu]
        if not buttons:
            return None
        return buttons[0]
