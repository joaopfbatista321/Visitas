from django.apps import AppConfig


class FisioterapiaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fisioterapia"
    verbose_name = "Fisioterapia"

    def ready(self):
        import fisioterapia.signals  # noqa: F401