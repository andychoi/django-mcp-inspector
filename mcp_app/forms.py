from django import forms
from oauth2_provider.models import get_application_model

class MCPLauncherForm(forms.Form):
    client_id = forms.CharField(
        required=False,
        label="OAuth Client ID",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    client_secret = forms.CharField(
        required=False,
        label="Client Secret (Optional)",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    mcp_service_username = forms.CharField(
        required=False,
        label="Service Username (Optional)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        client_id = cleaned_data.get("client_id")
        client_secret = cleaned_data.get("client_secret")
        if client_id:
            Application = get_application_model()
            try:
                app = Application.objects.get(client_id=client_id)
            except Application.DoesNotExist:
                raise forms.ValidationError(
                    "OAuth2 Application with this client ID does not exist."
                )
            # If the app is confidential, require a client_secret
            if app.client_type == Application.CLIENT_CONFIDENTIAL and not client_secret:
                self.add_error(
                    "client_secret",
                    "Client secret is required for confidential applications."
                )
        return cleaned_data
    

class CodeEntryForm(forms.Form):
    code = forms.CharField(
        label="Authorization Code",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Paste the code here'})
    )