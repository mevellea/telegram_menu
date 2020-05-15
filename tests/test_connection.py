# -*- coding: utf-8 -*scheduler-

"""Test telegram_menu package."""

import datetime
import logging
import time
import unittest

from telegram_menu import BaseMessage, ButtonType, MenuButton, SessionManager

# this is a testing key, do not use it in production!
API_KEY = "872134523:AAEe0_y78tnYYEWNUn2QRahnd48rjKhsxSA"


class OptionsAppMessage(BaseMessage):
    """Options app message, show an example of a button with inline buttons."""

    LABEL = "options"

    def __init__(self, navigation, update_callback):
        """Init OptionsAppMessage class."""
        super().__init__(navigation, OptionsAppMessage.LABEL)

        self.is_inline = True
        self.play_pause = True
        update_callback.append(self.app_update_display)

    def app_update_display(self):
        """Update message content when callback triggered."""
        self.play_pause = not self.play_pause
        edited = self.edit_message()
        if edited:
            self.is_alive()

    def kill_message(self):
        """Kill message after this callback."""
        self.play_pause = not self.play_pause
        return "Kill message"

    def action_button(self):
        """Execute an action and return notification content."""
        self.play_pause = not self.play_pause
        return "option selected!"

    def text_button(self):
        """Display any text data."""
        self.play_pause = not self.play_pause
        data = [["text1", "value1"], ["text2", "value2"]]
        return self.format_list_to_html(data)

    def picture_button(self):
        """Display a picture."""
        self.play_pause = not self.play_pause
        return "resources/stats_default.png"

    def picture_button2(self):
        """Display an undefined picture."""
        self.play_pause = not self.play_pause

    def content_updater(self):
        """Update message content."""
        play_pause_button = "play_button" if self.play_pause else "pause_button"
        self.keyboard = [
            MenuButton(self.emojize(play_pause_button), self.action_button),
            MenuButton(self.emojize("twisted_rightwards_arrows"), self.action_button),
            MenuButton(self.emojize("chart_with_upwards_trend"), self.picture_button, ButtonType.PICTURE),
            MenuButton(self.emojize("chart_with_downwards_trend"), self.picture_button2, ButtonType.PICTURE),
            MenuButton(self.emojize("door"), self.text_button, ButtonType.MESSAGE),
            MenuButton(self.emojize("speaker_medium_volume"), self.action_button),
            MenuButton(self.emojize("speaker_high_volume"), self.action_button),
        ]
        return "Status updated!"


class ActionAppMessage(BaseMessage):
    """Single action message."""

    LABEL = "action"

    def __init__(self, navigation):
        """Init ActionAppMessage class."""
        super().__init__(navigation, ActionAppMessage.LABEL)
        # go back to home menu after executing the action
        self.is_inline = True
        self.home_after = True
        self.expiry_period = datetime.timedelta(seconds=5)

    def content_updater(self):
        """Update message content."""
        return "<code>Action!</code>"


class SecondMenuMessage(BaseMessage):
    """Second example of menu."""

    LABEL = "second_message"

    def __init__(self, navigation, update_callback):
        """Init SecondMenuMessage class."""
        super().__init__(navigation, SecondMenuMessage.LABEL)

        action_message = ActionAppMessage(self._navigation)
        option_message = OptionsAppMessage(self._navigation, update_callback)
        self.add_button("Option", option_message)
        self.add_button("Action", action_message)
        self.add_button("Back")
        self.add_button("Home")

    def content_updater(self):
        """Update message content."""
        return "Second message"


class StartMessage(BaseMessage):
    """Start menu, create all app sub-menus."""

    LABEL = "start"

    def __init__(self, navigation, update_callback):
        """Init StartMessage class."""
        super().__init__(navigation, StartMessage.LABEL)

        # define menu buttons
        action_message = ActionAppMessage(navigation)
        second_menu = SecondMenuMessage(navigation, update_callback)
        self.add_button("Action", action_message)
        self.add_button("Second menu", second_menu)

    def content_updater(self):
        """Update message content."""
        return "Start message!"


class Test(unittest.TestCase):
    """The basic class that inherits unittest.TestCase."""

    def test_wrong_api_key(self):
        """Test starting a client with wrong key."""
        with self.assertRaises(AttributeError):
            SessionManager(None)

        with self.assertRaises(AttributeError):
            SessionManager(1234)

        with self.assertRaises(AttributeError):
            SessionManager("1234:5678")

    def test_bad_start_message(self):
        """Test starting a client with bad start message."""
        manager = SessionManager(API_KEY)

        with self.assertRaises(AttributeError):
            manager.start(MenuButton)

        with self.assertRaises(AttributeError):
            manager.start(StartMessage, 1)

        manager.updater.stop()

    def test_client_connection(self):
        """Run the client test."""
        init_logger()
        update_callback = []

        manager = SessionManager(API_KEY)
        manager.start(StartMessage, update_callback)

        session = None
        while not session:
            session = manager.get_session()
            time.sleep(1)

        msg_id = session.select_menu_button("Action")
        self.assertGreater(msg_id, 1)
        time.sleep(0.5)
        manager.broadcast("Test message")
        time.sleep(0.5)
        session.select_menu_button("Action")
        time.sleep(0.5)
        session.select_menu_button("Second menu")
        time.sleep(0.5)
        session.select_menu_button("Back")
        time.sleep(0.5)
        session.select_menu_button("Second menu")
        time.sleep(0.5)
        session.select_menu_button("Home")
        time.sleep(0.5)
        session.select_menu_button("Second menu")
        time.sleep(0.5)
        session.goto_home()
        time.sleep(0.5)
        session.select_menu_button("Second menu")
        time.sleep(0.5)
        session.select_menu_button("Option")

        # run the update callback to trigger edition
        update_callback[0]()

        time.sleep(7)

        manager.updater.stop()


def init_logger():
    """Initialize logger properties."""
    log_formatter = logging.Formatter(
        fmt="%(asctime)s [%(name)s] [%(levelname)s]  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    root_logger = logging.getLogger()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # start scheduler
    logging.getLogger("apscheduler.scheduler").setLevel(logging.ERROR)
    logging.getLogger("apscheduler.executors").setLevel(logging.ERROR)
