# telegram_menu package

<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="drawing"/> <img src="https://img.shields.io/badge/python--telegram--bot-22.x-blue.svg" alt="drawing"/>
<br/>
A python library to generate navigation menus using Telegram Bot API.

Features:

* Menu navigation using tree structure, unlimited depth
* Support for sending pictures (local file or url), stickers, documents, audio, video, voice, albums, notifications, webapps and polls
* Rich polls: quiz mode, multiple answers, anonymity and configurable lifetime
* Emoji reactions on messages (`ButtonType.REACTION`)
* Copy-to-clipboard buttons (`ButtonType.COPY`)
* Animated message effects and link-preview control
* Bot command menu and chat menu button configuration
* Session manager with multiple users connecting to the same bot
* Messages can read text input from the keyboard
* Automatic deletion of messages when configurable timer has expired
* Integration of HTML formatting + emojis

> **_[2026] NOTE:_** version 3.1.0 adds new button/media types (reactions, copy buttons, documents/audio/video/voice, albums), rich polls, message effects, link-preview control and bot command/menu helpers, leveraging Bot API 9.x available in python-telegram-bot 22.x.
>
> **_[2025] NOTE:_** version 3.0.0 targets Python 3.10+ and python-telegram-bot 22.x. Use a 2.x release for older interpreters.
>
> **_[2023-01] NOTE:_** asyncio support was added in version 2.0.0. Previous versions use the oldest non-asynchronous version of python-telegram-bot and are not compatible.

Here is an example of navigation with menus and inlined buttons:

![Demo: TelegramMenuSession]  

## Installation

```bash
pip install telegram_menu
```

## Getting Started

You first need to [create a Telegram bot], then you can refer to the sample code in ``tests/example_app.py`` (run it with ``tests/demo.py``) for a complete use-case.

A session can be started with the keyword ``/start`` from a Telegram client.

Following code block creates a ``Hello, World!`` message:

```python
from telegram_menu import BaseMessage, TelegramMenuSession, NavigationHandler

API_KEY = "put_your_telegram_bot_api_key_here"

class StartMessage(BaseMessage):
    """Start menu, create all app sub-menus."""

    LABEL = "start"

    def __init__(self, navigation: NavigationHandler) -> None:
        """Init StartMessage class."""
        super().__init__(navigation, StartMessage.LABEL)

    def update(self) -> str:
        """Update message content."""
        return "Hello, world!"

TelegramMenuSession(API_KEY).start(StartMessage)
```

You can add new buttons in ``StartMessage``, using ``self.add_button()`` method. 
The callback of a button can be used to update the content of the current message, or to open a new menu.
For example, adding these lines in the constructor of the previous class will open a second menu:

```python
second_menu = SecondMenuMessage(navigation)
self.add_button(label="Second menu", callback=second_menu)
```

Then define the second message:

```python
class SecondMenuMessage(BaseMessage):
    """Second menu, create an inlined button."""

    LABEL = "action"

    def __init__(self, navigation: NavigationHandler) -> None:
        """Init SecondMenuMessage class."""
        super().__init__(navigation, StartMessage.LABEL, inlined=True)

        # 'run_and_notify' function executes an action and return a string as Telegram notification.
        self.add_button(label="Action", callback=self.run_and_notify)
        # 'back' button goes back to previous menu
        self.add_button_back()
        # 'home' button goes back to main menu
        self.add_button_home()

    def update(self) -> str:
        """Update message content."""
        # emoji can be inserted with a keyword enclosed with ::
        # list of emojis can be found at this link: https://www.webfx.com/tools/emoji-cheat-sheet/
        return ":warning: Second message"

    @staticmethod
    def run_and_notify() -> str:
        """Update message content."""
        return "This is a notification"
```

An application message can contain several inlined buttons, the behavior is similar to MenuMessage buttons.
To define a message as inlined, the property ``inlined`` must be set to ``True``.

A message can also be used to create a poll or show a picture, using property ``btype``.

The input field can be set using the property ``input_field`` (non-inlined messages only). You can use the keyword ``<disable>`` to restore the default behaviour. 

The default number of buttons per row is 2 for base keyboards, 4 for inlined keyboards, 
to create a new row the property ``new_row`` can be set to ``True`` when calling ``add_button()``.

```python
from telegram_menu import MenuButton

# 'get_content' function must return the text content to display, eventually with Markdown formatting
self.add_button(label="Display content", callback=self.get_content, btype=ButtonType.MESSAGE)

# 'get_picture' function must return the path of a picture to display in Telegram
self.add_button(label="Show picture", callback=self.get_picture, btype=ButtonType.PICTURE, new_row=True)

# 'get_sticker' function must return the path of a sticker to display in Telegram
self.add_button(label="Show sticker", callback=self.get_sticker, btype=ButtonType.STICKER)

# 'webapp_cb' function will receive the result of the given web-app
webapp_url = "https://python-telegram-bot.org/static/webappbot"
self.add_button(label="Show picture", callback=self.webapp_cb, web_app_url=webapp_url)

# New buttons can be added to the 'keyboard' property of the message instance too.
# Next poll message will get items to display from function 'get_playlists_arg', and run 'select_playlist' when 
# the poll button is selected, identified with emoji 'closed_book'
poll_button = MenuButton(
    label=":closed_book:", callback=self.select_playlist, btype=ButtonType.POLL, args=self.get_playlists_arg()
)
self.keyboard.append([poll_button])
```

## New in 3.1.0 (Bot API 9.x)

These features rely on capabilities available in python-telegram-bot 22.x.

```python
# Copy-to-clipboard button: pressing it copies 'copy_text' (or the label) on the client.
self.add_button(label=":clipboard: Copy code", btype=ButtonType.COPY, copy_text="ABC-123")

# Emoji reaction: the callback returns the emoji to set on the current message.
self.add_button(label=":thumbs_up:", callback=lambda: ":thumbs_up:", btype=ButtonType.REACTION)

# Extra media types: the callback returns a local path or a url.
self.add_button(label="File", callback=self.get_doc, btype=ButtonType.DOCUMENT)   # also AUDIO / VIDEO / VOICE

# Rich poll (quiz / multiple answers / lifetime) via an optional 3rd args element.
quiz_opts = {"poll_type": "quiz", "correct_option_id": 1, "explanation": "2 + 2 = 4", "open_period": 30}
self.add_button(label="Quiz", callback=self.on_answer, btype=ButtonType.POLL, args=["2 + 2?", ["3", "4"], quiz_opts])
```

Messages can also play an animated effect and control the link preview:

```python
super().__init__(navigation, self.LABEL, message_effect_id="5104841245755180586", disable_web_page_preview=True)
```

The session exposes album broadcasting and bot command/menu helpers:

```python
session = TelegramMenuSession(API_KEY)
# register the slash command menu when the bot starts
session.start(StartMessage, commands=[("start", "Start the bot"), ("help", "Show help")])

# or, once running:
await session.set_menu_button(web_app_url="https://example.com", web_app_text="Open app")
await session.broadcast_media_group(["pic1.png", "https://example.com/pic2.png"])
```

## Structure

Classes in package ``telegram_menu`` are stored in 2 python files:


* [navigation.py] - Main interface, menu and message generation and management
* [models.py] - Menu and message models, classes definition

<img src="https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/packages.png" width="400"/>

Following class diagram describes all public interfaces:

<img src="https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/classes.png" width="800"/>

[navigation.py]: https://github.com/mevellea/telegram_menu/blob/master/telegram_menu/navigation.py
[models.py]: https://github.com/mevellea/telegram_menu/blob/master/telegram_menu/models.py
[create a Telegram bot]: https://github.com/python-telegram-bot/python-telegram-bot/wiki/Introduction-to-the-API
[Demo: TelegramMenuSession]: https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/demo.gif

## Unit-tests

To execute the test suite, run the following command and then start a session from a Telegram client with the keyword **/start**.

```bash
python -m unittest
```