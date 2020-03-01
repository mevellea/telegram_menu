# -*- coding: utf-8 -*scheduler-

"""Test telegram_menu package."""

import logging
import time

from telegram_menu import AppMessage, ButtonType, MenuButton, MenuMessage, format_list_to_html, SessionManager

# this key is for testing only, do not use it in production!
API_KEY = "1137336406:AAEfshEFKovLe2ia_mq2KsgTuAgxazLM9s0"


class OptionsAppMessage(AppMessage):
    """Options app message, show an example of a button with inline buttons."""

    LABEL = "options"

    def __init__(self, navigation):
        """Init OptionsAppMessage class."""
        AppMessage.__init__(self, navigation, OptionsAppMessage.LABEL)

    def app_update_display(self):
        """Update message content when callback triggered."""
        edited = self.edit_message()
        if edited:
            self.is_alive()

    @staticmethod
    def kill_message():
        """Kill message after this callback."""
        return "Kill message"

    @staticmethod
    def action_button():
        """Execute an ction and return notification content."""
        return "option selected!"

    @staticmethod
    def text_button():
        """Display any text data."""
        data = [["text1", "value1"], ["text2", "value2"]]
        return format_list_to_html(data)

    @staticmethod
    def picture_button():
        """Display a picture."""
        return "resources/stats_default.png"

    def content_updater(self):
        """Update message content."""
        self.keyboard = [
            MenuButton(self.emojize("play_button"), self.action_button),
            MenuButton(self.emojize("twisted_rightwards_arrows"), self.action_button),
            MenuButton(self.emojize("speaker_medium_volume"), self.action_button),
            MenuButton(self.emojize("speaker_high_volume"), self.action_button),
            MenuButton(self.emojize("door"), self.text_button, ButtonType.MESSAGE),
            MenuButton(self.emojize("chart_with_upwards_trend"), self.picture_button, ButtonType.PICTURE),
        ]
        return "Status updated!"


class ActionAppMessage(AppMessage):
    """Single action message."""

    LABEL = "action"

    def __init__(self, navigation):
        """Init ActionAppMessage class."""
        AppMessage.__init__(self, navigation, ActionAppMessage.LABEL)
        # go back to home menu after executing the action
        self.home_after = True

    def content_updater(self):
        """Update message content."""
        return f"<code>Action!</code>"


class SecondMenuMessage(MenuMessage):
    """Second example of menu."""

    LABEL = "second_message"

    def __init__(self, navigation):
        """Init SecondMenuMessage class."""
        MenuMessage.__init__(self, navigation, SecondMenuMessage.LABEL)

        action_message = ActionAppMessage(self.navigation)
        option_message = OptionsAppMessage(self.navigation)
        self.add_button("Option", option_message)
        self.add_button("Action", action_message)
        self.add_button("Back")
        self.add_button("Home")

    def content_updater(self):
        """Update message content."""
        return "Second message"


class StartMessage(MenuMessage):
    """Start menu, create all app sub-menus."""

    LABEL = "start"

    def __init__(self, navigation):
        """Init StartMessage class."""
        MenuMessage.__init__(self, navigation, StartMessage.LABEL)

        # define menu buttons
        action_message = ActionAppMessage(navigation)
        second_menu = SecondMenuMessage(navigation)
        self.add_button("Action", action_message)
        self.add_button("Second menu", second_menu)

    def content_updater(self):
        """Update message content."""
        return "Start message!"


def test_client():
    """Run the client test."""
    init_logger()
    manager = SessionManager(API_KEY, StartMessage)
    time.sleep(30)
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
