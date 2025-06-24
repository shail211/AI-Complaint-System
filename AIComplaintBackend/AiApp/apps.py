from django.apps import AppConfig

class AiappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'AiApp'

    def ready(self):
        # Import db module when Django starts
        from . import db