"""
Crea los dos usuarios iniciales de la demo tomando credenciales de .env.
Uso:  python manage.py seed_users
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea los usuarios Auditoria2027 y LucasCastro definidos en .env.'

    def handle(self, *args, **opts):
        User = get_user_model()

        users = [
            (os.environ.get('SEED_USER_1', 'Auditoria2027'),
             os.environ.get('SEED_PASS_1', 'Tpaso2019')),
            (os.environ.get('SEED_USER_2', 'LucasCastro'),
             os.environ.get('SEED_PASS_2', 'LCastro2026')),
        ]

        for username, password in users:
            obj, creado = User.objects.get_or_create(
                username=username,
                defaults={'is_active': True},
            )
            obj.set_password(password)       # Argon2id
            obj.is_active = True
            obj.save()
            accion = 'creado' if creado else 'actualizado'
            self.stdout.write(self.style.SUCCESS(f'✓ {username} {accion}'))

        self.stdout.write(self.style.WARNING(
            'Recordá cambiar las contraseñas en .env después de la prueba.'))
