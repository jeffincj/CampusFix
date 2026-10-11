"""Forms for student registration and login."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class StudentRegisterForm(UserCreationForm):
    """
    Sign-up form for students. The role is NOT a form field, so nobody
    can make themselves staff or admin by editing the HTML. Staff and
    admin accounts are created by an admin.
    """

    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        # Emails are stored lowercase so "A@x.com" and "a@x.com" are the same.
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT  # self-registration is always a student
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Django's standard login form; kept here so we can style it in one place."""

    username = forms.CharField(max_length=150)
