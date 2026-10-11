"""
Matplotlib chart helpers for the weekly PDF report.
One consistent look: one blue for single-series charts, thin bars, value at the
bar tip, light solid gridlines, no top/right borders, text in grey/black (never
in the data colour).
"""
import matplotlib

matplotlib.use("Agg")  # draw to files, no screen needed (servers have no display)
import matplotlib.pyplot as plt  # noqa: E402

BLUE = "#2a78d6"  # series colour
ORANGE = "#eb6834"  # second series (comparison)
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
WEEK_SHADE = "#cde2fb"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "xtick.color": MUTED,
    "ytick.color": INK_2,
    "pdf.fonttype": 42,  # real fonts in the PDF, so text can be copied
})


def style_axes(ax, grid_axis="x"):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def horizontal_bars(ax, labels, values, title, empty_text="No complaints in this period."):
    """Count per label, biggest on top, value written at the end of each bar."""
    ax.set_title(title)
    style_axes(ax, "x")
    if not values:
        ax.text(0.5, 0.5, empty_text, ha="center", va="center", color=MUTED, transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        return
    pairs = sorted(zip(labels, values), key=lambda p: p[1])
    names, counts = [p[0] for p in pairs], [p[1] for p in pairs]
    bars = ax.barh(names, counts, color=BLUE, height=0.55)
    ax.bar_label(bars, padding=3, color=INK_2, fontsize=8)
    ax.set_xlim(0, max(counts) * 1.15 + 0.5)
    ax.xaxis.get_major_locator().set_params(integer=True)


def daily_line(ax, days, counts, week_start_index, title):
    """New complaints per day; the current week is shaded."""
    ax.set_title(title)
    style_axes(ax, "y")
    x = range(len(days))
    ax.axvspan(week_start_index - 0.5, len(days) - 0.5, color=WEEK_SHADE, alpha=0.35, linewidth=0)
    ax.plot(x, counts, color=BLUE, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels(days, rotation=45, ha="right", fontsize=7)
    ax.set_ylim(0, max(counts + [1]) * 1.25)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.text(week_start_index - 0.4, ax.get_ylim()[1] * 0.92, "this week", color=INK_2, fontsize=8)
    if counts:
        ax.annotate(str(counts[-1]), (len(counts) - 1, counts[-1]), textcoords="offset points", xytext=(0, 7),
                    ha="center", color=INK_2, fontsize=8)
