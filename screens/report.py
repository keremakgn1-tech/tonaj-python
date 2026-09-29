"""
TONAJ - Rapor ekrani (Task 18 refactor: main.py'den ayrildi).

Toplam tonaj, PR sayisi ve kas grubu bazli haftalik hacim gibi ozet
istatistikleri gosterir. Davranis main.py'deki halinden HICBIR sekilde
degismedi - bu SAF bir tasima (bkz. shared.py basindaki Task 18 notu).
"""
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

import core
from shared import MUTED, ACCENT, DANGER, weight_unit, to_display_weight, Card, label, mono_label, WeeklyBarChart


class ReportScreen(Screen):
    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        state = app.state
        self.clear_widgets()
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))

        if not state["history"]:
            col.add_widget(label("Henüz veri yok.", color=MUTED, height=dp(40)))
            scroll.add_widget(col); self.add_widget(scroll); return

        cur_key = core.period_key(core.now_ms(), "week")
        tonnage = sum(core.session_tonnage(s) for s in state["history"] if core.period_key(s["startedAt"], "week") == cur_key)
        count = sum(1 for s in state["history"] if core.period_key(s["startedAt"], "week") == cur_key)
        prs = [p for p in core.compute_all_prs(state) if core.period_key(p["date"], "week") == cur_key]

        stats = Card(size_hint_y=None, height=dp(84), orientation="horizontal", spacing=dp(4))
        def stat_cell(value, unit_label):
            cell = BoxLayout(orientation="vertical")
            cell.add_widget(mono_label(value, size=22, color=ACCENT, bold=True, halign="center", height=dp(32)))
            cell.add_widget(label(unit_label, size=14, color=MUTED, halign="center", height=dp(18)))
            return cell
        stats.add_widget(stat_cell(f"{to_display_weight(tonnage):g}", f"{weight_unit()} bu hafta"))
        stats.add_widget(stat_cell(str(count), "antrenman"))
        stats.add_widget(stat_cell(str(len(prs)), "yeni rekor"))
        col.add_widget(stats)

        # KOK NEDEN (UX incelemesi): bu ekran ONCEDEN SADECE mevcut haftanin
        # sayilarini gosteriyordu - kullanici "geceyim mi ilerliyor muyum"
        # sorusuna hicbir zaman cevap bulamiyordu, her ziyarette ayni "su an"
        # anlik goruntusunu goruyordu. Asagidaki basit cubuk grafik son 8
        # haftalik tonaj trendini (bkz. core.weekly_tonnage_trend) gosterir -
        # calisilmayan haftalar da (0 olarak, ince bir cizgiyle) goruluyor ki
        # "bos gecen" bir hafta grafikten sessizce kaybolmasin.
        from datetime import datetime as _dt
        trend = core.weekly_tonnage_trend(state, weeks=8)
        col.add_widget(label("SON 8 HAFTA - TONAJ TRENDİ", size=14, color=MUTED, bold=True, height=dp(26)))
        chart_card = Card()
        points = []
        for i, p in enumerate(trend):
            wk_dt = _dt.fromtimestamp(p["weekStart"] / 1000)
            points.append({
                "label": wk_dt.strftime("%d.%m"),
                "value": to_display_weight(p["tonnage"]),
                "highlight": i == len(trend) - 1,
            })
        chart_card.add_widget(WeeklyBarChart(points, value_fmt=lambda v: f"{v:g}"))
        col.add_widget(chart_card)

        vol = core.muscle_group_volume(state, "week", cur_key)
        if vol:
            col.add_widget(label("KAS GRUBU BAZLI HAFTALIK HACİM", size=14, color=MUTED, bold=True, height=dp(26)))
            for g, c in vol:
                bar = Card(size_hint_y=None, height=dp(32), orientation="horizontal")
                bar.add_widget(label(g, size=14, height=dp(20)))
                bar.add_widget(mono_label(f"{c} set", size=14, color=DANGER if c < 10 else ACCENT, halign="right", height=dp(20)))
                col.add_widget(bar)

        scroll.add_widget(col)
        self.add_widget(scroll)
