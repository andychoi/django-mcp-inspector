from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from oauth2_provider.models import get_application_model

class Command(BaseCommand):
    help = "Setup admin user and OAuth2 application for MCP Inspector (public or confidential)"

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='mcp_service', help='Admin username')
        parser.add_argument('--password', type=str, default='mcp_service123!', help='Admin password')
        parser.add_argument('--email', type=str, default='mcp_service@localhost', help='Admin email')
        parser.add_argument('--client-name', type=str, default='MCP Inspector App', help='OAuth app name')
        parser.add_argument('--redirect-uri', type=str, default='http://127.0.0.1:6274/auth/callback', help='OAuth redirect URI')
        parser.add_argument('--client-id', type=str, help='Use existing OAuth2 client ID')
        parser.add_argument('--client-secret', type=str, default='', help='OAuth2 client secret (for confidential apps)')

    def handle(self, *args, **options):
        User = get_user_model()
        Application = get_application_model()

        # 1) Create or get admin user
        username = options['username']
        password = options['password']
        email = options['email']
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_superuser': True, 'is_staff': True}
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Created admin user: {username}"))
        else:
            self.stdout.write(self.style.WARNING(f"ℹ️ Admin user '{username}' already exists"))

        # 2) Create or update OAuth2 application
        client_id = options.get('client_id')
        client_secret = options.get('client_secret')
        client_name = options['client_name']
        redirect_uri = options['redirect_uri']

        if client_id:
            # Use existing application
            try:
                app = Application.objects.get(client_id=client_id)
                self.stdout.write(self.style.SUCCESS(f"✅ Using existing OAuth2 app: {app.name}"))
            except Application.DoesNotExist:
                raise CommandError(f"OAuth2 Application with client_id={client_id} not found.")
        else:
            # Determine client type
            client_type = (Application.CLIENT_CONFIDENTIAL if client_secret
                           else Application.CLIENT_PUBLIC)
            app, created = Application.objects.get_or_create(
                name=client_name,
                user=user,
                client_type=client_type,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                defaults={'redirect_uris': redirect_uri},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created OAuth2 app: {app.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"ℹ️ OAuth2 app '{app.name}' already exists"))

        # 3) For confidential apps, ensure secret
        if app.client_type == Application.CLIENT_CONFIDENTIAL:
            if client_secret:
                # override stored secret if provided
                app.client_secret = client_secret
                app.save()
                self.stdout.write(self.style.SUCCESS("✅ Updated client secret for confidential app"))
            elif not app.client_secret:
                self.stdout.write(self.style.ERROR("❌ Confidential app missing secret. Provide --client-secret."))

        # 4) Display configuration
        self.stdout.write("\n🔑 OAuth2 Client Configuration:")
        self.stdout.write(f"Client ID:     {app.client_id}")
        if app.client_type == Application.CLIENT_CONFIDENTIAL:
            self.stdout.write(f"Client Secret: {app.client_secret}")
        self.stdout.write(f"Redirect URI:  {redirect_uri}")
        self.stdout.write(f"Auth URL:      http://127.0.0.1:8000/o/authorize/")
        self.stdout.write(f"Token URL:     http://127.0.0.1:8000/o/token/")
        self.stdout.write(f"Introspect:    http://127.0.0.1:8000/o/introspect/")
        self.stdout.write(f"Revocation:    http://127.0.0.1:8000/o/revoke/")
