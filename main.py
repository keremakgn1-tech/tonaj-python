"""
TONAJ - Antrenman Takibi (Kivy / Android)
main.py, arayuzu (View) core.py'deki (Model/Logic) fonksiyonlara baglar.
"""
import os
from kivy.core.text import LabelBase
_FONT_DIR = os.path.dirname(os.path.abspath(__file__))
def _f(name): return os.path.join(_FONT_DIR, name)
# Orijinal web uygulamasinin tipografi kimligi: Oswald (baslik/wordmark),
# Inter (govde metni), Space Mono (rakam/veri). Ucu de Turkce karakterleri
# (ğ ş ı İ ö ü ç) tam destekliyor - kaydetmeden once dogrulandi.
# 'Roboto' Kivy'nin TUM widget'larinin varsayilan font adi oldugu icin, onu
# Inter'e cevirmek butun uygulamayi tek satirla Inter'e gecirir.
LabelBase.register(name="Roboto", fn_regular=_f("Inter-Regular.ttf"), fn_bold=_f("Inter-SemiBold.ttf"))
LabelBase.register(name="Oswald", fn_regular=_f("Oswald-Bold.ttf"), fn_bold=_f("Oswald-Bold.ttf"))
LabelBase.register(name="SpaceMono", fn_regular=_f("SpaceMono-Regular.ttf"), fn_bold=_f("SpaceMono-Bold.ttf"))

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.properties import ObjectProperty

import core

# ---------------------------------------------------------------------------
# Renk paleti (mevcut web uygulamasiyla ayni: koyu + limon yesili vurgu)
# ---------------------------------------------------------------------------
BG = (0x12/255, 0x13/255, 0x16/255, 1)
CARD = (0x1B/255, 0x1D/255, 0x21/255, 1)
CARD2 = (0x23/255, 0x25/255, 0x29/255, 1)
RAISED = (0x2A/255, 0x2D/255, 0x32/255, 1)
BORDER = (0x2E/255, 0x31/255, 0x38/255, 1)
TEXT = (0xF5/255, 0xF5/255, 0xF0/255, 1)
MUTED = (0x8B/255, 0x8D/255, 0x93/255, 1)
FAINT = (0x5C/255, 0x5F/255, 0x66/255, 1)
ACCENT = (0xE8/255, 0xFF/255, 0x3D/255, 1)
ACCENT_DARK = (0x0C/255, 0x1A/255, 0x02/255, 1)
DANGER = (0xFF/255, 0x5A/255, 0x5A/255, 1)
STEEL = (0x5B/255, 0x7F/255, 0xB5/255, 1)


def get_data_path():
    try:
        app = App.get_running_app()
        base = app.user_data_dir if app else "."
    except Exception:
        base = "."
    return os.path.join(base, "tonaj_state.json")


def bg_rect(widget, color):
    with widget.canvas.before:
        Color(*color)
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(10)])
    def upd(*_):
        rect.pos = widget.pos
        rect.size = widget.size
    widget.bind(pos=upd, size=upd)
    return rect


class Card(BoxLayout):
    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        super().__init__(**kw)
        bg_rect(self, CARD)
        self.padding = dp(12)
        self.spacing = dp(6)


def styled_button(text, color=ACCENT, text_color=(0.07, 0.08, 0.06, 1), **kw):
    kw.setdefault("font_name", "Oswald")
    kw.setdefault("font_size", sp_(14))
    btn = Button(text=tr_upper(text), background_normal="", background_color=color,
                 color=text_color, size_hint_y=None, height=dp(46), **kw)
    return btn


def label(text, size=15, color=TEXT, bold=False, halign="left", **kw):
    lb = Label(text=text, font_size=sp_(size), color=color, bold=bold,
               halign=halign, valign="middle", size_hint_y=None, **kw)
    lb.bind(size=lambda *_: setattr(lb, "text_size", lb.size))
    lb.bind(texture_size=lambda *_: setattr(lb, "height", max(lb.texture_size[1], dp(20))))
    return lb


def sp_(v):
    from kivy.metrics import sp
    return sp(v)


def dark_ti(**kw):
    """Kivy'nin varsayilan (acik renkli) TextInput'unu koyu temaya uydurur."""
    kw.setdefault("background_color", RAISED)
    kw.setdefault("foreground_color", TEXT)
    kw.setdefault("hint_text_color", FAINT)
    kw.setdefault("cursor_color", ACCENT)
    kw.setdefault("padding", [dp(10), dp(10), dp(10), dp(10)])
    if "size_hint_y" not in kw and "height" not in kw:
        kw["size_hint_y"] = None
        kw["height"] = dp(40)
    return TextInput(**kw)


def mono_label(text, size=11, color=MUTED, halign="left", **kw):
    width = kw.pop("width", None)
    if width is not None:
        kw["size_hint_x"] = None
        kw["width"] = width
    lb = Label(text=text, font_name="SpaceMono", font_size=sp_(size), color=color,
               halign=halign, valign="middle", size_hint_y=None, **kw)
    lb.bind(size=lambda *_: setattr(lb, "text_size", lb.size))
    if "height" not in kw:
        lb.height = dp(20)
    return lb


class ClickableRow(ButtonBehavior, BoxLayout):
    pass


import re
_DAY_NAME_RE = re.compile(r'^\s*(\d+)\s*\.\s*G[üu]n\s*:\s*(.+?)\s*(?:\(([^)]*)\))?\s*$', re.IGNORECASE)
def parse_day_name(name):
    """'1. Gün: İtiş (Göğüs-Omuz-Triceps)' -> ('01', 'İtiş', 'Göğüs-Omuz-Triceps').
    Bu kaliba uymayan (kullanicinin kendi yeniden adlandirdigi) isimler icin
    ordinal/meta bos doner, headline oldugu gibi kullanilir."""
    m = _DAY_NAME_RE.match(name)
    if m:
        ordinal = m.group(1).zfill(2)
        headline = m.group(2).strip()
        meta = m.group(3).strip() if m.group(3) else None
        return ordinal, headline, meta
    return None, name, None


def tr_upper(s):
    """Python'un str.upper()'ı Turkce'ye ozgu degil: 'i' -> 'I' (noktasiz) yapar,
    oysa Turkce'de 'i' harfinin buyugu noktali 'İ'dir. Once bu iki harfi elle
    cevirip sonra genel upper() uyguluyoruz."""
    return s.replace("i", "İ").replace("ı", "I").upper()


def toast(app, msg):
    app.root_widget.show_toast(msg)


# ---------------------------------------------------------------------------
# Yardimci: hedef metni
# ---------------------------------------------------------------------------
def target_label(ex):
    parts = []
    rmin, rmax = ex.get("targetRepsMin"), ex.get("targetRepsMax")
    reps = f"{rmin}-{rmax}" if rmin and rmax and rmin != rmax else (rmin or rmax)
    sets = ex.get("targetSets")
    if sets and reps:
        parts.append(f"{sets}×{reps}")
    elif sets:
        parts.append(f"{sets} set")
    elif reps:
        parts.append(f"{reps} tekrar")
    if ex.get("targetWeight"):
        parts.append(f"{ex['targetWeight']}kg")
    if ex.get("targetRIR") is not None:
        parts.append(f"RIR {ex['targetRIR']}")
    return " · ".join(parts)


SUGGEST_TEXT = {
    "ceiling": "geçen sefer tüm setlerde tavana ulaştın, ağırlık artırma zamanı",
    "ceiling-bw": "geçen sefer hedefi tuttun, bu sefer tekrar sayısını artırmayı dene",
    "below": "aynı ağırlık — geçen sefer bazı setler hedefin altında kaldı",
    "inrange": "aynı ağırlık — bu sefer aralığın tavanına ulaşmaya çalış",
}


# ---------------------------------------------------------------------------
# PROGRAM EKRANI
# ---------------------------------------------------------------------------
class ProgramScreen(Screen):
    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        state = app.state
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")

        if state["activeSession"]:
            root.add_widget(self.render_active_session(state))
        else:
            root.add_widget(self.render_planner(state))
        self.add_widget(root)

    # ---- Planlayici (gun listesi) ----
    def render_planner(self, state):
        app = App.get_running_app()
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))

        if not state["program"]["days"]:
            col.add_widget(label("Program tanımlı değil. Aşağıdan gün ekle.", color=MUTED, height=dp(60)))

        next_id = core.next_suggested_day_id(state)
        for day in state["program"]["days"]:
            col.add_widget(self.day_card(state, day, is_next=(day["id"] == next_id)))

        add_btn = styled_button("+ GÜN EKLE", color=RAISED, text_color=TEXT)
        add_btn.bind(on_release=lambda *_: (core.add_program_day(state), app.save(), self.render()))
        col.add_widget(add_btn)

        free_btn = styled_button("Serbest Antrenman Başlat", color=RAISED, text_color=TEXT)
        free_btn.bind(on_release=lambda *_: self.start_session(None))
        col.add_widget(free_btn)

        scroll.add_widget(col)
        return scroll

    def day_card(self, state, day, is_next):
        app = App.get_running_app()
        card = Card(size_hint_y=None, spacing=dp(4))
        card.bind(minimum_height=card.setter("height"))
        # Sol kenarda ince vurgu seridi (SIRADA gunlerde limon, digerlerinde sessiz)
        stripe_color = ACCENT if is_next else BORDER
        with card.canvas.after:
            Color(*stripe_color)
            stripe = Rectangle(pos=card.pos, size=(dp(3), card.height))
        def _upd_stripe(*_):
            stripe.pos = card.pos
            stripe.size = (dp(3), card.height)
        card.bind(pos=_upd_stripe, size=_upd_stripe)

        ordinal, headline, meta = parse_day_name(day["name"])

        eyebrow = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(8))
        if ordinal:
            eyebrow.add_widget(mono_label(ordinal, size=11, color=FAINT, width=dp(20)))
        if is_next:
            sirada = Label(text="SIRADA", font_name="Oswald", font_size=sp_(11), bold=True,
                            color=ACCENT_DARK, size_hint=(None, None), size=(dp(72), dp(20)))
            bg_rect(sirada, ACCENT)
            eyebrow.add_widget(sirada)
        eyebrow.add_widget(BoxLayout())  # sag tarafi dolduran bosluk
        up = Button(text="↑", size_hint=(None, None), size=(dp(26), dp(26)), background_color=(0,0,0,0), color=FAINT)
        down = Button(text="↓", size_hint=(None, None), size=(dp(26), dp(26)), background_color=(0,0,0,0), color=FAINT)
        dup = Button(text="Kopya", size_hint=(None, None), size=(dp(48), dp(26)), background_color=(0,0,0,0), color=FAINT, font_size=sp_(10))
        delete = Button(text="✕", size_hint=(None, None), size=(dp(26), dp(26)), background_color=(0,0,0,0), color=DANGER)
        up.bind(on_release=lambda *_: (core.move_program_day(state, day["id"], -1), app.save(), self.render()))
        down.bind(on_release=lambda *_: (core.move_program_day(state, day["id"], 1), app.save(), self.render()))
        dup.bind(on_release=lambda *_: (core.duplicate_program_day(state, day["id"]), app.save(), self.render()))
        delete.bind(on_release=lambda *_: self.confirm_delete_day(day["id"]))
        for w in (up, down, dup, delete):
            eyebrow.add_widget(w)
        card.add_widget(eyebrow)

        head_lbl = Label(text=tr_upper(headline), font_name="Oswald", font_size=sp_(24), color=TEXT,
                          halign="left", valign="middle", shorten=True, shorten_from="right",
                          size_hint_y=None, height=dp(30))
        head_lbl.bind(size=lambda *_: setattr(head_lbl, "text_size", head_lbl.size))
        card.add_widget(head_lbl)
        if meta:
            card.add_widget(label(meta + f" · {len(day['exercises'])} hareket", size=12, color=FAINT, height=dp(20)))

        for i, ex in enumerate(day["exercises"]):
            row = ClickableRow(size_hint_y=None, height=dp(36), spacing=dp(6))
            row.bind(on_release=lambda *_, d=day, e=ex: self.open_target_editor(d, e["name"]))
            with row.canvas.before:
                Color(*BORDER)
                rline = Line(points=[0, row.top, row.width, row.top], width=1)
            row.bind(pos=lambda w, *_: setattr(rline, 'points', [w.x, w.top, w.right, w.top]),
                     size=lambda w, *_: setattr(rline, 'points', [w.x, w.top, w.right, w.top]))
            row.add_widget(label(ex["name"], size=13.5))
            tgt = target_label(ex) or "hedef yok"
            tgt_lbl = mono_label(tgt, size=11, color=MUTED)
            row.add_widget(tgt_lbl)
            rm = Button(text="✕", size_hint=(None, None), size=(dp(24), dp(24)), background_color=(0,0,0,0), color=FAINT)
            rm.bind(on_release=lambda *_, d=day, idx=i: (core.remove_exercise_from_day(state, d["id"], idx), app.save(), self.render()))
            row.add_widget(rm)
            card.add_widget(row)

        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(16), padding=(0, dp(10), 0, 0))
        add_ex = Button(text="+ Hareket", background_color=(0,0,0,0), color=MUTED, font_size=sp_(13), size_hint_x=None, width=dp(90))
        add_ex.bind(on_release=lambda *_: self.open_exercise_picker(day["id"]))
        deload = Button(text="Deload", background_color=(0,0,0,0), color=MUTED, font_size=sp_(13), size_hint_x=None, width=dp(70))
        deload.bind(on_release=lambda *_: self.start_session(day["id"], is_deload=True))
        actions.add_widget(add_ex)
        actions.add_widget(deload)
        actions.add_widget(BoxLayout())
        start = Button(text="BAŞLA", font_name="Oswald", font_size=sp_(15), background_color=ACCENT,
                        color=ACCENT_DARK, size_hint_x=None, width=dp(110))
        start.bind(on_release=lambda *_: self.start_session(day["id"]))
        actions.add_widget(start)
        card.add_widget(actions)
        return card

    def confirm_delete_day(self, day_id):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(label("Bu günü silmek istediğine emin misin?"))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title="Günü Sil", content=content, size_hint=(0.85, 0.35))
        yes = styled_button("Evet, Sil", color=DANGER, text_color=(1, 1, 1, 1))
        no = styled_button("Vazgeç", color=RAISED, text_color=TEXT)
        yes.bind(on_release=lambda *_: (core.delete_program_day(app.state, day_id), app.save(), popup.dismiss(), self.render()))
        no.bind(on_release=popup.dismiss)
        row.add_widget(no); row.add_widget(yes)
        content.add_widget(row)
        popup.open()

    def open_exercise_picker(self, day_id):
        app = App.get_running_app()
        names = core.all_exercise_names(app.state)
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        col.bind(minimum_height=col.setter("height"))
        popup = Popup(title="Hareket Seç", size_hint=(0.9, 0.8))
        for n in names:
            b = Button(text=n, size_hint_y=None, height=dp(38), background_color=RAISED, color=TEXT)
            b.bind(on_release=lambda *_, name=n: (popup.dismiss(), self.open_target_editor({"id": day_id}, name)))
            col.add_widget(b)
        scroll.add_widget(col)
        content.add_widget(scroll)
        newrow = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        ti = dark_ti(hint_text="Yeni hareket adı", multiline=False)
        addb = styled_button("Ekle")
        def add_new(*_):
            val = ti.text.strip()
            if val:
                if val not in app.state["library"]:
                    app.state["library"].append(val)
                popup.dismiss()
                self.open_target_editor({"id": day_id}, val)
        addb.bind(on_release=add_new)
        newrow.add_widget(ti); newrow.add_widget(addb)
        content.add_widget(newrow)
        popup.content = content
        popup.open()

    def open_target_editor(self, day, name):
        app = App.get_running_app()
        state = app.state
        day_obj = next((d for d in state["program"]["days"] if d["id"] == day["id"]), None)
        existing = next((e for e in day_obj["exercises"] if e["name"] == name), {}) if day_obj else {}

        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        content.add_widget(label(name, size=17, bold=True, height=dp(28)))

        def field(hint, val):
            ti = dark_ti(hint_text=hint, text=str(val) if val not in (None, "") else "",
                            multiline=False, input_filter="float", size_hint_y=None, height=dp(40))
            return ti

        sets_i = field("Set", existing.get("targetSets"))
        rmin_i = field("Tekrar min", existing.get("targetRepsMin"))
        rmax_i = field("Tekrar max", existing.get("targetRepsMax"))
        w_i = field("Ağırlık (kg)", existing.get("targetWeight"))
        rir_i = field("RIR", existing.get("targetRIR"))
        rest_i = field("Dinlenme (sn)", existing.get("restSeconds"))
        for w in (sets_i, rmin_i, rmax_i, w_i, rir_i, rest_i):
            content.add_widget(w)

        popup = Popup(title="Hedef", content=content, size_hint=(0.9, 0.85))
        save_btn = styled_button("Kaydet")

        def to_num(text, cast=int):
            text = text.strip()
            if not text:
                return None
            try:
                return cast(float(text)) if cast is int else float(text)
            except ValueError:
                return None

        def do_save(*_):
            core.set_day_exercise_target(
                state, day["id"], name,
                target_sets=to_num(sets_i.text), target_reps_min=to_num(rmin_i.text),
                target_reps_max=to_num(rmax_i.text), target_weight=to_num(w_i.text, float),
                target_rir=to_num(rir_i.text), rest_seconds=to_num(rest_i.text),
            )
            app.save()
            popup.dismiss()
            self.render()

        save_btn.bind(on_release=do_save)
        content.add_widget(save_btn)
        popup.open()

    # ---- Aktif antrenman ----
    def start_session(self, day_id, is_deload=False):
        app = App.get_running_app()
        core.start_session(app.state, day_id, is_deload)
        app.save()
        self.render()

    def render_active_session(self, state):
        app = App.get_running_app()
        sess = state["activeSession"]
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))

        header = Card(size_hint_y=None, height=dp(92), spacing=dp(2))
        title_row = BoxLayout(size_hint_y=None, height=dp(22))
        title_row.add_widget(label(sess["dayName"] or "Serbest Antrenman", size=13, bold=True, color=MUTED))
        if sess["isDeload"]:
            deload_tag = Label(text="DELOAD", font_name="Oswald", font_size=sp_(10), bold=True,
                                color=ACCENT_DARK, size_hint=(None, None), size=(dp(62), dp(18)))
            bg_rect(deload_tag, ACCENT)
            title_row.add_widget(deload_tag)
        header.add_widget(title_row)
        tonnage = core.session_tonnage(sess)
        tonnage_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        tonnage_row.add_widget(mono_label(f"{tonnage:g}", size=32, color=ACCENT, bold=True, height=dp(44)))
        tonnage_row.add_widget(label("kg", size=13, color=FAINT, height=dp(44)))
        header.add_widget(tonnage_row)
        col.add_widget(header)

        note_btn = styled_button(("Not: " + sess["note"][:40]) if sess["note"] else "+ Antrenman notu ekle",
                                  color=RAISED, text_color=TEXT)
        note_btn.bind(on_release=lambda *_: self.open_note_editor())
        col.add_widget(note_btn)

        for i, ex in enumerate(sess["exercises"]):
            col.add_widget(self.exercise_card(state, sess, ex, i))

        add_ex = styled_button("+ HAREKET EKLE", color=RAISED, text_color=TEXT)
        add_ex.bind(on_release=lambda *_: self.add_adhoc_exercise())
        col.add_widget(add_ex)

        finish = styled_button("Antrenmanı Bitir ve Kaydet")
        finish.bind(on_release=lambda *_: (core.finish_session(state), app.save(), toast(app, "ANTRENMAN KAYDEDİLDİ"), self.render()))
        col.add_widget(finish)

        discard = styled_button("Antrenmanı Sil", color=(0.2, 0.1, 0.1, 1), text_color=DANGER)
        discard.bind(on_release=lambda *_: (core.discard_session(state), app.save(), self.render()))
        col.add_widget(discard)

        scroll.add_widget(col)
        return scroll

    def open_note_editor(self):
        app = App.get_running_app()
        sess = app.state["activeSession"]
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        ti = dark_ti(text=sess["note"], multiline=True, size_hint_y=1, height=None)
        content.add_widget(ti)
        popup = Popup(title="Antrenman Notu", content=content, size_hint=(0.9, 0.6))
        save = styled_button("Kaydet", size_hint_y=None, height=dp(44))
        def do_save(*_):
            sess["note"] = ti.text.strip()
            app.save(); popup.dismiss(); self.render()
        save.bind(on_release=do_save)
        content.add_widget(save)
        popup.open()

    def add_adhoc_exercise(self):
        app = App.get_running_app()
        names = core.all_exercise_names(app.state)
        content = BoxLayout(orientation="vertical", padding=dp(10))
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        col.bind(minimum_height=col.setter("height"))
        popup = Popup(title="Hareket Ekle", content=content, size_hint=(0.9, 0.8))
        for n in names:
            b = Button(text=n, size_hint_y=None, height=dp(38), background_color=RAISED, color=TEXT)
            def pick(*_, name=n):
                core.add_exercise_to_session(app.state, name)
                app.save(); popup.dismiss(); self.render()
            b.bind(on_release=pick)
            col.add_widget(b)
        scroll.add_widget(col)
        content.add_widget(scroll)
        popup.open()

    def exercise_card(self, state, sess, ex, idx):
        app = App.get_running_app()
        card = Card(size_hint_y=None, spacing=dp(4))
        card.bind(minimum_height=card.setter("height"))

        working = [s for s in ex["sets"] if not s.get("isWarmup")]
        prev_max = core.max_weight_for(state, ex["name"])
        head = BoxLayout(size_hint_y=None, height=dp(26))
        head.add_widget(label(ex["name"], size=16, bold=True))
        rm_ex = Button(text="✕", size_hint=(None, None), size=(dp(26), dp(26)), background_color=(0, 0, 0, 0), color=FAINT)
        rm_ex.bind(on_release=lambda *_: (sess["exercises"].pop(idx), app.save(), self.render()))
        head.add_widget(rm_ex)
        card.add_widget(head)
        meta = f"{len(working)} SET" + (f" · ÖNCEKİ REKOR {prev_max:g}KG" if prev_max else "")
        card.add_widget(mono_label(meta, size=10.5, color=FAINT, height=dp(18)))

        tgt = target_label(ex)
        if tgt:
            tgt_row = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
            tgt_row.add_widget(label("HEDEF", size=10.5, bold=True, color=ACCENT, size_hint_x=None, width=dp(48)))
            tgt_row.add_widget(mono_label(tgt, size=11.5, color=TEXT))
            card.add_widget(tgt_row)
        if ex.get("suggestedWeight") is not None:
            txt = f"{ex['suggestedWeight']:g}kg — {SUGGEST_TEXT.get(ex.get('suggestReason'), '')}"
            sug_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
            sug_row.add_widget(label("ÖNERİ", size=10.5, bold=True, color=STEEL, size_hint_x=None, width=dp(48)))
            sug_row.add_widget(label(txt, size=11, color=STEEL))
            card.add_widget(sug_row)

        for si, s in enumerate(ex["sets"]):
            row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
            flag = "ISI" if s.get("isWarmup") else str(si + 1)
            row.add_widget(mono_label(f"{flag}", size=11, color=FAINT, width=dp(24)))
            row.add_widget(mono_label(f"{s['weight']:g}kg × {s['reps']}", size=13,
                                       color=FAINT if s.get("isWarmup") else TEXT))
            badge = core.rir_badge_info(s, ex)
            if badge:
                badge_color = {"easy": ACCENT, "hard": DANGER, "ontarget": STEEL, "neutral": MUTED}[badge["kind"]]
                row.add_widget(mono_label(badge["text"], size=10, color=badge_color, halign="right"))
            rm = Button(text="✕", size_hint=(None, None), size=(dp(24), dp(24)), background_color=(0, 0, 0, 0), color=FAINT)
            rm.bind(on_release=lambda *_, i=idx, j=si: (core.remove_set(state, i, j), app.save(), self.render()))
            row.add_widget(rm)
            card.add_widget(row)

        form = GridLayout(cols=3, size_hint_y=None, height=dp(44), spacing=dp(6))
        w_input = dark_ti(hint_text=f"{ex.get('suggestedWeight') or ex.get('targetWeight') or 'kg'}",
                             multiline=False, input_filter="float", font_name="SpaceMono")
        r_input = dark_ti(hint_text="tekrar", multiline=False, input_filter="int", font_name="SpaceMono")
        add_btn = Button(text="+", background_color=ACCENT, color=(0.07, 0.08, 0.06, 1), bold=True)
        form.add_widget(w_input); form.add_widget(r_input); form.add_widget(add_btn)
        card.add_widget(form)

        extra = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        rir_input = dark_ti(hint_text="RIR", multiline=False, input_filter="int", size_hint_x=0.25, font_name="SpaceMono")
        warm_toggle = ToggleButton(text="Isınma Seti", size_hint_x=0.5, background_color=RAISED, color=TEXT)
        extra.add_widget(rir_input)
        extra.add_widget(warm_toggle)
        card.add_widget(extra)

        def submit(*_):
            try:
                w = float(w_input.text) if w_input.text.strip() else None
                r = int(r_input.text) if r_input.text.strip() else None
            except ValueError:
                w = r = None
            if not w or not r:
                toast(app, "Geçerli değer gir")
                return
            rir = int(rir_input.text) if rir_input.text.strip().isdigit() else None
            is_pr = core.add_set(state, idx, w, r, is_warmup=warm_toggle.state == "down", rir=rir)
            app.save()
            if is_pr:
                toast(app, "YENİ REKOR — PR!")
            self.render()

        add_btn.bind(on_release=submit)
        return card


# ---------------------------------------------------------------------------
# GECMIS EKRANI
# ---------------------------------------------------------------------------
class HistoryScreen(Screen):
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
            col.add_widget(label("Henüz antrenman kaydın yok.", color=MUTED, height=dp(40)))

        for s in state["history"]:
            col.add_widget(self.session_card(state, s))

        scroll.add_widget(col)
        self.add_widget(scroll)

    def session_card(self, state, s):
        from datetime import datetime
        card = Card(size_hint_y=None, spacing=dp(4))
        card.bind(minimum_height=card.setter("height"))
        dt = datetime.fromtimestamp(s["startedAt"] / 1000)
        tonnage = core.session_tonnage(s)
        head = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        title_col = BoxLayout(orientation="vertical")
        title_col.add_widget(label(dt.strftime("%d.%m.%Y"), size=15, bold=True, height=dp(18)))
        if s.get("dayName"):
            title_col.add_widget(label(s["dayName"], size=10.5, color=FAINT, height=dp(14)))
        head.add_widget(title_col)
        head.add_widget(mono_label(f"{tonnage:g}kg", size=15, color=ACCENT, bold=True, halign="right"))
        card.add_widget(head)

        for ex in s["exercises"]:
            cmp = core.history_exercise_compare(ex)
            row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(46), spacing=dp(2))
            top = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(6))
            top.add_widget(label(ex["name"], size=13))
            actual = "  ".join(f"{st['weight']:g}×{st['reps']}" for st in ex["sets"]) or "—"
            top.add_widget(mono_label(actual, size=11, color=MUTED, halign="right"))
            row.add_widget(top)
            if cmp["hasTarget"]:
                dtxt = cmp["delta"][1] or ""
                color = {"up": ACCENT, "down": DANGER, "eq": STEEL, "none": FAINT}.get(cmp["delta"][0], FAINT)
                sub_row = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(6))
                sub_row.add_widget(mono_label("hedef " + target_label(ex), size=10, color=FAINT))
                sub_row.add_widget(mono_label(dtxt, size=10, color=color, halign="right"))
                row.add_widget(sub_row)
            card.add_widget(row)
        return card


# ---------------------------------------------------------------------------
# HAREKETLER EKRANI
# ---------------------------------------------------------------------------
class LibraryScreen(Screen):
    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        state = app.state
        self.clear_widgets()
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))

        names = set()
        for s in state["history"]:
            for e in s["exercises"]:
                names.add(e["name"])

        for n in sorted(names):
            pts = core.history_for_exercise(state, n)
            pr = max((p["max"] for p in pts), default=0)
            row = Card(size_hint_y=None, height=dp(58), orientation="horizontal", spacing=dp(8))
            info = BoxLayout(orientation="vertical")
            info.add_widget(label(n, size=14, bold=True, height=dp(20)))
            info.add_widget(mono_label(f"{len(pts)} antrenman", size=10, color=FAINT, height=dp(16)))
            row.add_widget(info)
            pr_col = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(70))
            pr_col.add_widget(mono_label(f"{pr:g}kg", size=15, color=ACCENT, bold=True, halign="right", height=dp(22)))
            pr_col.add_widget(label("PR", size=9.5, color=FAINT, halign="right", height=dp(14)))
            row.add_widget(pr_col)
            col.add_widget(row)

        if not names:
            col.add_widget(label("Henüz hiç antrenman kaydın yok.", color=MUTED, height=dp(40)))

        scroll.add_widget(col)
        self.add_widget(scroll)


# ---------------------------------------------------------------------------
# RAPOR EKRANI
# ---------------------------------------------------------------------------
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
            cell.add_widget(label(unit_label, size=10, color=FAINT, halign="center", height=dp(16)))
            return cell
        stats.add_widget(stat_cell(f"{tonnage:g}", "kg bu hafta"))
        stats.add_widget(stat_cell(str(count), "antrenman"))
        stats.add_widget(stat_cell(str(len(prs)), "yeni rekor"))
        col.add_widget(stats)

        vol = core.muscle_group_volume(state, "week", cur_key)
        if vol:
            col.add_widget(label("KAS GRUBU BAZLI HAFTALIK HACİM", size=11.5, color=MUTED, bold=True, height=dp(24)))
            for g, c in vol:
                bar = Card(size_hint_y=None, height=dp(32), orientation="horizontal")
                bar.add_widget(label(g, size=12, height=dp(20)))
                bar.add_widget(mono_label(f"{c} set", size=12, color=DANGER if c < 10 else ACCENT, halign="right", height=dp(20)))
                col.add_widget(bar)

        scroll.add_widget(col)
        self.add_widget(scroll)


# ---------------------------------------------------------------------------
# AYARLAR EKRANI
# ---------------------------------------------------------------------------
class SettingsScreen(Screen):
    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        self.clear_widgets()
        col = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        col.add_widget(label("Verilerin bu cihazda kalıcı olarak saklanıyor.", color=MUTED, height=dp(40)))
        export_btn = styled_button("Yedeği Dışa Aktar")
        export_btn.bind(on_release=lambda *_: self.export_backup())
        col.add_widget(export_btn)
        self.add_widget(col)

    def export_backup(self):
        import json
        import time
        app = App.get_running_app()
        try:
            downloads = os.path.join(app.user_data_dir, "yedekler")
            os.makedirs(downloads, exist_ok=True)
            fname = f"tonaj-yedek-{time.strftime('%Y-%m-%d')}.json"
            path = os.path.join(downloads, fname)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(app.state, f, ensure_ascii=False, indent=2)
            app.state["settings"]["lastBackupAt"] = core.now_ms()
            app.save()
            toast(app, f"Yedek kaydedildi: {path}")
        except Exception as e:
            toast(app, f"Yedekleme hatası: {e}")


# ---------------------------------------------------------------------------
# ANA UYGULAMA
# ---------------------------------------------------------------------------
class RootWidget(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        bg_rect(self, BG)
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(ProgramScreen(name="program"))
        self.sm.add_widget(HistoryScreen(name="history"))
        self.sm.add_widget(LibraryScreen(name="library"))
        self.sm.add_widget(ReportScreen(name="report"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        self.add_widget(self.sm)

        nav = BoxLayout(size_hint_y=None, height=dp(56))
        bg_rect(nav, CARD)
        for name, icon in [("program", "Program"), ("history", "Geçmiş"),
                            ("library", "Hareketler"), ("report", "Rapor"), ("settings", "Ayarlar")]:
            b = Button(text=icon, background_normal="", background_color=CARD, color=MUTED, font_size=sp_(11))
            b.bind(on_release=lambda *_, n=name: setattr(self.sm, "current", n))
            nav.add_widget(b)
        self.add_widget(nav)

        self.toast_label = Label(text="", size_hint=(None, None), opacity=0,
                                  color=(0.07, 0.08, 0.06, 1), bold=True)
        bg_rect(self.toast_label, ACCENT)

    def show_toast(self, msg):
        self.toast_label.text = msg
        self.toast_label.opacity = 1
        Clock.schedule_once(lambda *_: setattr(self.toast_label, "opacity", 0), 1.6)


class TonajApp(App):
    def build(self):
        self.title = "Tonaj"
        Window.clearcolor = BG
        self.state, _ = core.load_state(get_data_path())
        self.root_widget = RootWidget()
        return self.root_widget

    def save(self):
        core.save_state(get_data_path(), self.state)


if __name__ == "__main__":
    TonajApp().run()
