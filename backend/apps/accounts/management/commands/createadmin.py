"""
Management command to create admin user.
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import AdminUser


class Command(BaseCommand):
    help = 'Create a super admin user for Kavithedal Publications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Admin email address',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Admin username',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Admin password',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            help='Admin first name',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            help='Admin last name',
        )
        parser.add_argument(
            '--role',
            type=str,
            choices=['admin', 'superadmin'],
            default='superadmin',
            help='Admin role',
        )

    def handle(self, *args, **options):
        email = options.get('email') or input('Email: ')
        username = options.get('username') or input('Username: ')
        password = options.get('password') or input('Password: ')
        first_name = options.get('first_name') or input('First Name (optional): ')
        last_name = options.get('last_name') or input('Last Name (optional): ')
        role = options.get('role', 'superadmin')

        if AdminUser.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'Admin with email {email} already exists')
            )
            return

        admin = AdminUser.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_staff=True,
            is_superuser=(role == 'superadmin'),
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created admin user: {admin.email}')
        )
