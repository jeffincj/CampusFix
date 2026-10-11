"""
Hotspots: DBSCAN clustering on location + category.

Each complaint becomes a point (x, y) on the campus map (see ai/campus.py).
We add the category as a third coordinate multiplied by a big number, so
complaints of different categories are always far apart and never end up
in the same cluster. DBSCAN then finds dense groups: "many HOSTEL
complaints around the A/B block hostels". Isolated complaints are noise.
"""
from collections import Counter
from datetime import timedelta

import numpy as np
from django.utils import timezone
from sklearn.cluster import DBSCAN

from ai.campus import locate

CATEGORY_GAP = 10_000  # metres; far bigger than the campus, keeps categories apart


def complaint_points(complaints):
    """Turn complaints into points. Complaints with an unknown location are skipped."""
    points = []
    for c in complaints:
        found = locate(c.location, c.block, c.description)
        if found:
            place, block, x, y = found
            points.append({"id": c.id, "category": c.category or "unknown", "place": place, "block": block,
                           "x": x, "y": y, "status": c.status, "created_at": c.created_at})
    return points


def find_hotspots(points, eps=70, min_samples=4):
    """
    Cluster points with DBSCAN.
    eps: max distance in metres between neighbours; min_samples: points needed to form a cluster.
    Returns clusters sorted by size (biggest first).
    """
    if len(points) < min_samples:
        return []
    categories = sorted({p["category"] for p in points})
    features = np.array([[p["x"], p["y"], categories.index(p["category"]) * CATEGORY_GAP] for p in points])
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(features)

    clusters = []
    for label in sorted(set(labels) - {-1}):  # -1 means noise
        members = [p for p, lab in zip(points, labels) if lab == label]
        places = Counter(p["place"] for p in members)
        clusters.append({
            "category": members[0]["category"],
            "count": len(members),
            "open_count": sum(p["status"] in ("open", "in_progress") for p in members),
            "places": [{"place": name, "count": n} for name, n in places.most_common()],
            "blocks": sorted({p["block"] for p in members}),
            "center": {"x": round(float(np.mean([p["x"] for p in members])), 1),
                       "y": round(float(np.mean([p["y"] for p in members])), 1)},
            "complaint_ids": [p["id"] for p in members],
            "latest": max(p["created_at"] for p in members),
        })
    return sorted(clusters, key=lambda c: -c["count"])


def hotspots_for(queryset, days=30, eps=70, min_samples=4):
    """Hotspots among complaints created in the last `days` days."""
    since = timezone.now() - timedelta(days=days)
    return find_hotspots(complaint_points(queryset.filter(created_at__gte=since)), eps=eps, min_samples=min_samples)
