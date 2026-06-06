#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 Armel Mevellec
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

"""Telegram menu navigation."""

from __future__ import annotations

import asyncio
import datetime
import logging
import mimetypes
from pathlib import Path
from typing import Any, Sequence, Type

import telegram
import telegram.error
import telegram.ext
import tzlocal
import validators
from apscheduler.schedulers.base import BaseScheduler
from telegram import Bot, Chat, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    PollAnswerHandler,
    filters,
)

from . import _imaging
from ._version import __raw_url__
from .models import BaseMessage, ButtonType, Context, TypeCallback, call_callback, emoji_replace

logger = logging.getLogger(__name__)

# Sentinel used to detect whether the caller overrode ``stop_signals`` in ``start``.
_UNSET = object()


class NavigationException(Exception):
    """Base exception."""


class TelegramMenuSession:
    """Session manager, send start message to each new user connecting to the bot."""

    START_MESSAGE = "start"

    def __init__(self, api_key: str, start_message: str = START_MESSAGE, persistence_path: str = "") -> None:
        """Initialize the session object.

        Args:
            api_key: Telegram bot API key
            start_message: text used to start a session, e.g. /start
            persistence_path: file path used to persist arbitrary callback data
        """
        if not isinstance(api_key, str):
            raise KeyError("API_KEY must be a string!")

        persistence = PicklePersistence(filepath=persistence_path or "arbitrarycallbackdatabot")
        self.application: Application = (  # type: ignore[type-arg]
            Application.builder().token(api_key).persistence(persistence).arbitrary_callback_data(True).build()
        )
        if self.application.job_queue is None:
            raise NavigationException("JobQueue is not available, install python-telegram-bot[job-queue]")
        self.scheduler: BaseScheduler = self.application.job_queue.scheduler

        self._api_key = api_key
        self.sessions: list[NavigationHandler] = []
        self.start_message_class: Type[BaseMessage] | None = None
        self.start_message_args: list[Any] | None = None
        self.navigation_handler_class: Type[NavigationHandler] | None = None

        # on different commands - answer in Telegram
        self.application.add_handler(CommandHandler(start_message, self._send_start_message))
        self.application.add_handler(MessageHandler(filters.TEXT, self._button_select_callback))
        self.application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self._button_webapp_callback))
        self.application.add_handler(CallbackQueryHandler(self._button_inline_select_callback))
        self.application.add_handler(PollAnswerHandler(self._poll_answer))
        self.application.add_error_handler(self._msg_error_handler)
        self.application.add_handler(MessageHandler(filters.LOCATION, self._get_location_handler))

    def start(
        self,
        start_message_class: Type[BaseMessage],
        start_message_args: list[Any] | None = None,
        polling: bool = True,
        navigation_handler_class: Type[NavigationHandler] | None = None,
        stop_signals: Sequence[int] | None | object = _UNSET,
    ) -> None:
        """Set the start message and run the dispatcher.

        Args:
            start_message_class: class used to create start message
            start_message_args: optional arguments passed to the start class
            polling: if True, start polling updates from Telegram
            navigation_handler_class: optional class used to extend the base NavigationHandler
            stop_signals: signals that stop polling, forwarded to ``run_polling`` if provided
        """
        self.start_message_class = start_message_class
        self.start_message_args = start_message_args
        self.navigation_handler_class = navigation_handler_class or NavigationHandler
        if not (isinstance(start_message_class, type) and issubclass(start_message_class, BaseMessage)):
            raise NavigationException("start_message_class must be a BaseMessage!")
        if start_message_args is not None and not isinstance(start_message_args, list):
            raise NavigationException("start_message_args is not a list!")
        if not issubclass(self.navigation_handler_class, NavigationHandler):
            raise NavigationException("navigation_handler_class must be a NavigationHandler!")

        if polling:
            # Application.run_polling() starts the job-queue scheduler inside the event
            # loop it creates. Starting it here (no running loop yet) breaks with modern
            # APScheduler, whose AsyncIOScheduler.start() requires a running event loop.
            extra = {} if stop_signals is _UNSET else {"stop_signals": stop_signals}
            self.application.run_polling(**extra)  # type: ignore[arg-type]
        elif not self.scheduler.running:
            # No polling: only safe to start the scheduler if the caller is already
            # running an event loop, otherwise leave it to the caller's Application.
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                logger.warning(
                    "Scheduler not started: no running event loop. Run the Application "
                    "within an event loop (e.g. polling=True) to enable scheduled jobs."
                )
            else:
                self.scheduler.start()

    async def _send_start_message(self, update: Update, context: Context) -> None:
        """Start main message, app choice."""
        chat = update.effective_chat
        if chat is None:
            raise NavigationException("Chat object was not created")
        if self.navigation_handler_class is None:
            raise NavigationException("Navigation Handler class not defined")
        session = self.navigation_handler_class(self.application.bot, chat, self.scheduler)
        self.sessions.append(session)
        if self.start_message_class is None:
            raise NavigationException("Message class not defined")
        if self.start_message_args is not None:
            start_message = self.start_message_class(session, message_args=self.start_message_args)
        else:
            start_message = self.start_message_class(session)
        await session.goto_menu(start_message, context)

    def get_session(self, chat_id: int = 0) -> NavigationHandler | None:
        """Get a session from the list, matching the chat id (or the first one if chat_id is 0)."""
        return next((session for session in self.sessions if chat_id in (session.chat_id, 0)), None)

    async def _get_location_handler(self, update: Update, context: Context) -> None:
        """Store the location received from the user in the matching session."""
        if update.effective_chat is None or update.message is None or update.message.location is None:
            raise NavigationException("Incorrect session, location can't be updated")
        session = self.get_session(update.effective_chat.id)
        if session is not None:
            session.location = update.message.location

    async def _button_select_callback(self, update: Update, context: Context) -> None:
        """Menu message main entry point."""
        if update.effective_chat is None or update.message is None:
            raise NavigationException("Chat object was not created")
        session = self.get_session(update.effective_chat.id)
        if session is None:
            await self._send_start_message(update, context)
            return
        if update.message.text:
            await session.select_menu_button(update.message.text, context)

    async def _poll_answer(self, update: Update, _: Context) -> None:
        """Entry point for poll selection."""
        if update.effective_user is None or update.poll_answer is None:
            raise NavigationException("User object was not created")
        session = next((x for x in self.sessions if x.user_name == update.effective_user.first_name), None)
        if session:
            await session.poll_answer(update.poll_answer.option_ids[0])

    async def _button_inline_select_callback(self, update: Update, context: Context) -> None:
        """Execute the inline callback of a BaseMessage."""
        if update.effective_chat is None or update.callback_query is None:
            raise NavigationException("Chat object was not created")
        session = self.get_session(update.effective_chat.id)
        if session is None:
            await self._send_start_message(update, context)
            return
        if update.callback_query.data and update.callback_query.id:
            await session.app_message_button_callback(update.callback_query.data, update.callback_query.id, context)

    async def _button_webapp_callback(self, update: Update, context: Context) -> None:
        """Execute a webapp callback."""
        if (
            update.effective_chat is None
            or update.effective_message is None
            or update.effective_message.web_app_data is None
        ):
            raise NavigationException("Chat object was not created")
        session = self.get_session(update.effective_chat.id)
        if session is None:
            await self._send_start_message(update, context)
            return
        await session.app_message_webapp_callback(
            update.effective_message.web_app_data.data, update.effective_message.web_app_data.button_text
        )

    @staticmethod
    async def _msg_error_handler(update: object, context: Context) -> None:
        """Log errors caused by updates."""
        if not isinstance(update, Update):
            raise NavigationException("Incorrect update object")
        error_message = f"Update {update.update_id} - {context.error}"
        logger.error(error_message)

    async def broadcast_message(self, message: str, notification: bool = True) -> list[Message]:
        """Broadcast a simple message without keyboard markup to all sessions."""
        messages = []
        for session in self.sessions:
            msg = await session.send_message(message, notification=notification)
            if msg is not None:
                messages.append(msg)
        return messages

    async def broadcast_picture(self, picture_path: str, notification: bool = True) -> list[Message]:
        """Broadcast a picture to all sessions."""
        messages = []
        for session in self.sessions:
            msg = await session.send_photo(picture_path, notification=notification)
            if msg is not None:
                messages.append(msg)
        return messages

    async def broadcast_sticker(self, sticker_path: str, notification: bool = True) -> list[Message]:
        """Broadcast a sticker to all sessions."""
        messages = []
        for session in self.sessions:
            msg = await session.send_sticker(sticker_path, notification=notification)
            if msg is not None:
                messages.append(msg)
        return messages


class NavigationHandler:
    """Navigation handler for a Telegram application."""

    POLL_DEADLINE = 10  # seconds
    MESSAGE_CHECK_TIMEOUT = 10  # seconds
    CONNECTION_POOL_SIZE = 8

    def __init__(self, bot: Bot, chat: Chat, scheduler: BaseScheduler) -> None:
        """Init NavigationHandler class."""
        self._bot = bot
        self._poll: Message | None = None
        self._poll_callback: TypeCallback | None = None

        self.scheduler = scheduler
        self.chat_id = chat.id
        self.user_name = chat.first_name
        self.poll_name = f"poll_{self.user_name}"
        self.location: telegram.Location | None = None

        logger.info("Opening chat with user %s", self.user_name)

        self._menu_queue: list[BaseMessage] = []  # list of menus selected by user
        self._message_queue: list[BaseMessage] = []  # list of application messages sent

        # check if messages have expired every MESSAGE_CHECK_TIMEOUT seconds
        scheduler.add_job(
            self._expiry_date_checker,
            "interval",
            id="state_nav_update",
            seconds=self.MESSAGE_CHECK_TIMEOUT,
            replace_existing=True,
        )

    async def _expiry_date_checker(self) -> None:
        """Check the expiry date of messages and delete those that have expired."""
        for message in self._message_queue[:]:
            if message.has_expired():
                await self._delete_queued_message(message)

        # go back to home after sub-menu message has expired
        if len(self._menu_queue) >= 2 and self._menu_queue[-1].has_expired():
            await self.goto_home()

    async def delete_message(self, message_id: int) -> None:
        """Delete a message from its id."""
        await self._bot.delete_message(chat_id=self.chat_id, message_id=message_id)

    async def _delete_queued_message(self, message: BaseMessage) -> None:
        """Delete a message and remove it from the queue."""
        message.kill_message()
        if message in self._message_queue:
            self._message_queue.remove(message)
            await self.delete_message(message.message_id)

    async def goto_menu(self, menu_message: BaseMessage, context: Context | None = None) -> int:
        """Send a menu message and add it to the queue."""
        content = await menu_message.get_updated_content(context)
        logger.info("Opening menu %s", menu_message.label)
        keyboard = menu_message.gen_keyboard_content()
        if menu_message.picture:
            message = await self.send_photo(
                menu_message.picture, notification=menu_message.notification, keyboard=keyboard, caption=content
            )
        else:
            message = await self.send_message(content, keyboard, notification=menu_message.notification)
        if message is None:
            return -1  # message was not sent, abort
        menu_message.is_alive()
        menu_message.message_id = message.message_id
        self._menu_queue.append(menu_message)
        return message.message_id

    async def goto_home(self, context: Context | None = None) -> int:
        """Go to the home menu, emptying the menu queue."""
        if not self._menu_queue:
            return -1
        if len(self._menu_queue) == 1:
            # already at 'home' level
            return self._menu_queue[0].message_id
        menu_previous = self._menu_queue.pop()
        while self._menu_queue:
            menu_previous = self._menu_queue.pop()
        return await self.goto_menu(menu_previous, context)

    @staticmethod
    def filter_unicode(input_string: str) -> str:
        """Remove non-ascii characters from the input string."""
        return input_string.encode("ascii", "ignore").decode("utf-8")

    async def _send_app_message(self, message: BaseMessage, label: str, context: Context | None = None) -> int:
        """Send an application (inline) message."""
        content = await message.get_updated_content(context)
        # if a message with this label already exists in the queue, delete it and replace it
        logger.info(self.filter_unicode(f"Send message '{message.label}': '{label}'"))
        if "_" not in message.label:
            message.label = f"{message.label}_{label}"

        # delete message if already displayed
        if self.get_message(message.label) is not None:
            await self._delete_queued_message(message)

        message.is_alive()

        keyboard = message.gen_inline_keyboard_content()
        if message.picture:
            msg = await self.send_photo(
                message.picture, notification=message.notification, caption=content, keyboard=keyboard
            )
        else:
            msg = await self.send_message(content, keyboard, message.notification)
        if msg is None:
            return -1  # message was not sent, abort
        message.message_id = msg.message_id
        self._message_queue.append(message)

        message.content_previous = content
        message.keyboard_previous = message.keyboard.copy()
        return message.message_id

    async def send_message(
        self,
        content: str,
        keyboard: ReplyKeyboardMarkup | InlineKeyboardMarkup | None = None,
        notification: bool = True,
    ) -> Message:
        """Send a text message with HTML formatting."""
        return await self._bot.send_message(
            chat_id=self.chat_id,
            text=content,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_notification=not notification,
        )

    async def edit_message(self, message: BaseMessage, context: Context | None = None) -> bool:
        """Edit an inline message asynchronously."""
        message_updt = self.get_message(message.label)
        if message_updt is None:
            return False

        # check if content and keyboard have changed since previous message
        content = await message_updt.get_updated_content(context)
        if not self._message_check_changes(message_updt, content):
            return False

        keyboard_format = message_updt.gen_inline_keyboard_content()
        try:
            if message_updt.picture:
                await self._bot.edit_message_caption(
                    caption=content,
                    chat_id=self.chat_id,
                    message_id=message_updt.message_id,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard_format,
                )
            else:
                await self._bot.edit_message_text(
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
        """Return True if the message content or keyboard has changed since the last edit."""
        content_identical = content == message.content_previous
        keyboard_identical = [button.label for row in message.keyboard_previous for button in row] == [
            button.label for row in message.keyboard for button in row
        ]
        if content_identical and keyboard_identical:
            return False
        message.content_previous = content
        message.keyboard_previous = message.keyboard.copy()
        return True

    async def select_menu_button(self, label: str, context: Context | None = None) -> int | None:
        """Select a menu button using its label."""
        if label == "Back":
            if len(self._menu_queue) == 1:
                # already at 'home' level
                return self._menu_queue[0].message_id
            self._menu_queue.pop()  # delete current menu
            menu_previous = self._menu_queue.pop() if self._menu_queue else None
            if menu_previous is None:
                return None
            return await self.goto_menu(menu_previous, context)
        if label == "Home":
            return await self.goto_home(context)

        for menu_item in reversed(self._menu_queue):
            button = menu_item.get_button(label)
            if button is None:
                continue
            return await self._run_button_callback(button, label, context)

        # label does not match any sub-menu, just process the user input
        await self.capture_user_input(label, context)
        return None

    async def _run_button_callback(self, button: Any, label: str, context: Context | None) -> int:
        """Execute the action attached to a selected menu button."""
        if isinstance(button.callback, BaseMessage):
            if button.callback.inlined:
                msg_id = await self._send_app_message(button.callback, label, context)
                if button.callback.home_after:
                    msg_id = await self.goto_home(context)
                return msg_id
            return await self.goto_menu(button.callback, context)
        if callable(button.callback):
            if button.args is not None:
                await call_callback(button.callback, context, button.args)
            else:
                await call_callback(button.callback, context)
        return 0

    async def capture_user_input(self, label: str, context: Context | None = None) -> None:
        """Process the user input in the most recently updated message."""
        last_menu_message = self._menu_queue[-1]
        for last_app_message in reversed(self._message_queue):
            if last_app_message.time_alive > last_menu_message.time_alive:
                last_menu_message = last_app_message
                break
        await last_menu_message.text_input(label, context)

    async def app_message_webapp_callback(self, webapp_data: str, button_text: str) -> None:
        """Execute the callback associated with a webapp."""
        last_menu = self._menu_queue[-1]
        webapp_message = next(
            (button for row in last_menu.keyboard for button in row if button.label == button_text), None
        )
        if webapp_message is not None and callable(webapp_message.callback):
            if asyncio.iscoroutinefunction(webapp_message.callback):
                html_response = await webapp_message.callback(webapp_data)
            else:
                html_response = webapp_message.callback(webapp_data)
            await self.send_message(html_response, notification=webapp_message.notification)

    async def app_message_button_callback(
        self, callback_label: str, callback_id: str, context: Context | None = None
    ) -> None:
        """Entry point to execute an action after an inline message button is selected."""
        label_message, label_action = callback_label.split(BaseMessage.SEPARATOR)
        logger.info(self.filter_unicode(f"Received action request from '{label_message}': '{label_action}'"))
        message = self.get_message(label_message)
        if message is None:
            logger.error("Message with label %s not found, return", label_message)
            return
        button = message.get_button(label_action)
        if button is None:
            logger.error("No button found with label %s, return", label_action)
            return

        if button.btype in (ButtonType.PICTURE, ButtonType.STICKER):
            await self._bot.send_chat_action(chat_id=self.chat_id, action=ChatAction.UPLOAD_PHOTO)
        elif button.btype == ButtonType.MESSAGE:
            await self._bot.send_chat_action(chat_id=self.chat_id, action=ChatAction.TYPING)
        elif button.btype == ButtonType.POLL:
            await self.send_poll(question=button.args[0], options=button.args[1])
            self._poll_callback = button.callback
            await self._bot.answer_callback_query(callback_id, text="Select an answer...")
            return

        if not callable(button.callback):
            return

        if button.args is not None:
            action_status = await call_callback(button.callback, context, button.args)
        else:
            action_status = await call_callback(button.callback, context)

        # send picture/sticker/message if a custom button type is set
        if button.btype == ButtonType.PICTURE:
            await self.send_photo(picture_path=action_status, notification=button.notification)
            await self._bot.answer_callback_query(callback_id, text="Picture sent!")
            return
        if button.btype == ButtonType.STICKER:
            await self.send_sticker(sticker_path=action_status, notification=button.notification)
            await self._bot.answer_callback_query(callback_id, text="Sticker sent!")
            return
        if button.btype == ButtonType.MESSAGE:
            await self.send_message(action_status, notification=button.notification)
            await self._bot.answer_callback_query(callback_id, text="Message sent!")
            return
        await self._bot.answer_callback_query(callback_id, text=action_status)

        # update expiry period and refresh the message
        message.is_alive()
        await self.edit_message(message, context)

    @staticmethod
    def _sticker_check_replace(sticker_path: str) -> str | bytes:
        """Check that the sticker is a valid .webp file, replacing it with a default otherwise."""
        try:
            if not sticker_path.lower().endswith(".webp"):
                raise ValueError("Sticker has no .webp format")
            if validators.url(sticker_path):
                # todo: add check if url exists
                return sticker_path
            if Path(sticker_path).is_file() and _imaging.what(sticker_path):
                return Path(sticker_path).read_bytes()
            raise ValueError("Path is not a picture")
        except (ValueError, OSError):
            url_default = f"{__raw_url__}/resources/stats_default.webp"
            logger.error("Sticker path '%s' is invalid, replacing with default %s", sticker_path, url_default)
            return url_default

    @staticmethod
    def _picture_check_replace(picture_path: str) -> str | bytes:
        """Check that the picture path or uri is valid, replacing it with a default otherwise."""
        try:
            if validators.url(picture_path):
                # check if the url has an image format
                mimetype, _ = mimetypes.guess_type(picture_path)
                if mimetype and mimetype.startswith("image"):
                    return picture_path
                raise ValueError("Url is not a picture")
            if Path(picture_path).is_file() and _imaging.what(picture_path):
                return Path(picture_path).read_bytes()
            raise ValueError("Path is not a picture")
        except (ValueError, OSError):
            url_default = f"{__raw_url__}/resources/stats_default.png"
            logger.error("Picture path '%s' is invalid, replacing with default %s", picture_path, url_default)
            return url_default

    async def send_photo(
        self,
        picture_path: str,
        notification: bool = True,
        caption: str = "",
        keyboard: ReplyKeyboardMarkup | InlineKeyboardMarkup | None = None,
    ) -> Message | None:
        """Send a picture."""
        picture_obj = self._picture_check_replace(picture_path=picture_path)
        try:
            return await self._bot.send_photo(
                chat_id=self.chat_id,
                photo=picture_obj,
                caption=caption,
                reply_markup=keyboard,
                disable_notification=not notification,
                parse_mode=ParseMode.HTML,
            )
        except telegram.error.BadRequest as error:
            logger.error("Failed to send picture %s: %s", picture_path, error)
        return None

    async def send_sticker(self, sticker_path: str, notification: bool = True) -> Message | None:
        """Send a sticker."""
        sticker_obj = self._sticker_check_replace(sticker_path=sticker_path)
        try:
            return await self._bot.send_sticker(
                chat_id=self.chat_id, sticker=sticker_obj, disable_notification=not notification
            )
        except telegram.error.BadRequest as error:
            logger.error("Failed to send sticker %s: %s", sticker_path, error)
        return None

    def get_message(self, label_message: str) -> BaseMessage | None:
        """Get the message from the message queue matching the given label."""
        return next((x for x in self._message_queue if x.label == label_message), None)

    async def send_poll(self, question: str, options: list[str]) -> None:
        """Send a poll to the user with a question and options."""
        if self.scheduler.get_job(self.poll_name) is not None:
            await self.poll_delete()
        options = [emoji_replace(option) for option in options]
        self._poll = await self._bot.send_poll(
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
            next_run_time=datetime.datetime.now(tz=tzlocal.get_localzone())
            + datetime.timedelta(seconds=self.POLL_DEADLINE + 1),
            replace_existing=True,
        )

    async def poll_delete(self) -> None:
        """Run when the poll timeout has expired."""
        if self._poll is not None and self._poll.poll is not None:
            try:
                logger.info("Deleting poll '%s'", self._poll.poll.question)
                await self._bot.delete_message(chat_id=self.chat_id, message_id=self._poll.message_id)
            except telegram.error.BadRequest:
                logger.error("Poll message %s already deleted", self._poll.message_id)

    async def poll_answer(self, answer_id: int) -> None:
        """Run when a poll answer is received."""
        if (
            self._poll is None
            or self._poll.poll is None
            or self._poll_callback is None
            or not callable(self._poll_callback)
        ):
            logger.error("Poll is not defined")
            return

        answer_ascii = self._poll.poll.options[answer_id].text.encode("ascii", "ignore").decode()
        logger.info("%s's answer to question '%s' is '%s'", self.user_name, self._poll.poll.question, answer_ascii)
        if asyncio.iscoroutinefunction(self._poll_callback):
            await self._poll_callback(self._poll.poll.options[answer_id].text)
        else:
            self._poll_callback(self._poll.poll.options[answer_id].text)
        await asyncio.sleep(1)
        await self.poll_delete()

        if self.scheduler.get_job(self.poll_name) is not None:
            self.scheduler.remove_job(self.poll_name)
        self._poll = None
