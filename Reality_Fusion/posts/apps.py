from django.apps import AppConfig
from django.db.models.signals import post_migrate


def auto_seed(sender, **kwargs):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if User.objects.count() == 0:
        from .management.commands.seed_data import Command as SeedCommand
        SeedCommand().handle()


class PostsConfig(AppConfig):
    name = 'posts'

    def ready(self):
        post_migrate.connect(auto_seed, sender=self)