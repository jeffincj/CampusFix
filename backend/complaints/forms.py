"""Forms used by the student and staff HTML pages."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Complaint, Feedback
from .services import ALLOWED_TRANSITIONS


class ComplaintForm(forms.ModelForm):
    """Students write the complaint. Category is optional (AI will decide from Phase 5)."""

    class Meta:
        model = Complaint
        fields = ["title", "description", "category", "location", "block"]
        labels = {
            "title": _("Title"),
            "description": _("Description"),
            "category": _("Category (optional, our AI decides)"),
            "location": _("Location"),
            "block": _("Block / building (optional)"),
        }
        help_texts = {
            "description": _("Write in English, Tamil, Malayalam, or a mix."),
            "location": _("Example: Room 214, near the lift"),
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [("", _("Not sure"))] + list(Complaint.Category.choices)

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if len(text) < 10:
            raise forms.ValidationError(_("Please describe the problem in at least 10 characters."))
        return text


class StatusUpdateForm(forms.Form):
    """Staff/admin move a complaint to one of the allowed next statuses."""

    status = forms.ChoiceField()
    note = forms.CharField(max_length=300, required=False, widget=forms.TextInput(attrs={"placeholder": _("Optional note")}))

    def __init__(self, *args, complaint, **kwargs):
        super().__init__(*args, **kwargs)
        labels = dict(Complaint.Status.choices)
        # Only show statuses that the workflow allows from the current one.
        self.fields["status"].choices = [(s, labels[s]) for s in ALLOWED_TRANSITIONS[complaint.status]]


class FeedbackForm(forms.ModelForm):
    """The student rates the fix from 1 to 5."""

    rating = forms.TypedChoiceField(
        choices=[(i, f"{i} ★") for i in range(5, 0, -1)], coerce=int, widget=forms.RadioSelect
    )

    class Meta:
        model = Feedback
        fields = ["rating", "comment"]
        labels = {"rating": _("Rating"), "comment": _("Comment")}
        widgets = {"comment": forms.Textarea(attrs={"rows": 3})}
