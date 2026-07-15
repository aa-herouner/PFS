from django.apps import AppConfig


class HealthConfig(AppConfig):
    name = 'health'

    def ready(self):
        from . import signals  # noqa: F401  (registers post_save handler)
