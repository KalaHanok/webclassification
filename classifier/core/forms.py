# core/forms.py
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django import forms

class CustomUserCreationForm(UserCreationForm):
    device_id = forms.CharField(
        max_length=36,
        required=True,
        help_text="Enter your device ID"
    )

    class Meta:
        model = User
        fields = ("username", "device_id", "password1", "password2")