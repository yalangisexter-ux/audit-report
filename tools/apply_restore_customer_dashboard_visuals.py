#!/usr/bin/env python3
from pathlib import Path
import re

app_path = Path("app.py")
text = app_path.read_text(encoding="utf-8")

old_anim_start = "    def animate_tab_transition(self, index):"
if "Customer requirement: keep live wallpaper and button/card drop-shadows" in text:
    print("animate already customer-preserving")
else:
    # Replace from def animate_tab_transition through the dashboard early-return block
    pattern = re.compile(
        r"    def animate_tab_transition\(self, index\):\n"
        r"        page = self\.tabs\.widget\(index\)\n"
        r"        if page is None:\n"
        r"            return\n"
        r".*?"
        r"            return\n"
        r"(?=        if self\._tab_animation:)",
        re.S,
    )
    replacement = '''    def animate_tab_transition(self, index):
        page = self.tabs.widget(index)
        if page is None:
            return
        is_dashboard = index == 1 or page is getattr(self, "dashboard", None)
        # Customer requirement: keep live wallpaper and button/card drop-shadows.
        # On Dashboard only, slow the particle timer (still animated) so Windows does
        # not freeze while the dense page composites over the wallpaper.
        if hasattr(self, "bg_anim") and hasattr(self.bg_anim, "timer"):
            if is_dashboard:
                if not self.bg_anim.timer.isActive():
                    self.bg_anim.timer.start(200)
                else:
                    self.bg_anim.timer.setInterval(200)
            else:
                if not self.bg_anim.timer.isActive():
                    self.bg_anim.timer.start(80)
                else:
                    self.bg_anim.timer.setInterval(80)
        # Skip only the page-level opacity transition on Dashboard (not customer shadows).
        # Full-page QGraphicsOpacityEffect on this dense tab freezes Windows on every open.
        if is_dashboard:
            if self._tab_animation:
                self._tab_animation.stop()
            if self._animated_page:
                try:
                    self._animated_page.setGraphicsEffect(None)
                except Exception:
                    pass
            try:
                page.setGraphicsEffect(None)
            except Exception:
                pass
            return
'''
    new_text, n = pattern.subn(replacement, text, count=1)
    if n != 1:
        raise SystemExit(f"animate_tab_transition replace count={n}")
    text = new_text
    print("patched animate")

# Restore interaction animations for dashboard
if "Customer requirement: keep InteractionFeedback" in text:
    print("interaction already customer-preserving")
else:
    old_fb = '''        dashboard_page = getattr(self, "dashboard", None)
        for widget in targets:
            # Drop-shadow effects on the dense Dashboard page force expensive
            # off-screen compositing on every tab open (Windows freeze).
            if dashboard_page is not None and (
                widget is dashboard_page or dashboard_page.isAncestorOf(widget)
            ):
                if widget.graphicsEffect() is not None:
                    widget.setGraphicsEffect(None)
                if hasattr(widget, "_interaction_feedback"):
                    widget._interaction_feedback = None
                continue
            feedback = getattr(widget, "_interaction_feedback", None)
            if feedback is not None:
                feedback.set_accent(accent)
                continue
            if widget.graphicsEffect() is not None:
                continue
            feedback = InteractionFeedback(widget, accent)
            widget._interaction_feedback = feedback
            widget.setProperty("interactionAnimation", "enabled")
'''
    new_fb = '''        # Customer requirement: keep InteractionFeedback / drop-shadows on Dashboard
        # buttons and cards. Hang mitigation is handled by skipping page-level opacity
        # transitions and throttling wallpaper interval on Dashboard only.
        for widget in targets:
            feedback = getattr(widget, "_interaction_feedback", None)
            if feedback is not None:
                feedback.set_accent(accent)
                continue
            if widget.graphicsEffect() is not None:
                continue
            feedback = InteractionFeedback(widget, accent)
            widget._interaction_feedback = feedback
            widget.setProperty("interactionAnimation", "enabled")
'''
    if old_fb in text:
        text = text.replace(old_fb, new_fb, 1)
        print("patched interaction")
    elif "InteractionFeedback(widget, accent)" in text and "Drop-shadow effects on the dense Dashboard page" not in text:
        print("interaction already ok")
    else:
        raise SystemExit("interaction block not found")

app_path.write_text(text, encoding="utf-8")

# Rewrite the visual-related tests at end of productivity async file
test_path = Path("tests/test_dashboard_productivity_async.py")
t = test_path.read_text(encoding="utf-8")
# Drop prior hang tests that required stripping visuals
for name in [
    "test_dashboard_open_pauses_live_wallpaper_and_strips_page_effects",
    "test_interaction_animations_skip_dashboard_drop_shadows",
    "test_dashboard_keeps_customer_wallpaper_and_drop_shadows",
    "test_dashboard_tab_transition_skips_only_page_opacity",
]:
    t = re.sub(rf"\ndef {name}\(\):.*?(?=\ndef |\Z)", "\n", t, count=1, flags=re.S)

# Soften opacity test
t = t.replace(
    '''def test_dashboard_tab_transition_skips_opacity_effect():
    import inspect
    source = inspect.getsource(app.MainWindow.animate_tab_transition)
    assert "index == 1" in source
    assert "dashboard" in source
    assert "QGraphicsOpacityEffect" in source
    # Dashboard branch must return before creating an opacity effect.
    dash_branch = source.find("index == 1")
    effect_pos = source.find("QGraphicsOpacityEffect")
    assert dash_branch != -1 and effect_pos != -1
    assert dash_branch < effect_pos
''',
    '''def test_dashboard_tab_transition_skips_opacity_effect():
    import inspect
    source = inspect.getsource(app.MainWindow.animate_tab_transition)
    assert "is_dashboard" in source or "index == 1" in source
    assert "dashboard" in source
    assert "QGraphicsOpacityEffect" in source
    # Dashboard branch must return before creating an opacity effect.
    dash_branch = source.find("is_dashboard")
    if dash_branch == -1:
        dash_branch = source.find("index == 1")
    effect_pos = source.find("QGraphicsOpacityEffect")
    assert dash_branch != -1 and effect_pos != -1
    assert dash_branch < effect_pos
''',
)

extra = '''

def test_dashboard_keeps_customer_wallpaper_and_drop_shadows():
    """Customer visuals stay enabled; only page-level opacity transition is skipped."""
    import inspect
    anim = inspect.getsource(app.MainWindow.animate_tab_transition)
    inter = inspect.getsource(app.MainWindow.apply_interaction_animations)
    # Live wallpaper remains running (throttled, not stopped hard-only).
    assert "setInterval(200)" in anim or "timer.start(200)" in anim
    assert "setInterval(80)" in anim or "timer.start(80)" in anim
    # Must not strip child drop-shadows on open.
    assert "child.setGraphicsEffect(None)" not in anim
    # InteractionFeedback must still be applied (not skipped for dashboard).
    assert "InteractionFeedback(widget, accent)" in inter
    assert "Drop-shadow effects on the dense Dashboard page" not in inter
    # Page-level opacity transition still skipped for Dashboard.
    assert "is_dashboard" in anim
    assert "QGraphicsOpacityEffect" in anim
'''
if "test_dashboard_keeps_customer_wallpaper_and_drop_shadows" not in t:
    t = t.rstrip() + "\n" + extra
test_path.write_text(t, encoding="utf-8")
print("tests updated")
print("done")
