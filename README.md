# telegram_menu package

A python library to generate navigation menus using Telegram Bot API.

Base classes `MenuMessage` and `AppMessage` help to define  
applications buttons to navigate in a message tree. 

Features:

* Menu navigation using tree structure, unlimited depth
* Support for sending pictures, notifications, and polls
* Session manager when multiple users connect to the same bot
* Automatic deletion of messages when configurable timer has expired
* Integration of markdown format + emojis

Here is an example of navigation with menus and inline menus:

![Demo: TelegramMenuSession]

## Installation

```bash
pip install telegram_menu
```

## Getting Started

You first need to [create a Telegram bot], then you can refer to sample code in ``tests\test_connection.py`` to run a complete use-case.

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
A button can be used to update the content of the current message, or open a new menu.
For example, adding these lines in the constructor of the previous class will open a second menu:

```python
second_menu = SecondMenuMessage(navigation)
self.add_button(label="Second menu", callback=second_menu)
```

Then define the second (inlined) message:

```python
class SecondMenuMessage(BaseMessage):
    """Start menu, create all app sub-menus."""

    LABEL = "start"

    def __init__(self, navigation: NavigationHandler) -> None:
        """Init StartMessage class."""
        super().__init__(navigation, StartMessage.LABEL, inlined=True)

        # 'run_and_notify' function executes an action and return a string as Telegram notification.
        self.add_button(label="Action", callback=self.run_and_notify)

    def update(self) -> str:
        """Update message content."""
        # emoji can be inserted with a keyword enclosed with ::
        # list of emojis can be found at this link: https://www.webfx.com/tools/emoji-cheat-sheet/
        return ":warnings: Second message"

    @staticmethod
    def run_and_notify() -> str:
        """Update message content."""
        return "This is a notification"
```

An application message can contain several inlined buttons. The behavior is similar to MenuMessage buttons.
To define a message as inlined, the property ``inlined`` must be set to ``True``.

A message can also be used to create a poll or show a picture, using property ``btype``.

```python
# 'get_content' function generates some text to display, eventually with markdown formatting
self.add_button(label="Display content", callback=self.get_content, btype=ButtonType.MESSAGE)

# 'get_picture' function returns the path of a picture to display in Telegram
self.add_button(label="Show picture", callback=self.get_picture, btype=ButtonType.PICTURE)

# new buttons can be added to the 'keyboard' property of the message instance too.
# next poll message will get items to display from function 'get_playlists_arg', and run 'select_playlist' when 
# the poll button is selected, identified with emoji 'closed_book'
from telegram_menu import MenuButton

poll_button = MenuButton(
    label=emojize("closed_book"), callback=self.select_playlist, btype=ButtonType.POLL, args=self.get_playlists_arg()
)
self.keyboard.append(poll_button)
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