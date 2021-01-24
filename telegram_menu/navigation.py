#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Telegram menu navigation."""

import datetime
import imghdr
import logging
import mimetypes
import time
from pathlib import Path
from typing import Any, BinaryIO, List, Optional, Union

import telegram.ext
import validators
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from telegram import Bot, Chat, ChatAction, Poll, ReplyKeyboardMarkup
from telegram.error import Unauthorized
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext.callbackcontext import CallbackContext
from telegram.parsemode import ParseMode
from telegram.update import Update
from telegram.utils.request import Request

from .models import BaseMessage, ButtonType, TypeCallback, emoji_replace

logger = logging.getLogger(__name__)


class TelegramMenuSession:
    """Session manager, send start message to each new user connecting to the bot."""

    # delays in seconds
    READ_TIMEOUT = 6
    CONNECT_TIMEOUT = 7

    start_message_class: type

    def __init__(self, api_key: str, scheduler: Optional[BaseScheduler] = None) -> None:
        """Initialize TelegramMenuSession class."""
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
        bot = self.updater.bot
        try:
            logger.info("Connected with Telegram bot %s (%s)", bot.name, bot.first_name)
        except Unauthorized as error:
            raise AttributeError("No bot found matching given API_KEY") from error

        self._api_key = api_key
        self.sessions: List[NavigationHandler] = []
        self.start_message_args = None

        # on different commands - answer in Telegram
        self.updater.dispatcher.add_handler(CommandHandler("start", self._send_start_message))
        self.updater.dispatcher.add_handler(MessageHandler(telegram.ext.Filters.text, self._button_select_callback))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self._button_inline_select_callback))
        self.updater.dispatcher.add_handler(telegram.ext.PollAnswerHandler(self._poll_answer))
        self.updater.dispatcher.add_error_handler(self._msg_error_handler)

    def start(self, start_message_class: type, start_message_args: Any = None) -> None:
        """Set start message and run dispatcher."""
        self.start_message_class = start_message_class
        self.start_message_args = start_message_args
        if not issubclass(start_message_class, BaseMessage):
            raise AttributeError("start_message_class must be a BaseMessage!")
        if start_message_args is not None and not isinstance(start_message_args, list):
            raise AttributeError("start_message_args is not a list!")

        if not self._scheduler.running:
            self._scheduler.start()
        self.updater.start_polling()

    def _send_start_message(self, update: Update, _: CallbackContext) -> None:
        """Start main message, app choice."""
        chat = update.effective_chat
        session = NavigationHandler(self._api_key, chat, self._scheduler)
        self.sessions.append(session)
        if self.start_message_class is None:
            raise AttributeError("Message class not defined")
        if self.start_message_args is not None:
            start_message = self.start_message_class(session, self.start_message_args)
        else:
            start_message = self.start_message_class(session)
        session.goto_menu(start_message)

    def get_session(self, chat_id: int = 0) -> Optional["NavigationHandler"]:
        """Get session from list."""
        sessions = [x for x in self.sessions if chat_id in (x.chat_id, 0)]
        if not sessions:
            return None
        return sessions[0]

    def _button_select_callback(self, update: Update, context: CallbackContext) -> None:
        """Menu message main entry point."""
        session = self.get_session(update.effective_chat.id)
        if session is None:
            self._send_start_message(update, context)
            return
        session.select_menu_button(update.message.text)

    def _poll_answer(self, update: Update, _: CallbackContext) -> None:
        """Entry point for poll selection."""
        session = next((x for x in self.sessions if x.user_name == update.effective_user.first_name), None)
        if session:
            session.poll_answer(update.poll_answer.option_ids[0])

    def _button_inline_select_callback(self, update: Update, context: CallbackContext) -> None:
        """Execute inline callback of an BaseMessage."""
        session = self.get_session(update.effective_chat.id)
        if session is None:
            self._send_start_message(update, context)
            return
        session.app_message_button_callback(update.callback_query.data, update.callback_query.id)

    @staticmethod
    def _msg_error_handler(update: Update, context: CallbackContext) -> None:
        """Log Errors caused by Updates."""
        error_message = str(context.error) if update is None else f"Update {update.update_id} - {str(context.error)}"
        logger.error(error_message)

    def broadcast_message(self, message: str, notification: bool = True) -> List[telegram.Message]:
        """Broadcast simple message without keyboard markup to all sessions."""
        messages = []
        for session in self.sessions:
            msg = session.send_message(message, notification=notification)
            if msg is not None:
                messages.append(msg)
        return messages

    def broadcast_picture(self, picture_path: str, notification: bool = True) -> List[telegram.Message]:
        """Broadcast picture to all sessions."""
        messages = []
        for session in self.sessions:
            msg = session.send_photo(picture_path, notification=notification)
            if msg is not None:
                messages.append(msg)
        return messages


class NavigationHandler:
    """Navigation handler for Telegram application."""

    POLL_DEADLINE = 10  # seconds
    MESSAGE_CHECK_TIMEOUT = 10  # seconds
    CONNECTION_POOL_SIZE = 8

    PICTURE_DEFAULT = r"https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/stats_default.png"

    def __init__(self, api_key: str, chat: Chat, scheduler: BaseScheduler) -> None:
        """Init NavigationHandler class."""
        request = Request(con_pool_size=self.CONNECTION_POOL_SIZE)
        self._bot = Bot(token=api_key, request=request)
        self._poll: Optional[Poll] = None
        self._poll_calback: Optional[TypeCallback] = None

        self.scheduler = scheduler
        self.chat_id = chat.id
        self.user_name = chat.first_name
        self.poll_name = f"poll_{self.user_name}"

        logger.info("Opening chat with user %s", self.user_name)

        self._menu_queue: List[BaseMessage] = []  # list of menus selected by user
        self._message_queue: List[BaseMessage] = []  # list of application messages sent

        # check if messages have expired every MESSAGE_CHECK_TIMEOUT seconds
        scheduler.add_job(
            self._expiry_date_checker,
            "interval",
            id="state_nav_update",
            seconds=self.MESSAGE_CHECK_TIMEOUT,
            replace_existing=True,
        )

    def _expiry_date_checker(self) -> None:
        """Check expiry date of message and delete if expired."""
        for message in self._message_queue:
            if message.has_expired():
                self._delete_queued_message(message)

        # go back to home after sub-menu message has expired
        if len(self._menu_queue) >= 2 and self._menu_queue[-1].has_expired():
            self.goto_home()

    def _delete_queued_message(self, message: BaseMessage) -> None:
        """Delete a message, remove from queue."""
        message.kill_message()
        if message in self._message_queue:
            self._message_queue.remove(message)
            self._bot.delete_message(chat_id=self.chat_id, message_id=message.message_id)
        del message

    def goto_menu(self, menu_message: BaseMessage) -> int:
        """Send menu message and add to queue."""
        content = menu_message.update()
        logger.info("Opening menu %s", menu_message.label)
        keyboard = menu_message.gen_keyboard_content(inlined=False)
        message = self.send_message(emoji_replace(content), keyboard, notification=menu_message.notification)
        menu_message.is_alive()
        self._menu_queue.append(menu_message)
        return message.message_id

    def goto_home(self) -> int:
        """Go to home menu, empty menu_queue."""
        menu_previous = self._menu_queue.pop()
        while self._menu_queue:
            menu_previous = self._menu_queue.pop()
        return self.goto_menu(menu_previous)

    def _send_app_message(self, message: BaseMessage, label: str) -> int:
        """Send an application message."""
        content = emoji_replace(message.update())
        # if message with this label already exist in message_queue, delete it and replace it
        logger.info("Send message %s: %s", message.label, label)
        if "_" not in message.label:
            message.label = f"{message.label}_{label}"

        # delete message if already displayed
        message_existing = self.get_message(message.label)
        if message_existing is not None:
            self._delete_queued_message(message)

        message.is_alive()

        keyboard = message.gen_keyboard_content(inlined=True)
        msg = self.send_message(content, keyboard, message.notification)
        message.message_id = msg.message_id
        self._message_queue.append(message)

        message.content_previous = content
        message.keyboard_previous = message.keyboard.copy()
        return message.message_id

    def send_message(
        self, content: str, keyboard: Optional[ReplyKeyboardMarkup] = None, notification: bool = True
    ) -> telegram.Message:
        """Send a text message with html formatting."""
        return self._bot.send_message(
            chat_id=self.chat_id,
            text=content,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_notification=not notification,
        )

    def edit_message(self, message: BaseMessage) -> bool:
        """Edit an inline message asynchronously."""
        message_updt = self.get_message(message.label)
        if message_updt is None:
            return False

        # check if content and keyboard have changed since previous message
        content = emoji_replace(message_updt.update())
        if not self._message_check_changes(message_updt, content):
            return False

        keyboard_format = message_updt.gen_keyboard_content()
        try:
            self._bot.edit_message_text(
                text=content,
                chat_id=self.chat_id,
                message_id=message_updt.message_id,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard_format,
            )
        except telegram.error.BadRequest as error:
            logger.error(error)
            return False
        return True

    @staticmethod
    def _message_check_changes(message: BaseMessage, content: str) -> bool:
        """Check is message content and keyboard has changed since last edit."""
        content_identical = content == message.content_previous
        keyboard_identical = [y.label for x in message.keyboard_previous for y in x] == [
            y.label for x in message.keyboard for y in x
        ]
        if content_identical and keyboard_identical:
            return False
        message.content_previous = content
        message.keyboard_previous = message.keyboard.copy()
        return True

    def select_menu_button(self, label: str) -> int:
        """Select menu button using label."""
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
                if isinstance(message_callback, BaseMessage):
                    if message_callback.inlined:
                        msg_id = self._send_app_message(message_callback, label)
                        if message_callback.home_after:
                            msg_id = self.goto_home()
                    else:
                        msg_id = self.goto_menu(message_callback)
                    return msg_id
        return 0

    def app_message_button_callback(self, callback_label: str, callback_id: str) -> None:
        """Entry point to execute an action after message button selection."""
        label_message, label_action = callback_label.split(".")
        logger.info("Received action request from %s: %s", label_message, label_action)
        message = self.get_message(label_message)
        if message is None:
            logger.error("Message with label %s not found, return", label_message)
            return
        button_found = message.get_button(label_action)

        if button_found is None:
            return

        if button_found.btype == ButtonType.PICTURE:
            # noinspection PyTypeChecker
            self._bot.send_chat_action(chat_id=self.chat_id, action=ChatAction.UPLOAD_PHOTO)
        elif button_found.btype == ButtonType.MESSAGE:
            # noinspection PyTypeChecker
            self._bot.send_chat_action(chat_id=self.chat_id, action=ChatAction.TYPING)
        elif button_found.btype == ButtonType.POLL:
            self.send_poll(question=button_found.args[0], options=button_found.args[1])
            self._poll_calback = button_found.callback
            self._bot.answer_callback_query(callback_id, text="Select an answer...")
            return

        if not callable(button_found.callback):
            return

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

        # update expiry period and update
        message.is_alive()
        self.edit_message(message)

    @staticmethod
    def _picture_check_replace(picture_path: str) -> Union[str, BinaryIO]:
        """Check if the given picture path or uri is correct, replace by default if not."""
        try:
            if validators.url(picture_path):
                # check if the url has image format
                mimetype, _ = mimetypes.guess_type(picture_path)
                if mimetype and mimetype.startswith("image"):
                    return picture_path
                raise ValueError("Url is not a picture")
            if Path(picture_path).is_file() and imghdr.what(picture_path):
                return open(picture_path, "rb")
            raise ValueError("Path is not a picture")
        except ValueError:
            logger.error(
                "Picture path '%s' is invalid, replacing with default %s",
                picture_path,
                NavigationHandler.PICTURE_DEFAULT,
            )
            return NavigationHandler.PICTURE_DEFAULT

    def send_photo(self, picture_path: str, notification: bool = True) -> Optional[telegram.Message]:
        """Send a picture."""
        picture_obj = self._picture_check_replace(picture_path)
        try:
            return self._bot.send_photo(chat_id=self.chat_id, photo=picture_obj, disable_notification=not notification)
        except telegram.error.BadRequest as error:
            logger.error("Failed to send picture '%s': %s", picture_obj, error)
        return None

    def get_message(self, label_message: str) -> Optional[BaseMessage]:
        """Get message from message_queue matching attribute label_message."""
        return next(iter(x for x in self._message_queue if x.label == label_message), None)

    def send_poll(self, question: str, options: List[str]) -> None:
        """Send poll to user with question and options."""
        if self.scheduler.get_job(self.poll_name) is not None:
            self.poll_delete()
        options = [emoji_replace(x) for x in options]
        self._poll = self._bot.send_poll(
            chat_id=self.chat_id,
            question=emoji_replace(question),
            options=options,
            is_anonymous=False,
            open_period=self.POLL_DEADLINE,
        )
        self.scheduler.add_job(
            self.poll_delete,
            "date",
            id=self.poll_name,
            next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=self.POLL_DEADLINE + 1),
            replace_existing=True,
        )

    def poll_delete(self) -> None:
        """Run when poll timeout has expired."""
        if self._poll is not None:
            try:
                logger.info("Deleting poll '%s'", self._poll.poll.question)
                self._bot.delete_message(chat_id=self.chat_id, message_id=self._poll.message_id)
            except telegram.error.BadRequest:
                logger.error("Poll message %s already deleted", self._poll.message_id)

    def poll_answer(self, answer_id: int) -> None:
        """Run when poll message is received."""
        if self._poll is None or self._poll_calback is None or not callable(self._poll_calback):
            logger.error("Poll is not defined")
            return

        logger.info(
            "%s's answer to question '%s' is '%s'",
            self.user_name,
            self._poll.poll.question,
            self._poll.poll.options[answer_id].text,
        )
        self._poll_calback(self._poll.poll.options[answer_id].text)
        time.sleep(1)
        self.poll_delete()

        if self.scheduler.get_job(self.poll_name) is not None:
            self.scheduler.remove_job(self.poll_name)
        self._poll = None
