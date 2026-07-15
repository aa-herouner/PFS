from django.apps import AppConfig


class FeedConfig(AppConfig):
    name = 'feed'

    def ready(self):
        from . import signals  # noqa: F401  (registers post_save handler)
