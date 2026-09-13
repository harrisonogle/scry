import numpy as np

from vt.config import Stage1Config
from vt.settle import SettleMachine

FPS = 30
H, W = 60, 200


def run(frames, cfg=None, duration=None):
    cfg = cfg or Stage1Config()
    m = SettleMachine(cfg, FPS, (H, W))
    out = []
    for i, g in enumerate(frames):
        out += m.step(i, i / FPS, g)
    out += m.finish(duration if duration is not None else len(frames) / FPS)
    return out


def blank():
    return np.zeros((H, W), np.uint8)


def with_glyphs(n, base=None, x0=10, y=20):
    g = blank() if base is None else base.copy()
    for k in range(n):
        g[y:y + 10, x0 + 8 * k:x0 + 8 * k + 6] = 255
    return g


def test_static_video_emits_only_first_frame():
    frames = [blank() for _ in range(90)]
    ems = run(frames)
    assert len(ems) == 1
    assert ems[0].settled and ems[0].t_change == 0.0 and ems[0].t_end == 3.0


def test_single_change_settles_with_first_still_frame_time():
    frames = [blank() for _ in range(30)] + [with_glyphs(1) for _ in range(60)]
    ems = run(frames)
    assert len(ems) == 2
    e = ems[1]
    assert e.frame_index >= 30 + 12
    assert e.t_change == 30 / FPS
    assert e.t_settled == 30 / FPS  # frame 31 is still relative to 30, so the state was on screen at t(30)
    assert e.settled
    assert ems[0].t_end == e.t_change


def test_flash_that_reverts_within_S_emits_nothing():
    frames = [blank() for _ in range(30)] + [with_glyphs(2) for _ in range(6)] + [blank() for _ in range(60)]
    assert len(run(frames)) == 1


def test_bar_caret_blink_does_not_emit_and_is_recorded_as_caret():
    frames = []
    for i in range(150):
        g = blank()
        if (i // 15) % 2 == 1:
            g[20:38, 100:102] = 255
        frames.append(g)
    ems = run(frames)
    assert len(ems) == 1
    assert ems[0].caret is not None and abs(ems[0].caret[0] - 100) <= 1


def test_block_cursor_blink_is_learned_and_does_not_prevent_settling():
    frames = [blank() for _ in range(15)]
    for i in range(15, 240):
        g = with_glyphs(1)
        if (i // 15) % 2 == 1:
            g[20:32, 20:28] = 255  # 8x12 block cursor right of the glyph
        frames.append(g)
    ems = run(frames)
    assert len(ems) == 2
    e = ems[1]
    assert e.settled
    assert abs(e.t_settled - 15 / FPS) < 0.05  # corrected back to the real motion, not the blinks
    assert not any(not x.settled for x in ems)


def test_typing_without_pauses_is_one_state_and_with_a_pause_is_two():
    fast = [blank() for _ in range(30)]
    for k in range(1, 6):
        fast += [with_glyphs(k) for _ in range(8)]  # 0.27 s per keystroke < S
    fast += [with_glyphs(5) for _ in range(60)]
    ems = run(fast)
    assert len(ems) == 2 and ems[1].t_change == 30 / FPS and ems[1].t_settled == (30 + 8 * 4) / FPS

    slow = [blank() for _ in range(30)] + [with_glyphs(1) for _ in range(30)] + [with_glyphs(2) for _ in range(60)]
    ems = run(slow)
    assert len(ems) == 3


def test_max_hold_during_continuous_motion_then_settle():
    frames = [blank() for _ in range(30)]
    for i in range(150):  # a 20x20 block jumping 5 px per frame for 5 s (1 px/frame leaves bar-shaped edges, design §7.7)
        g = blank()
        x = 10 + (i * 5) % 140
        g[30:50, x:x + 20] = 255
        frames.append(g)
    frames += [frames[-1] for _ in range(60)]
    ems = run(frames)
    unsettled = [e for e in ems if not e.settled]
    settled = [e for e in ems if e.settled]
    assert len(unsettled) == 1 and abs(unsettled[0].t_change - 30 / FPS) < 1e-6 and abs(unsettled[0].t_settled - (30 + 90) / FPS) < 1e-6
    assert settled[-1].t_settled == (30 + 149) / FPS


def test_max_hold_frame_that_is_the_end_state_is_upgraded():
    frames = [blank() for _ in range(30)]
    for i in range(91):  # motion for M plus one frame, so the max-hold fires on the last moving frame
        g = blank()
        x = 10 + (i * 5) % 140
        g[30:50, x:x + 20] = 255
        frames.append(g)
    frames += [frames[-1] for _ in range(60)]  # identical to the max-hold frame
    ems = run(frames)
    assert len(ems) == 2
    assert ems[1].settled and ems[1].t_settled == (30 + 90) / FPS


def test_end_of_stream_flushes_pending_change():
    frames = [blank() for _ in range(30)] + [with_glyphs(3) for _ in range(5)]
    ems = run(frames)
    assert len(ems) == 2 and ems[1].settled and ems[1].t_end == 35 / FPS


def test_scrolling_region_yields_ticks_and_a_final_settled_state():
    cfg = Stage1Config()
    cfg.churn.window_s = 1.0
    cfg.churn.min_area = 100
    rng = np.random.default_rng(1)
    frames = [blank() for _ in range(30)]
    for i in range(300):  # 10 s of a 30x40 region changing every frame
        g = blank()
        g[10:40, 120:160] = (rng.random((30, 40)) * 255).astype(np.uint8)
        frames.append(g)
    frames += [frames[-1] for _ in range(180)]
    ems = run(frames, cfg)
    ticks = [e for e in ems if not e.settled]
    assert len(ticks) >= 2
    final = ems[-1]
    assert final.settled and abs(final.t_settled - (30 + 299) / FPS) < 0.1
