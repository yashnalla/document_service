from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = 'Create test users (user1 and user2) with API tokens for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete existing users and recreate them',
        )

    def handle(self, *args, **options):
        users_data = [
            {'username': 'user1', 'email': 'user1@example.com'},
            {'username': 'user2', 'email': 'user2@example.com'},
        ]
        password = 'password123'

        for user_data in users_data:
            username = user_data['username']
            
            if options['force']:
                # Delete existing user if force flag is provided
                User.objects.filter(username=username).delete()
                self.stdout.write(f"Deleted existing user: {username}")

            try:
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=user_data['email'],
                    password=password
                )
                
                # Create API token
                token, created = Token.objects.get_or_create(user=user)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created user: {username} (password: {password})"
                    )
                )
                self.stdout.write(f"  API Token: {token.key}")
                
            except IntegrityError:
                # User already exists
                user = User.objects.get(username=username)
                token, created = Token.objects.get_or_create(user=user)
                
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ User already exists: {username}"
                    )
                )
                self.stdout.write(f"  API Token: {token.key}")

        self.stdout.write(
            self.style.SUCCESS(
                "\n✓ Test users setup complete!"
            )
        )
        self.stdout.write("You can now log in with:")
        self.stdout.write("  - Username: user1, Password: password123")
        self.stdout.write("  - Username: user2, Password: password123")