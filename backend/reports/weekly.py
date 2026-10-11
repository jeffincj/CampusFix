"""
Weekly PDF report (Matplotlib, 3 A4 pages):
 1. Summary numbers vs the previous week, hotspots, spike alerts, urgent open complaints
 2. Charts: complaints per category, new complaints per day (last 14 days)
 3. Charts: complaints per block, average days to resolve per category
"""
import io
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta

import matplotlib.pyplot as plt
from django.utils import timezone
from matplotlib.backends.backend_pdf import PdfPages

from ai.ml.hotspots import hotspots_for
from ai.ml.spikes import spikes_for
from complaints.models import Complaint, DuplicateLink

from . import charts

A4 = (8.27, 11.69)
CATEGORY_NAMES = dict(Complaint.Category.choices)


def day_start(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def week_numbers(queryset, start, end):
    """Summary numbers for complaints created in [start, end)."""
    created = queryset.filter(created_at__gte=start, created_at__lt=end)
    resolved = queryset.filter(resolved_at__gte=start, resolved_at__lt=end)
    durations = [(c.resolved_at - c.created_at).total_seconds() / 86400 for c in resolved.only("created_at", "resolved_at")]
    return {
        "new": created.count(),
        "resolved": resolved.count(),
        "avg_days": round(sum(durations) / len(durations), 1) if durations else None,
        "critical": created.filter(urgency="critical").count(),
        "duplicates": DuplicateLink.objects.filter(duplicate__in=created).count(),
    }


def collect(queryset, end_day):
    """All numbers the report needs, for the 7 days ending on end_day (inclusive)."""
    end = day_start(end_day + timedelta(days=1))
    start = end - timedelta(days=7)
    previous_start = start - timedelta(days=7)
    this_week = queryset.filter(created_at__gte=start, created_at__lt=end)

    # Complaints per day for the last 14 days
    per_day = Counter(timezone.localtime(t).date() for t in
                      queryset.filter(created_at__gte=previous_start, created_at__lt=end).values_list("created_at", flat=True))
    days = [(previous_start + timedelta(days=i)).date() for i in range(14)]

    # Average days to resolve per category (complaints resolved this week)
    durations = defaultdict(list)
    for c in queryset.filter(resolved_at__gte=start, resolved_at__lt=end).only("category", "created_at", "resolved_at"):
        durations[c.category].append((c.resolved_at - c.created_at).total_seconds() / 86400)

    return {
        "start": start, "end": end,
        "this": week_numbers(queryset, start, end),
        "previous": week_numbers(queryset, previous_start, start),
        "open_now": queryset.filter(status__in=["open", "in_progress"]).count(),
        "needs_review": queryset.filter(needs_review=True, status__in=["open", "in_progress"]).count(),
        "by_category": Counter(CATEGORY_NAMES.get(c, "Unknown") for c in this_week.values_list("category", flat=True)),
        "by_block": Counter(b or "Unknown" for b in this_week.values_list("block", flat=True)),
        "days": days, "per_day": [per_day.get(d, 0) for d in days],
        "resolve_days": {CATEGORY_NAMES.get(k, k): round(sum(v) / len(v), 1) for k, v in durations.items()},
        "hotspots": hotspots_for(queryset, days=7)[:5],
        "spikes": spikes_for(queryset, days=7)[:5],
        "urgent_open": list(queryset.filter(status__in=["open", "in_progress"], urgency__in=["critical", "high"])
                            .order_by("created_at")[:10]),
    }


def english_line(complaint):
    """
    One English line for a complaint. Matplotlib cannot shape Tamil/Malayalam letters,
    so non-Latin titles are replaced by the AI summary or "category at location".
    """
    if complaint.summary:
        text = complaint.summary
    elif complaint.title.isascii():
        text = complaint.title
    else:
        text = f"{CATEGORY_NAMES.get(complaint.category, 'Campus')} problem at {complaint.location or complaint.block or 'campus'}"
    text = text if text.isascii() else text.encode("ascii", "ignore").decode()
    return text if len(text) <= 70 else text[:67] + "..."


def change_text(now, before):
    if before in (None, 0) or now is None:
        return ""
    change = (now - before) / before * 100
    return f"  ({'+' if change >= 0 else ''}{change:.0f}% vs last week)"


def summary_page(pdf, data, title):
    fig = plt.figure(figsize=A4)
    period = f"{timezone.localtime(data['start']):%d %b %Y} – {timezone.localtime(data['end'] - timedelta(seconds=1)):%d %b %Y}"
    fig.text(0.07, 0.95, title, fontsize=18, weight="bold", color=charts.INK)
    fig.text(0.07, 0.925, f"Weekly report · {period} · generated {timezone.localtime():%d %b %Y %H:%M}", color=charts.INK_2)

    this, prev = data["this"], data["previous"]
    rows = [
        ("New complaints", this["new"], change_text(this["new"], prev["new"])),
        ("Resolved this week", this["resolved"], change_text(this["resolved"], prev["resolved"])),
        ("Average days to resolve", this["avg_days"] if this["avg_days"] is not None else "—",
         change_text(this["avg_days"], prev["avg_days"])),
        ("New critical complaints", this["critical"], ""),
        ("Duplicates merged", this["duplicates"], ""),
        ("Open right now", data["open_now"], ""),
        ("Open and needing review (AI disagreement)", data["needs_review"], ""),
    ]
    y = 0.87
    fig.text(0.07, y, "Summary", fontsize=12, weight="bold"); y -= 0.03
    for label, value, change in rows:
        fig.text(0.09, y, label, color=charts.INK_2)
        fig.text(0.62, y, f"{value}", weight="bold", ha="right")
        fig.text(0.63, y, change, color=charts.MUTED)
        y -= 0.024

    y -= 0.02
    fig.text(0.07, y, "Hotspots (last 7 days)", fontsize=12, weight="bold"); y -= 0.03
    if not data["hotspots"]:
        fig.text(0.09, y, "No hotspots.", color=charts.MUTED); y -= 0.024
    for h in data["hotspots"]:
        places = ", ".join(p["place"] for p in h["places"][:3])
        fig.text(0.09, y, f"{CATEGORY_NAMES.get(h['category'], h['category'])}: {h['count']} complaints ({h['open_count']} open) at {places}")
        y -= 0.024

    y -= 0.02
    fig.text(0.07, y, "Spike alerts (last 7 days)", fontsize=12, weight="bold"); y -= 0.03
    if not data["spikes"]:
        fig.text(0.09, y, "No spikes.", color=charts.MUTED); y -= 0.024
    for s in data["spikes"]:
        hour = datetime.fromisoformat(s["hour"])
        top = ", ".join(f"{CATEGORY_NAMES.get(c['category'], c['category'])} {c['count']}" for c in s["categories"][:3])
        fig.text(0.09, y, f"{hour:%a %d %b, %H:00}: {s['count']} complaints in one hour ({top})")
        y -= 0.024

    y -= 0.02
    fig.text(0.07, y, "Oldest open critical / high complaints", fontsize=12, weight="bold"); y -= 0.03
    if not data["urgent_open"]:
        fig.text(0.09, y, "None.", color=charts.MUTED)
    for c in data["urgent_open"]:
        age = (timezone.now() - c.created_at).days
        fig.text(0.09, y, f"#{c.id}  [{c.urgency}]  {CATEGORY_NAMES.get(c.category, '?')} · {c.block or '-'} · {age} days old")
        fig.text(0.11, y - 0.017, english_line(c), color=charts.INK_2, fontsize=8)
        y -= 0.04

    fig.text(0.5, 0.03, "CampusFix · page 1", ha="center", color=charts.MUTED, fontsize=8)
    pdf.savefig(fig)
    plt.close(fig)


def charts_page(pdf, data, page_number, panels):
    fig, axes = plt.subplots(len(panels), 1, figsize=A4)
    fig.subplots_adjust(left=0.27, right=0.93, top=0.94, bottom=0.08, hspace=0.45)
    for ax, draw in zip(axes, panels):
        draw(ax)
    fig.text(0.5, 0.03, f"CampusFix · page {page_number}", ha="center", color=charts.MUTED, fontsize=8)
    pdf.savefig(fig)
    plt.close(fig)


def build_weekly_pdf(queryset=None, end_day=None, title="CampusFix"):
    """Return the weekly report as PDF bytes."""
    queryset = queryset if queryset is not None else Complaint.objects.all()
    end_day = end_day or timezone.localdate()
    data = collect(queryset, end_day)
    week_start = 7  # index of the first day of this week in the 14-day series
    day_labels = [d.strftime("%a %d") for d in data["days"]]

    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        summary_page(pdf, data, title)
        charts_page(pdf, data, 2, [
            lambda ax: charts.horizontal_bars(ax, list(data["by_category"]), list(data["by_category"].values()),
                                              "New complaints per category (this week)"),
            lambda ax: charts.daily_line(ax, day_labels, data["per_day"], week_start, "New complaints per day (last 14 days)"),
        ])
        charts_page(pdf, data, 3, [
            lambda ax: charts.horizontal_bars(ax, list(data["by_block"]), list(data["by_block"].values()),
                                              "New complaints per block (this week)"),
            lambda ax: charts.horizontal_bars(ax, list(data["resolve_days"]), list(data["resolve_days"].values()),
                                              "Average days to resolve, per category (resolved this week)",
                                              empty_text="Nothing was resolved this week."),
        ])
        info = pdf.infodict()
        info["Title"] = f"{title} weekly report"
        info["Author"] = "CampusFix"
    return buffer.getvalue()
