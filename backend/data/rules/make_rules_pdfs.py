"""
Create SAMPLE college rule PDFs for the RAG demo (made-up rules, not a real college's).

    python data/rules/make_rules_pdfs.py      (from backend/)

Uses Matplotlib's PDF backend so no extra library is needed.
"""
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

plt.rcParams["pdf.fonttype"] = 42  # embed real fonts so the text can be extracted again

DOCUMENTS = {
    "hostel_rules.pdf": ("Hostel Rules and Regulations (Sample)", [
        ["1. Hostel timings",
         "The hostel gates close at 9:30 PM on weekdays and at 10:30 PM on Saturdays and Sundays. Students who return "
         "late must sign the late-entry register at the security desk and inform the warden. Three late entries in a "
         "month lead to a written warning and a fine of Rs. 500.",
         "2. Visitors",
         "Visitors are allowed only in the common visitor room between 4:00 PM and 7:00 PM. Visitors must show an ID "
         "card at the gate. Visitors are not allowed inside student rooms. Parents may stay in the guest room for up to "
         "two nights with prior approval from the warden.",
         "3. Room maintenance",
         "Students must report broken furniture, fans, lights or locks through CampusFix within 24 hours. Damage caused "
         "by a student is charged to that student. Room inspections take place on the first Monday of every month."],
        ["4. Electrical appliances",
         "Electric kettles, induction stoves, heaters and irons are not allowed in rooms because of fire risk. "
         "Appliances found during inspection are confiscated and returned only at the end of the semester. Laptops, "
         "phone chargers and table lamps are allowed.",
         "5. Leave and night-out",
         "Students going home must apply for leave on the portal at least one day before leaving. Night-outs require "
         "written permission from parents sent to the warden by email.",
         "6. Ragging",
         "Ragging in any form is a criminal offence and is strictly prohibited. Any student involved in ragging will be "
         "suspended immediately and the case reported to the anti-ragging committee and the police. Victims can "
         "complain through CampusFix, the anti-ragging helpline, or directly to the warden."],
    ]),
    "mess_rules.pdf": ("Mess Rules and Food Policy (Sample)", [
        ["1. Mess timings",
         "Breakfast is served from 7:15 AM to 9:00 AM, lunch from 12:15 PM to 2:00 PM, snacks from 4:30 PM to 5:30 PM "
         "and dinner from 7:30 PM to 9:15 PM. On exam days breakfast starts at 6:45 AM.",
         "2. Mess fee and refunds",
         "The mess fee is paid every semester. A refund for missed meals is given only when a student is away for "
         "seven or more continuous days with approved leave. Refund requests must be made within 15 days of returning.",
         "3. Food quality complaints",
         "Complaints about food quality or hygiene must be reported on the same day through CampusFix with a photo if "
         "possible. The mess committee checks every complaint within 24 hours. Cases of food poisoning are treated as "
         "critical and the medical officer is informed immediately."],
        ["4. Mess committee",
         "The mess committee has four student members elected every semester and meets on the second Friday of each "
         "month. The weekly menu is decided by the committee and displayed on the notice board every Sunday.",
         "5. Conduct in the mess",
         "Food must not be taken out of the mess hall, except for sick students with a note from the warden. Wasting "
         "food repeatedly leads to a fine of Rs. 100."],
    ]),
    "it_and_campus_policy.pdf": ("IT Services and Campus Policy (Sample)", [
        ["1. Wi-Fi and internet",
         "Campus Wi-Fi is available in hostels, the library and academic blocks from 6:00 AM to 12:00 midnight. Each "
         "student may connect up to two devices. Wi-Fi outages should be reported through CampusFix; the IT team aims "
         "to restore service within 4 working hours.",
         "2. Portal accounts",
         "Students log in to the student portal with their register number. Forgotten passwords can be reset at the "
         "IT help desk in the library between 9:00 AM and 5:00 PM with a college ID card.",
         "3. Acceptable use",
         "Downloading pirated content, running servers, or sharing accounts is not allowed. Violations lead to the "
         "Wi-Fi account being blocked for 30 days."],
        ["4. College buses",
         "College buses leave the bus bay at 4:45 PM and 5:45 PM. Students must show their bus pass to the driver. Bus "
         "route changes are announced one week in advance. Rash driving or a breakdown should be reported through "
         "CampusFix or to the transport office immediately.",
         "5. Attendance",
         "Students need at least 75 percent attendance in every course to write the semester exam. Medical leave "
         "certificates must be submitted within three days of returning to class.",
         "6. Lost and found",
         "Lost items are kept at the security office at the main gate for 30 days. Theft must be reported to security "
         "and through CampusFix the same day so CCTV footage can be checked."],
    ]),
}


def write_pdf(path, title, pages):
    with PdfPages(path) as pdf:
        for number, paragraphs in enumerate(pages, start=1):
            fig = plt.figure(figsize=(8.27, 11.69))  # A4
            fig.text(0.08, 0.95, title, fontsize=16, weight="bold")
            y = 0.90
            for paragraph in paragraphs:
                heading = paragraph[0].isdigit()
                for line in textwrap.wrap(paragraph, 88) or [""]:
                    fig.text(0.08, y, line, fontsize=11, weight="bold" if heading else "normal")
                    y -= 0.022
                y -= 0.012
            fig.text(0.5, 0.03, f"Page {number}  -  SAMPLE document for CampusFix", fontsize=8, ha="center")
            pdf.savefig(fig)
            plt.close(fig)


def main():
    folder = Path(__file__).resolve().parent
    for file_name, (title, pages) in DOCUMENTS.items():
        write_pdf(folder / file_name, title, pages)
        print(f"Wrote {folder / file_name}")


if __name__ == "__main__":
    main()
