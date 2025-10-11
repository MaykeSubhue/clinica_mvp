# clinic/forms.py
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django import forms

class StaffForm(forms.ModelForm):
    # ... (como você já tem)
    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("Este usuário já existe.")
        return username

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password"]
        labels = {
            "username": "Usuário",
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
        }
