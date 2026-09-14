import numpy as np

from scry.config import BlinkParams, ChurnParams, DetectParams
from scry.detect import BlinkTracker, ChurnTracker, Component, change_map, components, is_bar, trigger


def glyph(img, x, y, w=6, h=10, v=255):
    img[y:y + h, x:x + w] = v


def test_thin_strokes_survive_and_noise_does_not():
    p = DetectParams()
    prev = np.zeros((60, 160), np.uint8)
    cur = prev.copy()
    # a 1-px-wide 'l' glyph: 1x10 = 10 changed px, would vanish under a 3x3 opening
    cur[20:30, 40:41] = 255
    comps = components(change_map(prev, cur, p.theta_pix), p.theta_min)
    assert len(comps) == 1 and comps[0].area == 10 and comps[0].bbox == (40, 20, 41, 30)
    # scattered codec noise: 6 isolated pixels
    noisy = prev.copy()
    for x in (5, 30, 55, 80, 105, 130):
        noisy[10, x] = 40
    assert components(change_map(prev, noisy, p.theta_pix), p.theta_min) == []


def test_dilation_merges_glyph_strokes_into_one_component():
    p = DetectParams()
    prev = np.zeros((60, 160), np.uint8)
    cur = prev.copy()
    cur[20:30, 40:41] = 255  # left stem
    cur[20:21, 41:46] = 255  # top bar (touching)
    cur[20:30, 47:48] = 255  # a second stem 1 px away from the bar: dilation bridges the gap
    comps = components(change_map(prev, cur, p.theta_pix), p.theta_min)
    assert len(comps) == 1


def test_bar_caret_is_excluded_by_shape_but_glyph_triggers():
    p = DetectParams()
    prev = np.zeros((60, 160), np.uint8)
    caret = prev.copy()
    caret[20:38, 50:52] = 255  # 2x18 bar caret
    comps = components(change_map(prev, caret, p.theta_pix), p.theta_min)
    assert len(comps) == 1 and is_bar(comps[0], p)
    assert not trigger([c for c in comps if not is_bar(c, p)], p)
    g = prev.copy()
    glyph(g, 50, 20)  # 6x10 = 60 px lowercase-sized glyph
    comps = components(change_map(prev, g, p.theta_pix), p.theta_min)
    assert trigger(comps, p)


def test_churn_activates_on_sustained_change_and_deactivates_after_it_stops():
    fps = 30
    cp = ChurnParams(window_s=1.0, rho_on=0.5, rho_off=0.2, min_area=100)
    tr = ChurnTracker((60, 160), fps, cp)
    rng = np.random.default_rng(0)
    deactivated_at = None
    for i in range(150):
        changed = np.zeros((60, 160), bool)
        if i < 90:  # a 20x20 region flickers every frame for 3 s
            changed[10:30, 100:120] = rng.random((20, 20)) > 0.3
        upd = tr.update(changed, i, i / fps)
        if i == 60:
            assert upd.regions and tr.active
            x0, y0, x1, y1 = upd.regions[0]
            assert x0 <= 100 and y0 <= 10 and x1 >= 120 and y1 >= 30
            assert tr.excludes(Component(50, (105, 15, 110, 20)))
            assert not tr.excludes(Component(50, (5, 5, 10, 10)))
        if upd.deactivated and deactivated_at is None:
            deactivated_at = i
            assert upd.t_last_change is not None and abs(upd.t_last_change - 89 / fps) < 0.05
    assert deactivated_at is not None and 90 < deactivated_at < 130
    assert not tr.active


def test_churn_does_not_activate_on_a_single_large_change_at_startup():
    tr = ChurnTracker((60, 160), 30, ChurnParams(window_s=1.0, min_area=100))
    changed = np.zeros((60, 160), bool)
    changed[:, :] = True
    upd = tr.update(changed, 0, 0.0)
    assert upd.regions == []


def test_blink_tracker_confirms_periodic_component_and_expires():
    bp = BlinkParams()
    bt = BlinkTracker(bp)
    box = (50, 20, 58, 32)  # 8x12 block cursor
    confirmed_at = None
    for i in range(120):
        t = i / 30
        comps = [Component(96, box)] if i % 15 == 0 else []  # toggles every 0.5 s
        upd = bt.update(comps, t)
        if comps and upd.excluded and confirmed_at is None:
            confirmed_at = t
    assert confirmed_at == 1.0  # third toggle: 2 recurrences after the first
    assert bt.is_blinker_bbox((51, 21, 58, 32))
    assert bt.caret_for_interval(0.9, 1.6) == box
    for i in range(120, 220):  # no more toggles: expires after 2 s
        bt.update([], i / 30)
    assert not bt.is_blinker_bbox(box)


def test_blink_tracker_ignores_large_components():
    bt = BlinkTracker(BlinkParams())
    for i in range(0, 90, 15):
        upd = bt.update([Component(500, (0, 0, 40, 40))], i / 30)
        assert upd.excluded == set()


def test_reduce_2x2_keeps_single_pixel_strokes():
    from scry.detect import reduce_2x2

    m = np.zeros((6, 9), bool)
    m[1, 3] = True
    r = reduce_2x2(m)
    assert r.shape == (3, 4) and r[0, 1] and r.sum() == 1
