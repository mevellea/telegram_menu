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

"""Telegram menu navigation."""

import logging
import os

import telegram.ext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from telegram import Bot, ChatAction
from telegram.error import Unauthorized
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.utils.request import Request

from .models import BaseMessage, ButtonType


class SessionManager:
    """Session manager, send start message to each new user connecting to the bot.
    
    Args:
        api_key (str): Bot API key
        scheduler (BaseScheduler, optional): scheduler

    Raises:
        AttributeError: incorrect API key or scheduler

    """

    # delays in seconds
    READ_TIMEOUT = 6
    CONNECT_TIMEOUT = 7

    def __init__(self, api_key, scheduler=None):
        """Initialize SessionManager class."""
        if not isinstance(api_key, str):
            raise AttributeError("API_KEY must be a string!")

        if scheduler is not None:
            if not isinstance(scheduler, BaseScheduler):
                raise AttributeError("scheduler base class must be BaseScheduler!")
            self._scheduler = scheduler
        else:
            self._scheduler = BackgroundScheduler()

        self.updater = telegram.ext.Updater(
            api_key,
            use_context=True,
            request_kwargs={"read_timeout": self.READ_TIMEOUT, "connect_timeout": self.CONNECT_TIMEOUT},
        )
        dispatcher = self.updater.dispatcher
        bot = self.updater.bot

        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.INFO)
        try:
            self._logger.info("Connected with Telegram bot %s (%s)", bot.name, bot.first_name)
        except Unauthorized:
            raise AttributeError("No bot found matching given API_KEY")

        self._api_key = api_key
        self.sessions: [NavigationManager] = []
        self._start_message_class = None
        self._start_message_args = None

        # on different commands - answer in Telegram
        dispatcher.add_handler(CommandHandler("start", self._send_start_message))
        dispatcher.add_handler(MessageHandler(telegram.ext.Filters.text, self._button_select_callback))
        dispatcher.add_handler(CallbackQueryHandler(self._button_inline_select_callback))
        dispatcher.add_error_handler(self._msg_error_handler)

    def start(self, start_message_class, start_message_args=None):
        """Set start message and run dispatcher.

        Args:
            start_message_class (object): class derived from BaseMessage
            start_message_args (array, optional): arguments passed to the start message

        Raises:
            AttributeError: incorrect StartMessage

        """
        self._start_message_class = start_message_class
        self._start_message_args = start_message_args
        if not issubclass(start_message_class, BaseMessage):
            raise AttributeError("start_message_class must be a BaseMessage!")
        if start_message_args is not None and not isinstance(start_message_args, list):
            raise AttributeError("start_message_args is not a list!")

        if not self._scheduler.running:
            self._scheduler.start()
        self.updater.start_polling()

    def _send_start_message(self, update, context):  # pylint: disable=unused-argument
        """Start main message, app choice.
        
        Args:
            update (telegram.update.Update): telegram updater
            context (telegram.ext.callbackcontext.CallbackContext): _callback context
        
        """
        chat = update.effective_chat
        self._logger.info("Opening %s chat with user %s", chat.type, chat.first_name)
        session = NavigationManager(self._api_key, chat.id, self._scheduler)
        self.sessions.append(session)
        if self._start_message_args is not None:
            start_message = self._start_message_class(session, self._start_message_args)
        else:
            start_message = self._start_message_class(session)
        session.goto_menu(start_message)

    def get_session(self, chat_id=0):
        """Get session from list.
        
        Args:
            chat_id (int, optional): chat identifier
        
        Returns:
            NavigationManager: the session found

        """
        sessions = [x for x in self.sessions if chat_id in (x.chat_id, 0)]
        if not sessions:
            return None
        return sessions[0]

    def _button_select_callback(self, update, context):
        """Menu message main entry point.
        
        Args:
            update (telegram.update.Update): telegram updater
            context (telegram.ext.callbackcontext.CallbackContext): _callback context
        
        """
        session = self.get_session(update.effective_chat.id)
        if session is None:
            self._send_start_message(update, context)
            return
        session.select_menu_button(update.message.text)

    def _button_inline_select_callback(self, update, context):
        """Execute inline _callback of an BaseMessage.
        
        Args:
            update (telegram.update.Update): telegram updater
            context (telegram.ext.callbackcontext.CallbackContext): _callback context
        
        """
        session = self.get_session(update.effective_chat.id)
        if session is None:
            self._send_start_message(update, context)
            return
        session.app_message_button_callback(
            update.callback_query.data, update.callback_query.id, update.callback_query.message.message_id
        )

    def _msg_error_handler(self, update, context):
        """Log Errors caused by Updates."""
        error_message = str(context.error) if update is None else f"Update {update.update_id} - {str(context.error)}"
        self._logger.error(error_message)

    def broadcast_message(self, message, notification=True):
        """Broadcast simple message without keyboard markup to all sessions."""
        for session in self.sessions:
            session.send_message(message, notification=notification)

    def broadcast_picture(self, picture_path, notification=True):
        """Broadcast picture to all sessions."""
        for session in self.sessions:
            session.send_photo(picture_path, notification=notification)


class NavigationManager:
    """Navigation manager for Telegram application.
    
    Args:
        api_key (str): Bot API key
        chat_id (int): chat identifier
        scheduler (BaseScheduler): scheduler

    """

    MESSAGE_CHECK_TIMEOUT = 10
    CONNECTION_POOL_SIZE = 8

    PICTURE_DEFAULT = "resources/stats_default.png"

    def __init__(self, api_key, chat_id, scheduler):
        """Init Navigation manager class."""
        request = Request(con_pool_size=self.CONNECTION_POOL_SIZE)
        self._bot = Bot(token=api_key, request=request)

        self.chat_id = chat_id

        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.INFO)

        self._menu_queue: [BaseMessage] = []  # list of menus selected by user
        self._message_queue: [BaseMessage] = []  # list of application messages sent

        # check if messages have expired every MESSAGE_CHECK_TIMEOUT seconds
        scheduler.add_job(
            self._expiry_date_checker,
            "interval",
            id="state_nav_update",
            seconds=self.MESSAGE_CHECK_TIMEOUT,
            replace_existing=True,
        )

    def _expiry_date_checker(self):
        """Check expiry date of message and delete if expired."""
        for message in self._message_queue:
            if message.has_expired():
                self._delete_queued_message(message)

    def _delete_queued_message(self, message):
        """Delete a message, remove from queue.
    
        Args:
            message (BaseMessage): message

        """
        message.kill_message()
        if message in self._message_queue:
            self._message_queue.remove(message)
            self._bot.delete_message(chat_id=self.chat_id, message_id=message.message_id)
        del message

    def goto_menu(self, menu_message):
        """Send menu message and add to queue.
    
        Args:
            menu_message (BaseMessage): message

        Returns:
            int: message identifier

        """
        title = menu_message.content_updater()
        self._logger.info("Opening menu %s", menu_message.label)
        keyboard = menu_message.gen_keyboard_content(inlined=False)
        message = self.send_message(title, keyboard, notification=menu_message.notification)

        self._menu_queue.append(menu_message)
        return message.message_id

    def goto_home(self):
        """Go to home menu, empty menu_queue.

        Returns:
            int: message identifier

        """
        menu_previous = self._menu_queue.pop()
        while self._menu_queue:
            menu_previous = self._menu_queue.pop()
        return self.goto_menu(menu_previous)

    def _send_app_message(self, message, label):
        """Send an application message.
    
        Args:
            message (BaseMessage): message
            label (str): message label

        Returns:
            int: message identifier

        """
        title = message.content_updater()
        # if message with this label already exist in message_queue, delete it and replace it
        self._logger.info("Send message %s: %s", message.label, label)
        if "_" not in message.label:
            message.label = f"{message.label}_{label}"

        # delete message if already displayed
        message_existing = self.get_message(message.label)
        if message_existing is not None:
            self._delete_queued_message(message)

        message.is_alive()

        keyboard = message.gen_keyboard_content(inlined=True)
        msg = self.send_message(title, keyboard, message.notification)
        message.message_id = msg.message_id
        self._message_queue.append(message)

        message.content_previous = title
        message.keyboard_previous = message.keyboard.copy()
        return message.message_id

    def send_message(self, content, keyboard=None, notification=True):
        """Send a text message with html formatting.

        Args:
            content (str): message content
            keyboard (ReplyKeyboardMarkup, optional): message keyboard
            notification (bool, optional): send notification to user

        Returns:
            telegram.Message: message sent

        """
        return self._bot.send_message(
            chat_id=self.chat_id,
            text=content,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_notification=not notification,
        )

    def edit_message(self, message):
        """Edit an inline message asynchronously.
    
        Args:
            message (BaseMessage): message

        Returns:
            bool: message was edited

        """
        message = self.get_message(message.label)
        if message is None:
            return False

        # check if content and keyboard have changed since previous message
        content = message.content_updater()
        if not self._message_check_changes(message, content):
            return False

        keyboard_format = message.gen_keyboard_content()
        self._bot.edit_message_text(
            text=content,
            chat_id=self.chat_id,
            message_id=message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard_format,
        )
        return True

    @staticmethod
    def _message_check_changes(message, content):
        """Check is message content and keyboard has changed since last edit.
    
        Args:
            message (BaseMessage): message
            content (str): message content

        """
        content_identical = content == message.content_previous
        keyboard_identical = [x.label for x in message.keyboard_previous] == [x.label for x in message.keyboard]
        if content_identical and keyboard_identical:
            return False
        message.content_previous = content
        message.keyboard_previous = message.keyboard.copy()
        return True

    def select_menu_button(self, label):
        """Select menu button using label.
    
        Args:
            label (str): message label

        Returns:
            int: message identifier
            
        """
        if label == "Back":
            menu_previous = self._menu_queue.pop()  # delete actual menu
            if self._menu_queue:
                menu_previous = self._menu_queue.pop()
            return self.goto_menu(menu_previous)
        if label == "Home":
            return self.goto_home()
        for menu_item in self._menu_queue:
            button_found = menu_item.get_button(label)
            if button_found:
                message_callback = button_found.callback
                if message_callback.inlined:
                    msg_id = self._send_app_message(message_callback, label)
                    if message_callback.home_after:
                        msg_id = self.goto_home()
                else:
                    msg_id = self.goto_menu(message_callback)
                return msg_id
        return 0

    def app_message_button_callback(self, callback_label, callback_id, message_id):
        """Entry point to execute an action after message button selection.
    
        Args:
            callback_label (str): _callback label
            callback_id (str): _callback identifier
            message_id (str): message identifier

        """
        label_message, label_action = callback_label.split(".")
        self._logger.info("Received action request from %s: %s", label_message, label_action)
        message = self.get_message(label_message)
        if message is None:
            self._logger.error("Message with label %s not found, return", label_message)
            return
        button_found = message.get_button(label_action)

        if button_found.btype == ButtonType.PICTURE:
            self._bot.send_chat_action(chat_id=self.chat_id, action=ChatAction.UPLOAD_PHOTO)
        elif button_found.btype == ButtonType.MESSAGE:
            self._bot.send_chat_action(chat_id=self.chat_id, action=ChatAction.TYPING)

        if button_found.args is not None:
            action_status = button_found.callback(button_found.args)
        else:
            action_status = button_found.callback()

        # send picture if custom label found
        if button_found.btype == ButtonType.PICTURE:
            picture_path = action_status
            self.send_photo(picture_path, notification=button_found.notification)
            self._bot.answer_callback_query(callback_id, text="Picture sent!")
            return
        if button_found.btype == ButtonType.MESSAGE:
            self.send_message(action_status, notification=button_found.notification)
            self._bot.answer_callback_query(callback_id, text="Message sent!")
            return
        self._bot.answer_callback_query(callback_id, text=action_status)

        # update expiry period
        message.is_alive()

        content = message.content_updater()
        if not self._message_check_changes(message, content):
            return

        keyboard_format = message.gen_keyboard_content(True)
        self._bot.edit_message_text(
            text=content, chat_id=self.chat_id, message_id=message_id, parse_mode="HTML", reply_markup=keyboard_format
        )

    def send_photo(self, picture_path, notification=True):
        """Send a picture.

        Args:
            picture_path (str): path to picture
            notification (bool, optional): send notification to user

        Returns:
            telegram.Message: message sent

        """
        if picture_path is None or not os.path.isfile(picture_path):
            dir_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
            picture_path = os.path.join(dir_path, self.PICTURE_DEFAULT)
            self._logger.error("Picture not defined, replacing with default %s", self.PICTURE_DEFAULT)
        with open(picture_path, "rb") as file_h:
            return self._bot.send_photo(chat_id=self.chat_id, photo=file_h, disable_notification=not notification)

    def get_message(self, label_message):
        """Get message from message_queue matching attribute label_message.
    
        Args:
            label_message (str): message label

        Returns:
            BaseMessage: message found

        """
        buttons = [x for x in self._message_queue if x.label == label_message]
        if not buttons:
            return None
        return buttons[0]
