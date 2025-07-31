from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = "Create or retrieve an API token for a user"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username for token creation")
        parser.add_argument(
            "--recreate",
            action="store_true",
            help="Recreate token if it already exists",
        )

    def handle(self, *args, **options):
        username = options["username"]
        recreate = options["recreate"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')

        if recreate:
            # Delete existing token if it exists
            Token.objects.filter(user=user).delete()

        token, created = Token.objects.get_or_create(user=user)

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created new token for user "{username}": {token.key}'
                )
            )
        else:
            if recreate:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Recreated token for user "{username}": {token.key}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Token already exists for user "{username}": {token.key}'
                    )
                )
                self.stdout.write(
                    self.style.WARNING("Use --recreate to generate a new token")
                )

        # Additional information
        self.stdout.write("")
        self.stdout.write("Usage:")
        self.stdout.write("  Add this header to your API requests:")
        self.stdout.write(f"  Authorization: Token {token.key}")
