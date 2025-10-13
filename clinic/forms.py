from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class StaffSignupForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=30, required=True)
    last_name  = forms.CharField(label="Sobrenome", max_length=30, required=False)
    email      = forms.EmailField(label="E-mail", required=True)

    class Meta:
        model  = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
        labels = {
            "username":  "Usuário",
            "password1": "Senha",
            "password2": "Confirmar senha",
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name  = self.cleaned_data.get("last_name", "")
        user.is_staff   = True         # terá acesso ao dashboard (pois usamos @staff_member_required)
        user.is_active  = True         # já pode entrar (sem aprovação)
        if commit:
            user.save()
        return user