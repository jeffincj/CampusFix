"""The 8 campus departments. Codes match Complaint.Category values."""

DEPARTMENTS = [
    ("HOSTEL", "Hostel Office", "Rooms, furniture, water supply in hostels, warden issues."),
    ("MESS", "Mess & Food Committee", "Food quality, hygiene, timings, menu, mess staff."),
    ("IT", "IT Services", "Wi-Fi, internet, campus portal, computer accounts."),
    ("LAB", "Labs & Academics", "Lab equipment, practicals, classrooms, projectors."),
    ("TRANSPORT", "Transport Office", "College buses, routes, timings, drivers."),
    ("MAINTENANCE", "Maintenance (Electrical & Plumbing)", "Power cuts, fans, lights, leaks, taps, toilets not working."),
    ("SANITATION", "Housekeeping & Sanitation", "Cleaning, garbage, washrooms hygiene, pests."),
    ("SECURITY", "Security Office", "Safety, theft, gate entry, ragging, CCTV, lighting at night."),
]


def seed_departments(department_model):
    """Create or update the departments. Safe to run many times."""
    for code, name, description in DEPARTMENTS:
        department_model.objects.update_or_create(code=code, defaults={"name": name, "description": description})
