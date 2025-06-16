from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from oauth2_provider.models import get_application_model

class Command(BaseCommand):
    help = "Setup admin user and OAuth2 application for MCP Inspector"

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='mcp_service', help='Admin username')
        parser.add_argument('--password', type=str, default='mcp_service123!', help='Admin password')
        parser.add_argument('--email', type=str, default='mcp_service@localhost', help='Admin email')
        parser.add_argument('--client-name', type=str, default='MCP Inspector App', help='OAuth app name')
        parser.add_argument('--redirect-uri', type=str, default='http://127.0.0.1:6274/auth/callback', help='OAuth redirect URI')

    def handle(self, *args, **options):
        User = get_user_model()
        Application = get_application_model()

        # 1. Create or get admin user
        username = options['username']
        password = options['password']
        email = options['email']
        user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'is_superuser': True, 'is_staff': True})
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Created admin user: {username}"))
        else:
            self.stdout.write(self.style.WARNING(f"ℹ️ Admin user '{username}' already exists"))

        # 2. Create or get OAuth2 application
        client_name = options['client_name']
        redirect_uri = options['redirect_uri']
        app, created = Application.objects.get_or_create(
            name=client_name,
            user=user,
            client_type=Application.CLIENT_PUBLIC,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            defaults={
                'redirect_uris': redirect_uri,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created OAuth2 app: {client_name}"))
        else:
            self.stdout.write(self.style.WARNING(f"ℹ️ OAuth2 app '{client_name}' already exists"))

        # 3. Output credentials
        self.stdout.write("\n🔑 OAuth2 Client Configuration:")
        self.stdout.write(f"Client ID:     {app.client_id}")
        self.stdout.write(f"Redirect URI:  {redirect_uri}")
        self.stdout.write(f"Auth URL:      http://127.0.0.1:8000/o/authorize/")
        self.stdout.write(f"Token URL:     http://127.0.0.1:8000/o/token/")
        self.stdout.write(f"Introspect:    http://127.0.0.1:8000/o/introspect/")
        self.stdout.write(f"Revocation:    http://127.0.0.1:8000/o/revoke/")