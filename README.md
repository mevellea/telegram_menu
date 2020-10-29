# telegram_menu package

A python library to generate navigation menus using Telegram Bot API.

Base classes `MenuMessage` and `AppMessage` help defining  
applications buttons to navigate in a message tree. 

Features:

* Menu navigation using tree structure, unlimited depth
* Support for sending pictures, notifications, and polls
* Session manager when multiple users connect to the same bot
* Automatic deletion of messages when configurable timer has expired
* Integration of markdown format + emojis

Here is an example of navigation with menus and inline menus:

![Demo: TelegramMenuSession](https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/demo.gif)

## Installation

```bash
pip install telegram_menu
```

## Getting Started

You first need to [create a Telegram bot](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Introduction-to-the-API), then you can refer to sample code in ``tests\test_connection.py`` to run a complete use-case.

Following code block creates a ``Hello, World!`` message:

```python
from telegram_menu import BaseMessage, TelegramMenuSession

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

You can add any button in ``StartMessage``, using ``self.add_button()`` method:

```python
# 'run_and_notify' function executes an action and return a string as Telegram notification.
self.add_button(label="Action", callback=self.run_and_notify)

# 'new_menu_app' is a class derived from MenuMessage or AppMessage, which will generate a new menu or a message.
self.add_button(label="NewMenu", callback=new_menu_app)
```

An application message can contain several inlined buttons. The behavior is similar to MenuMessage buttons.

```python
# 'get_content' function generates some text to display, eventually with markdown formatting
self.add_button(label="Display content", callback=self.get_content, btype=ButtonType.MESSAGE)

# 'get_picture' function returns the path of a picture to display in Telegram
self.add_button(label="Show picture", callback=self.get_picture, btype=ButtonType.PICTURE)

# new buttons can be added to the 'keyboard' property of the message instance too.
# next poll message will get items to display from function 'get_playlists_arg', and run 'select_playlist' when 
# the poll button is selected, identified with emoji 'closed_book'
poll_button = MenuButton(
    label=emojize("closed_book"), callback=self.select_playlist, btype=ButtonType.POLL, args=self.get_playlists_arg()
)
self.keyboard.append(poll_button)
```

## Structure

Classes in package ``telegram_menu`` are stored in 2 python files:


* [navigation.py](telegram_menu/navigation.py): main interface, menu and message generation and management
* [models.py](telegram_menu/models.py): menu and message models, classes definition

<img src="https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/packages.png" width="400"/>

Following class diagram describes all public interfaces:

<img src="https://raw.githubusercontent.com/mevellea/telegram_menu/master/resources/classes.png" width="800"/>
