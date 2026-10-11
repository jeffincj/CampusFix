"""
Spike alerts: Isolation Forest on complaints per hour.

1. Count complaints in every hour of the last N days (empty hours count 0).
2. Each hour becomes a point [count, hour_of_day]. Isolation Forest learns
   what "normal" looks like and marks unusual points (-1).
3. We keep only unusual hours that are also HIGH (at least min_count
   complaints): a quiet hour is unusual too, but not an alert.
"""
from collections import Counter
from datetime import timedelta

import numpy as np
from django.utils import timezone
from sklearn.ensemble import IsolationForest


def hour_start(moment):
    return timezone.localtime(moment).replace(minute=0, second=0, microsecond=0)


def hourly_counts(timestamps, end, days=14):
    """[(hour_start, count), ...] for every hour in the window, oldest first."""
    last = hour_start(end)
    first = last - timedelta(days=days) + timedelta(hours=1)
    counts = Counter(hour_start(t) for t in timestamps if first <= hour_start(t) <= last)
    hours = [first + timedelta(hours=i) for i in range(days * 24)]
    return [(h, counts.get(h, 0)) for h in hours]


def detect_spikes(timestamps, end=None, days=14, min_count=5, contamination=0.01):
    """Return spike hours as dicts: {hour, count, typical, score}."""
    series = hourly_counts(timestamps, end or timezone.now(), days)
    counts = np.array([c for _, c in series], dtype=float)
    if counts.sum() == 0:
        return []
    features = np.array([[c, h.hour] for h, c in series], dtype=float)
    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=42).fit(features)
    flags = model.predict(features)  # -1 = anomaly
    scores = model.decision_function(features)  # lower = more unusual
    typical = float(np.median(counts[counts > 0])) if (counts > 0).any() else 0.0

    spikes = []
    for (hour, count), flag, score in zip(series, flags, scores):
        if flag == -1 and count >= min_count and count > typical:
            spikes.append({"hour": hour, "count": int(count), "typical": typical, "score": round(float(-score), 3)})
    return sorted(spikes, key=lambda s: s["hour"], reverse=True)


def spikes_for(queryset, days=14, min_count=5):
    """Spikes for a complaint queryset, with the top categories in each spike hour."""
    end = timezone.now()
    since = end - timedelta(days=days)
    rows = list(queryset.filter(created_at__gte=since).values_list("created_at", "category"))
    spikes = detect_spikes([t for t, _ in rows], end=end, days=days, min_count=min_count)
    for spike in spikes:
        in_hour = [cat or "unknown" for t, cat in rows if hour_start(t) == spike["hour"]]
        spike["categories"] = [{"category": c, "count": n} for c, n in Counter(in_hour).most_common()]
        spike["hour"] = spike["hour"].isoformat()
    return spikes
