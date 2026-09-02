from .settings import *


ROOT_URLCONF = "config.urls_test"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
