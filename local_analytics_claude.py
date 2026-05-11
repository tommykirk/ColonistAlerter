from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider, Button
from matplotlib.gridspec import GridSpec

# ── Constants ────────────────────────────────────────────────────────────────

RESOURCE_MAP = {
    'wheat': 'G',
    'brick': 'B',
    'wood':  'L',
    'ore':   'O',
    'sheep': 'W',
    'desert':'D',
}

# Expected probability of each dice value (out of 36 combinations)
EXPECTED_FREQ = {
    2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6,
    8: 5, 9: 4, 10: 3, 11: 2, 12: 1
}

DICE_VALUES = list(range(2, 13))

COLOR_NORMAL   = '#5B8DB8'
COLOR_BLOCKED  = '#CC4444'
COLOR_EXPECTED = '#AAAAAA'

# ── Parsing ──────────────────────────────────────────────────────────────────

def parse_roll(line):
    """Extract dice sum from a 'rolled' line. Returns int or None."""
    numbers = [int(p.split('_')[1]) for p in line.split() if 'dice_' in p]
    return sum(numbers) if len(numbers) == 2 else None

def parse_blocked(line):
    """Extract dice value from a 'blocked by the Robber' line. Returns int or None."""
    for part in line.split():
        if part.startswith('prob_'):
            try:
                return int(part.split('_')[1])
            except ValueError:
                return None
    return None

def parse_log(filepath='catan_log.txt'):
    events = []
    last_roll_idx = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if 'rolled' in line:
                dice = parse_roll(line)
                if dice:
                    events.append({'dice': dice, 'blocked': False})
                    last_roll_idx = len(events) - 1
            elif 'blocked by the Robber' in line:
                if last_roll_idx is not None:
                    events[last_roll_idx]['blocked'] = True
    return events

# ── Aggregation ──────────────────────────────────────────────────────────────

def compute_counts(events, up_to):
    """
    Count rolls per dice value up to roll index `up_to` (1-based).
    Returns:
      counts        {2..12: int}   total times each value was rolled
      blocked_counts {2..12: int}  how many of those were under the robber
    """
    counts         = {v: 0 for v in DICE_VALUES}
    blocked_counts = {v: 0 for v in DICE_VALUES}

    for event in events[:up_to]:
        d = event['dice']
        counts[d] += 1
        if event['blocked']:
            blocked_counts[d] += 1

    return counts, blocked_counts

# ── Plotting ─────────────────────────────────────────────────────────────────

def build_chart(events):
    total_rolls = len(events)
    if total_rolls == 0:
        print("No roll events found in log.")
        return

    fig = plt.figure(figsize=(12, 6))
    fig.patch.set_facecolor('#1E1E2E')

    gs = GridSpec(2, 1, height_ratios=[10, 1], hspace=0.4)
    ax     = fig.add_subplot(gs[0])
    ax_sl  = fig.add_subplot(gs[1])

    ax.set_facecolor('#2A2A3E')
    for spine in ax.spines.values():
        spine.set_edgecolor('#444466')

    # Initial state: all rolls
    counts, blocked_counts = compute_counts(events, total_rolls)
    x = DICE_VALUES
    normal_vals  = [counts[v] - blocked_counts[v] for v in x]
    blocked_vals = [blocked_counts[v] for v in x]
    expected_vals = [EXPECTED_FREQ[v] / 36 * total_rolls for v in x]

    bars_normal  = ax.bar(x, normal_vals, color=COLOR_NORMAL,  label='Rolled',  zorder=3)
    bars_blocked = ax.bar(x, blocked_vals, bottom=normal_vals,
                          color=COLOR_BLOCKED, label='Rolled (robber)', zorder=3)
    line_expected, = ax.plot(x, expected_vals, color=COLOR_EXPECTED,
                             linestyle='--', linewidth=1.5,
                             marker='o', markersize=4, label='Expected', zorder=4)

    ax.set_xticks(x)
    ax.set_xlabel('Dice Value', color='white')
    ax.set_ylabel('Times Rolled', color='white')
    ax.tick_params(colors='white')
    ax.yaxis.get_major_locator().set_params(integer=True)

    title = ax.set_title(f'Catan Roll Distribution — rolls 1 to {total_rolls}', color='white')

    legend = ax.legend(
        handles=[
            mpatches.Patch(color=COLOR_NORMAL,  label='Rolled'),
            mpatches.Patch(color=COLOR_BLOCKED, label='Rolled (robber active)'),
            mpatches.Patch(color=COLOR_EXPECTED, label='Expected'),
        ],
        facecolor='#2A2A3E', labelcolor='white', framealpha=0.7
    )

    # Slider
    ax_sl.set_facecolor('#1E1E2E')
    slider = Slider(
        ax=ax_sl,
        label='Up to roll',
        valmin=1,
        valmax=total_rolls,
        valinit=total_rolls,
        valstep=1,
        color='#5B8DB8',
    )
    slider.label.set_color('white')
    slider.valtext.set_color('white')

    # Prev / Next buttons
    btn_prev = Button(ax_prev, '◀  Prev', color='#2A2A3E', hovercolor='#3A3A5E')
    btn_next = Button(ax_next, 'Next  ▶', color='#2A2A3E', hovercolor='#3A3A5E')
    btn_prev.label.set_color('white')
    btn_next.label.set_color('white')
    ax_end.set_visible(False)  # just used as a centre spacer

    def update(val):
        n = int(slider.val)
        counts, blocked_counts = compute_counts(events, n)
        normal_vals  = [counts[v] - blocked_counts[v] for v in DICE_VALUES]
        blocked_vals = [blocked_counts[v] for v in DICE_VALUES]
        expected_vals = [EXPECTED_FREQ[v] / 36 * n for v in DICE_VALUES]

        for bar, h in zip(bars_normal, normal_vals):
            bar.set_height(h)
        for bar, h, b in zip(bars_blocked, blocked_vals, normal_vals):
            bar.set_height(h)
            bar.set_y(b)

        line_expected.set_ydata(expected_vals)

        max_y = max(max(counts.values(), default=1), max(expected_vals)) * 1.15
        ax.set_ylim(0, max(max_y, 1))

        title.set_text(f'Catan Roll Distribution — rolls 1 to {n}')
        fig.canvas.draw_idle()

    def step(delta):
        new_val = int(max(1, min(total_rolls, slider.val + delta)))
        slider.set_val(new_val)

    btn_prev.on_clicked(lambda _: step(-1))
    btn_next.on_clicked(lambda _: step(+1))

    def on_key(event):
        if event.key == 'right':
            step(+1)
        elif event.key == 'left':
            step(-1)

    fig.canvas.mpl_connect('key_press_event', on_key)

    slider.on_changed(update)
    update(total_rolls)

    plt.show()

# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    events = parse_log('catan_log.txt')
    print(f"Loaded {len(events)} rolls.")
    build_chart(events)