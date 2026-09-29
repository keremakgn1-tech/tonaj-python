"""
TONAJ - Gecmis ekrani (Task 18 refactor: main.py'den ayrildi).

Tamamlanmis antrenman oturumlarinin listesini, PR'lari ve hareket bazli
karsilastirmalari gosterir. Davranis main.py'deki halinden HICBIR
sekilde degismedi - bu SAF bir tasima (bkz. shared.py basindaki
Task 18 notu).
"""
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.clock import Clock

import core
from shared import (
    DIVIDER, TEXT, MUTED, FAINT, ACCENT, DANGER, STEEL,
    weight_unit, to_display_weight, fmt_weight,
    confirm_dialog, Card, label, sp_, mono_label, target_label, _find_scrollview,
)


class HistoryScreen(Screen):
    def on_pre_enter(self):
        self.render()

    def render(self, keep_scroll=False):
        app = App.get_running_app()
        state = app.state
        prev = _find_scrollview(self)
        prev_scroll_y = prev.scroll_y if (keep_scroll and prev is not None) else None
        self.clear_widgets()
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))

        if not state["history"]:
            col.add_widget(label("Henüz antrenman kaydın yok.", color=MUTED, height=dp(40)))

        for s in state["history"]:
            col.add_widget(self.session_card(state, s))

        scroll.add_widget(col)
        self.add_widget(scroll)

        if prev_scroll_y is not None:
            def restore(*_):
                scroll.scroll_y = prev_scroll_y
            Clock.schedule_once(restore, 0)

    def confirm_delete_session(self, session_id):
        app = App.get_running_app()

        def on_confirm():
            core.remove_history_session(app.state, session_id)
            app.save()
            self.render(keep_scroll=True)

        confirm_dialog(
            "Antrenmanı Sil",
            "Bu antrenman kaydını kalıcı olarak silmek istediğine emin misin? Bu işlem geri alınamaz.",
            on_confirm)

    def session_card(self, state, s):
        from datetime import datetime
        card = Card(size_hint_y=None, spacing=dp(4))
        card.bind(minimum_height=card.setter("height"))
        dt = datetime.fromtimestamp(s["startedAt"] / 1000)
        tonnage = core.session_tonnage(s)
        head = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        title_col = BoxLayout(orientation="vertical")
        title_col.add_widget(label(dt.strftime("%d.%m.%Y"), size=15, bold=True, height=dp(18)))
        if s.get("dayName"):
            title_col.add_widget(label(s["dayName"], size=14, color=MUTED, height=dp(18)))
        head.add_widget(title_col)
        head.add_widget(mono_label(fmt_weight(tonnage), size=15, color=ACCENT, bold=True, halign="right"))
        del_btn = Button(text="×", size_hint=(None, None), size=(dp(32), dp(32)),
                          background_color=(0, 0, 0, 0), color=MUTED, font_size=sp_(18))
        del_btn.bind(on_release=lambda *_, sid=s["id"]: self.confirm_delete_session(sid))
        head.add_widget(del_btn)
        card.add_widget(head)

        # Once set girilmis hareketler, sonra "SET GIRILMEDI" olanlar - boylece
        # goz once tamamlanani tarar, bos olanlar listenin sonuna cekilir.
        def sort_key(ex):
            done = any(not st.get("isWarmup") for st in ex["sets"])
            return (0 if done else 1)
        sorted_exercises = sorted(s["exercises"], key=sort_key)

        for i, ex in enumerate(sorted_exercises):
            cmp = core.history_exercise_compare(ex)
            is_empty = cmp["delta"][0] == "none"
            row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(48), spacing=dp(3),
                             padding=(0, dp(6), 0, dp(6)))
            if i > 0:
                with row.canvas.before:
                    Color(*DIVIDER)
                    rline = Line(points=[0, row.top, row.width, row.top], width=dp(1))
                row.bind(pos=lambda w, *_, ln=rline: setattr(ln, 'points', [w.x, w.top, w.right, w.top]),
                         size=lambda w, *_, ln=rline: setattr(ln, 'points', [w.x, w.top, w.right, w.top]))
            name_color = FAINT if is_empty else TEXT
            top = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(6))
            top.add_widget(label(ex["name"], size=14, color=name_color, bold=not is_empty))
            actual = "  ".join(f"{to_display_weight(st['weight']):g}×{st['reps']}" for st in ex["sets"]) or "—"
            top.add_widget(mono_label(actual, size=14, color=(FAINT if is_empty else TEXT), halign="right"))
            row.add_widget(top)
            if cmp["hasTarget"]:
                dtxt = cmp["delta"][1] or ""
                if cmp.get("weightDiffKg") is not None and not dtxt:
                    # Agirlik-bazli fark: core.py kg olarak hesapladi, burada
                    # kullanicinin sectigi birimde metni biz kuruyoruz.
                    d = to_display_weight(cmp["weightDiffKg"])
                    arrow = "▲ +" if d > 0 else "▼ "
                    dtxt = f"{arrow}{d:g} {weight_unit().upper()}"
                color = {"up": ACCENT, "down": DANGER, "eq": STEEL, "none": FAINT}.get(cmp["delta"][0], FAINT)
                # core.history_exercise_compare() hedeflenen set SAYISINA gore
                # de bir bilgi (setsBadge) hesapliyordu ama hicbir yerde
                # gosterilmiyordu - hedeften eksik kalinan setleri burada
                # (kirmizi uyariyla) yuzeye cikariyoruz.
                sets_badge = cmp.get("setsBadge")
                if sets_badge and sets_badge[2] == "under":
                    incomplete_txt = f"{sets_badge[0]}/{sets_badge[1]} SET"
                    dtxt = f"{incomplete_txt} · {dtxt}" if dtxt else incomplete_txt
                    color = DANGER
                sub_row = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(6))
                sub_row.add_widget(mono_label("hedef " + target_label(ex), size=13, color=FAINT))
                if dtxt:
                    sub_row.add_widget(mono_label(dtxt, size=13, color=color, halign="right", bold=True))
                row.add_widget(sub_row)
            card.add_widget(row)
        return card
