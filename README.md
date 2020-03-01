# telegram_menu
A python library for generating Telegram menu and application message.
## Installation
```bash
$ python setup.py install
```

## Getting Started

This library provides classes to generate menu using `python-telegram-bot` package, which runs on top of the `Telegram Bot Api`. It's compatible with Python versions 3.5+.

### Learning by example

You can refer to sample menu in ``tests\test_connection.py`` to have an example of all features available.

Next code example will create a single ``Hello, World!`` message:

```python
from telegram_menu import MenuMessage, SessionManager

API_KEY = "put_your_telegram_bot_api_key_here"

class StartMessage(MenuMessage):
    """Start menu, create all app sub-menus."""

    LABEL = "start"

    def __init__(self, navigation):
        """Init StartMessage class."""
        MenuMessage.__init__(self, navigation, StartMessage.LABEL)

    def content_updater(self):
        """Update message content."""
        return "Hello, world!"

SessionManager(API_KEY, StartMessage)
```

You can add any button in ``StartMessage``, using ``self.add_button()`` method:


```python
# run_and_notify() is a class method which runs something and returns a string as Telegram notification
self.add_button("Action", self.run_and_notify)

# new_menu is a class derived from MenuMessage, which will generate a new menu
self.add_button("NewMenu", new_menu)

# new_app is a class derived from AppMessage, which will generate an application message
self.add_button("NewApp", new_app)
```

An application message can contain several inlined buttons, which have same behavior as MenuMessage buttons.

```python
# run_and_notify() is a class method which runs something and returns a string as Telegram notification
self.add_button("Action", self.run_and_notify)

# get_content() is a class method which generate some text to display, eventually with markdown formatting
self.add_button("Display content", self.get_content, ButtonType.MESSAGE)

# get_picture() is a class method which returns the path of a picture to display
self.add_button("Show picture", self.get_picture, ButtonType.PICTURE)
```