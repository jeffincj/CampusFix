"""
Texts that are stored in the database in English but shown to students in their
language (department names, automatic history notes). gettext_noop only marks them
so "makemessages" puts them in the translation files; templates translate them
with {% translate value %}.
"""
from django.utils.translation import gettext_noop

DATABASE_TEXTS = [
    # Department names (complaints/seed.py)
    gettext_noop("Hostel Office"),
    gettext_noop("Mess & Food Committee"),
    gettext_noop("IT Services"),
    gettext_noop("Labs & Academics"),
    gettext_noop("Transport Office"),
    gettext_noop("Maintenance (Electrical & Plumbing)"),
    gettext_noop("Housekeeping & Sanitation"),
    gettext_noop("Security Office"),
    # Automatic notes in the status history
    gettext_noop("Complaint submitted"),
    gettext_noop("Changed in Django admin"),
    gettext_noop("Synthetic sample data"),
]
