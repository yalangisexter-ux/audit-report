#!/usr/bin/env python3
"""Apply every-open Dashboard hang fix without changing business logic."""
from pathlib import Path

app_path = Path("app.py")
text = app_path.read_text(encoding="utf-8")

old_anim = '''    def animate_tab_transition(self, index):
        page = self.tabs.widget(index)
        if page is None:
            return
        # Dashboard has large tables/charts; opacity effects freeze the UI on Windows.
        # Match by index and by widget identity so future tab reordering cannot reintroduce the hang.
        if index == 1 or page is getattr(self, "dashboard", None):
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

new_anim = '''    def animate_tab_transition(self, index):
        page = self.tabs.widget(index)
        if page is None:
            return
        is_dashboard = index == 1 or page is getattr(self, "dashboard", None)
        # Live wallpaper paint under a dense translucent Dashboard page freezes Windows
        # on every open. Pause particles while Dashboard is visible; resume elsewhere.
        if hasattr(self, "bg_anim") and hasattr(self.bg_anim, "timer"):
            if is_dashboard:
                self.bg_anim.timer.stop()
            elif not self.bg_anim.timer.isActive():
                self.bg_anim.timer.start(80)
        # Dashboard has large tables/charts; opacity effects freeze the UI on Windows.
        # Match by index and by widget identity so future tab reordering cannot reintroduce the hang.
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
            # Strip residual opacity/shadow effects that force offscreen rasterization
            # of the whole page when the tab becomes visible.
            try:
                for child in page.findChildren(QWidget):
                    effect = child.graphicsEffect()
                    if effect is not None and isinstance(effect, (QGraphicsOpacityEffect, QGraphicsDropShadowEffect)):
                        # Keep interaction feedback available via stylesheet only on this page.
                        child.setGraphicsEffect(None)
                        if hasattr(child, "_interaction_feedback"):
                            child._interaction_feedback = None
            except Exception:
                pass
            return
'''

if "bg_anim.timer.stop()" in text and "is_dashboard" in text and "findChildren(QWidget)" in text:
    print("animate already patched")
elif old_anim in text:
    text = text.replace(old_anim, new_anim, 1)
    print("patched animate")
else:
    raise SystemExit("animate_tab_transition block not found")

old_fb = '''        for widget in targets:
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

new_fb = '''        dashboard_page = getattr(self, "dashboard", None)
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

if "Drop-shadow effects on the dense Dashboard page" in text:
    print("interaction already patched")
elif old_fb in text:
    text = text.replace(old_fb, new_fb, 1)
    print("patched interaction")
else:
    raise SystemExit("interaction animation loop not found")

app_path.write_text(text, encoding="utf-8")

test_path = Path("tests/test_dashboard_productivity_async.py")
test_text = test_path.read_text(encoding="utf-8")
extra = '''

def test_dashboard_open_pauses_live_wallpaper_and_strips_page_effects():
    import inspect
    source = inspect.getsource(app.MainWindow.animate_tab_transition)
    assert "bg_anim.timer.stop()" in source
    assert "QGraphicsDropShadowEffect" in source
    assert "isAncestorOf" in source or "findChildren" in source
    assert "is_dashboard" in source


def test_interaction_animations_skip_dashboard_drop_shadows():
    import inspect
    source = inspect.getsource(app.MainWindow.apply_interaction_animations)
    assert "dashboard" in source
    assert "isAncestorOf" in source
    assert "Drop-shadow effects on the dense Dashboard page" in source or "off-screen compositing" in source
'''
if "test_dashboard_open_pauses_live_wallpaper_and_strips_page_effects" not in test_text:
    test_path.write_text(test_text.rstrip() + "\n" + extra, encoding="utf-8")
    print("tests updated")
else:
    print("tests already present")
print("done")
