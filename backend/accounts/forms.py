"""Forms for student registration and login."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class StudentRegisterForm(UserCreationForm):
    """
    Sign-up form for students. The role is NOT a form field, so nobody
    can make themselves staff or admin by editing the HTML. Staff and
    admin accounts are created by an admin.
    """

    email = forms.EmailField(required=True, label=_("Email"))
    first_name = forms.CharField(max_length=150, required=True, label=_("First name"))
    last_name = forms.CharField(max_length=150, required=False, label=_("Last name"))

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Our own labels and help texts, so every language we support has them translated.
        self.fields["username"].help_text = _("Letters, numbers and @ . + - _ only.")
        self.fields["password1"].label = _("Password")
        self.fields["password1"].help_text = _("At least 8 characters. Not too common, not only numbers, not similar to your name.")
        self.fields["password2"].label = _("Password confirmation")
        self.fields["password2"].help_text = _("Enter the same password again.")

    def clean_email(self):
        # Emails are stored lowercase so "A@x.com" and "a@x.com" are the same.
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT  # self-registration is always a student
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Django's standard login form; kept here so we can style it in one place."""

    username = forms.CharField(max_length=150, label=_("Username"))
    password = forms.CharField(label=_("Password"), strip=False, widget=forms.PasswordInput)
