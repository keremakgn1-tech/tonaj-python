"""
TONAJ - Antrenman Takibi (Kivy / Android)
main.py, arayuzu (View) core.py'deki (Model/Logic) fonksiyonlara baglar.
"""
import os
import json
import threading
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
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform
from kivy.base import ExceptionHandler, ExceptionManager

import core

# ---------------------------------------------------------------------------
# Renk paleti (mevcut web uygulamasiyla ayni: koyu + limon yesili vurgu)
# ---------------------------------------------------------------------------
BG = (0x12/255, 0x13/255, 0x16/255, 1)
CARD = (0x1B/255, 0x1D/255, 0x21/255, 1)
CARD2 = (0x23/255, 0x25/255, 0x29/255, 1)
RAISED = (0x2A/255, 0x2D/255, 0x32/255, 1)
BORDER = (0x2E/255, 0x31/255, 0x38/255, 1)
DIVIDER = (0x3E/255, 0x42/255, 0x4A/255, 1)  # satir ayirici - BORDER'dan biraz daha secilebilir
TEXT = (0xF5/255, 0xF5/255, 0xF0/255, 1)
MUTED = (0xC2/255, 0xC4/255, 0xC9/255, 1)
FAINT = (0x9E/255, 0xA0/255, 0xA6/255, 1)
ACCENT = (0xE8/255, 0xFF/255, 0x3D/255, 1)
ACCENT_DARK = (0x0C/255, 0x1A/255, 0x02/255, 1)
DANGER = (0xFF/255, 0x5A/255, 0x5A/255, 1)
STEEL = (0x5B/255, 0x7F/255, 0xB5/255, 1)

# NOT: buildozer.spec'teki "version" ile ELLE senkron tutulmali (Ayarlar >
# Hakkinda bolumunde gosteriliyor) - APK derlenirken otomatik okunmuyor,
# cunku .spec dosyasi APK'nin icine gomulmuyor (source.include_exts'te yok).
APP_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Birim sistemi (kg / lb)
# ---------------------------------------------------------------------------
# ONEMLI: Depoda (kaydedilen JSON'da) agirlik HER ZAMAN kg olarak tutulur -
# gecmis, hedefler, PR'lar, oneriler... hepsi kg. "lb" sadece bir GORUNUM
# tercihi: kullanici Ayarlar'dan lb secerse, sadece EKRANDA gosterilen sayilar
# ve kullanicinin YENI girdigi sayilarin depoya yazilmadan once kg'ye
# cevrilmesi degisir. Bu sayede birim degistirmek eski verileri BOZMAZ/
# yeniden yorumlamaz - her zaman ayni kg degerleri kalir, sadece farkli
# bir cetvelle gosterilir.
KG_PER_LB = 0.45359237


def weight_unit():
    try:
        app = App.get_running_app()
        return (app.state.get("settings") or {}).get("weightUnit", "kg")
    except Exception:
        return "kg"


def to_display_weight(kg_value):
    """Kg olarak saklanan bir degeri, kullanicinin sectigi birimde (sayi
    olarak) dondurur - ekranda gosterme icin."""
    if kg_value is None:
        return None
    return kg_value / KG_PER_LB if weight_unit() == "lb" else kg_value


def to_storage_kg(display_value):
    """Kullanicinin (secili birimde) girdigi bir sayiyi, depoya yazilacak
    kg degerine cevirir."""
    if display_value is None:
        return None
    return display_value * KG_PER_LB if weight_unit() == "lb" else display_value


def fmt_weight(kg_value, decimals=True):
    """Kg olarak saklanan bir degeri '70kg' / '154.3lb' gibi, birimiyle
    birlikte hazir bir gosterim metnine cevirir."""
    if kg_value is None:
        return ""
    v = to_display_weight(kg_value)
    return f"{v:g}{weight_unit()}"


def get_data_path():
    try:
        app = App.get_running_app()
        base = app.user_data_dir if app else "."
    except Exception:
        base = "."
    return os.path.join(base, "tonaj_state.json")


def _write_json_string_to_file(path, payload):
    """Onceden JSON'a cevrilmis (immutable) bir string'i diske atomik olarak
    yazar. core.save_state ile ayni "gecici dosya + os.replace" mantigini
    kullanir; sadece serialize etmeyi cagirandan (arka plan thread'inden
    guvenli sekilde ayirmak icin) devralmiyor - bkz. TonajApp.save()."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)
    os.replace(tmp, path)


def bg_rect(widget, color, radius=None):
    with widget.canvas.before:
        col = Color(*color)
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(10) if radius is None else radius])
    def upd(*_):
        rect.pos = widget.pos
        rect.size = widget.size
    widget.bind(pos=upd, size=upd)
    return col


def fit_popup_to_content(popup, content, extra=None, min_height=None, max_height_frac=0.9):
    """
    KOK NEDEN ("Hedef" ekranindaki orantisiz/bos gorunum): bazi popup'larin
    icerigi (content) sabit yukseklikli (size_hint_y=None) widget'lardan
    olusuyordu AMA content'in kendisi size_hint_y=None DEGILDI - yani content,
    Popup'un ayrilan (orn. ekranin %85'i kadar) alanini doldurmaya calisiyordu.
    Kivy'nin BoxLayout'u boyle bir durumda (hicbir cocuk esnemedigi icin) tum
    icerigi popup'un ALT kismina yigiyor ve bosluk EN USTTE kaliyor - kullanicinin
    gordugu "1. satirdan sonra kocaman bos alan, alanlar en altta" goruntusu
    tam olarak buydu.

    COZUM: content'i size_hint_y=None yapip minimum_height'ina bagliyoruz (kodun
    baska yerlerinde zaten kullanilan standart desen), sonra bu fonksiyonla
    Popup'un kendi yuksekligini content'in gercek ihtiyaci kadar (+ baslik
    cubugu/kenar bosluklari icin bir pay) ayarliyoruz - boylece popup da
    icerigi kadar kompakt gorunuyor, bos alan kalmiyor.
    """
    if extra is None:
        extra = dp(72)  # Popup'un kendi baslik cubugu + ayirici + kenar boslugu payi
    if min_height is None:
        min_height = dp(120)

    def update(*_):
        from kivy.core.window import Window as _W
        target = content.height + extra
        cap = _W.height * max_height_frac
        popup.height = max(min_height, min(target, cap))

    content.bind(minimum_height=update)
    update()


class Card(BoxLayout):
    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        super().__init__(**kw)
        bg_rect(self, CARD)
        self.padding = dp(12)
        self.spacing = dp(6)


def styled_button(text, color=ACCENT, text_color=(0.07, 0.08, 0.06, 1), **kw):
    # setdefault kullaniyoruz cunku bazi cagiranlar size_hint_y/height'i kendi
    # **kw'si icinde ayrica veriyor - dogrudan Button(size_hint_y=None,
    # height=..., **kw) yazsaydik, o zaman ayni anahtar iki kere verilmis
    # olur ve Button() "got multiple values for keyword argument" hatasiyla
    # patlardi. setdefault, cagiranin verdigi deger varsa ona saygi duyar,
    # yoksa varsayilana duser.
    kw.setdefault("font_name", "Oswald")
    kw.setdefault("font_size", sp_(14))
    kw.setdefault("size_hint_y", None)
    kw.setdefault("height", dp(46))
    btn = Button(text=tr_upper(text), background_normal="", background_down="", background_color=color,
                 color=text_color, **kw)
    return btn


def label(text, size=16, color=TEXT, bold=False, halign="left", **kw):
    # KOK NEDEN (silme onay popup'larinda ustteki satirlarin kaybolmasi /
    # "yazilar gozukmuyor" sikayeti): text_size, hem genislik HEM YUKSEKLIK
    # birlikte verildiginde Kivy metni O KUTUYA KIRPARAK ciziyor. Eski kod
    # `text_size = lb.size` yapiyordu - yani text_size'in yukseklik kismini
    # da etikettin O ANKI (henuz sarmadan once, varsayilan dp(20)) yuksekligine
    # esitliyordu. Bu da metni DAHA ILK KAREDE dp(20)'lik bir kutuya kirpiyor,
    # texture_size da (kirpilmis haliyle) hep ~dp(20) olarak geri donuyordu -
    # yani "gercek" (coklu satirli) yukseklik ASLA hesaplanamiyordu ve etiket
    # boyu hicbir zaman buyumuyordu: uzun/coklu-satir metinler (ornegin
    # "Antrenmanı Sil" onay yazisi) kalici olarak kirpilmis/eksik gorunuyordu.
    #
    # DUZELTME: text_size'in yukseklik kismini HIC vermiyoruz (None birakiyoruz)
    # - bu, Kivy'ye "metni bu genislige sar, yuksekligi metnin dogal ihtiyacina
    # gore SINIRSIZ hesapla" der. texture_size artik metnin GERCEK (kirpilmemis)
    # yuksekligini verir, o da asagidaki binding ile etiketin height'ina yaziliyor.
    lb = Label(text=text, font_size=sp_(size), color=color, bold=bold,
               halign=halign, valign="middle", size_hint_y=None, **kw)
    lb.bind(width=lambda *_: setattr(lb, "text_size", (lb.width, None)))
    lb.bind(texture_size=lambda *_: setattr(lb, "height", max(lb.texture_size[1], dp(20))))
    lb.text_size = (lb.width, None)
    return lb


def sp_(v):
    from kivy.metrics import sp
    return sp(v)


def make_stepper(hint, val, step=1, decimals=False, min_val=0, max_val=None,
                  btn_width=None, row_height=None):
    """Uygulamadaki HER sayisal deger girisi icin ortak, klavye ACMAYAN
    bileşen. Android'de bazi cihazlarda (dogrulandi: Samsung + Gboard)
    herhangi bir TextInput'a dokunulup klavye acilinca uygulama tamamen
    donuyordu - input_type, softinput modu, manifest ayari gibi butun
    Python/Kivy taraflı duzeltmeler denendi ve HICBIRI degistirmedi; yani
    sorun native/Android tarafinda gercek bir kilitlenmeydi. Kok nedeni
    bulmak yerine EN BASIT ve KESIN cozum uygulandi: uygulamada artik hicbir
    yerde TextInput/klavye kullanilmiyor. Butun sayisal degerler (set,
    tekrar, agirlik, RIR, dinlenme...) bu +/- sayaciyla giriliyor - kisa
    dokunus bir adim, basili tutmak (0.4sn sonra) hizla tekrar eden
    adimlarla degeri degistiriyor.

    Donen widget'in ".value" ozelligi her zaman guncel (float ya da None)
    degeri tutar.
    """
    btn_width = btn_width if btn_width is not None else dp(44)
    row_h = row_height if row_height is not None else dp(40)

    box = BoxLayout(orientation="vertical", size_hint_y=None,
                     height=row_h + dp(18), spacing=dp(3))
    box.value = float(val) if val not in (None, "") else None

    box.add_widget(label(hint, size=12, color=MUTED, height=dp(16)))

    row = BoxLayout(size_hint_y=None, height=row_h, spacing=dp(6))
    minus = styled_button("−", color=RAISED, text_color=TEXT,
                           size_hint_x=None, width=btn_width, height=row_h)
    val_lbl = mono_label("—", size=16, color=TEXT, halign="center")
    plus = styled_button("+", color=RAISED, text_color=TEXT,
                          size_hint_x=None, width=btn_width, height=row_h)

    def refresh():
        if box.value is None:
            val_lbl.text = "—"
        else:
            val_lbl.text = f"{box.value:g}" if decimals else str(int(round(box.value)))

    def apply_delta(delta):
        base = box.value if box.value is not None else 0
        new = round(base + delta, 2)
        if min_val is not None:
            new = max(min_val, new)
        if max_val is not None:
            new = min(max_val, new)
        box.value = new
        refresh()

    def make_hold(delta):
        ev = [None]

        def _tick(*_):
            apply_delta(delta)

        def start(*_):
            apply_delta(delta)
            ev[0] = Clock.schedule_interval(_tick, 0.12)

        def stop(*_):
            if ev[0] is not None:
                ev[0].cancel()
                ev[0] = None

        return start, stop

    m_start, m_stop = make_hold(-step)
    p_start, p_stop = make_hold(step)
    minus.bind(on_press=m_start, on_release=m_stop)
    plus.bind(on_press=p_start, on_release=p_stop)

    refresh()
    row.add_widget(minus)
    row.add_widget(val_lbl)
    row.add_widget(plus)
    box.add_widget(row)
    return box


def mono_label(text, size=14, color=MUTED, halign="left", **kw):
    width = kw.pop("width", None)
    if width is not None:
        kw["size_hint_x"] = None
        kw["width"] = width
    kw.setdefault("bold", True)
    lb = Label(text=text, font_size=sp_(size), color=color,
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
        parts.append(fmt_weight(ex["targetWeight"]))
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
def _find_scrollview(widget):
    if isinstance(widget, ScrollView):
        return widget
    for c in widget.children:
        found = _find_scrollview(c)
        if found is not None:
            return found
    return None


class ProgramScreen(Screen):
    def on_pre_enter(self):
        self.render()

    def render(self, keep_scroll=False):
        app = App.get_running_app()
        state = app.state
        prev = _find_scrollview(self)
        prev_scroll_y = prev.scroll_y if (keep_scroll and prev is not None) else None
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")

        if state["activeSession"]:
            root.add_widget(self.render_active_session(state))
        else:
            root.add_widget(self.render_planner(state))
        self.add_widget(root)

        if prev_scroll_y is not None:
            new_scroll = _find_scrollview(self)
            if new_scroll is not None:
                def restore(*_):
                    new_scroll.scroll_y = prev_scroll_y
                Clock.schedule_once(restore, 0)

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
        add_btn.bind(on_release=lambda *_: (core.add_program_day(state), app.save(), self.render(keep_scroll=True)))
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
            eyebrow.add_widget(mono_label(ordinal, size=14, color=MUTED, width=dp(24)))
        if is_next:
            sirada = Label(text="SIRADA", font_name="Oswald", font_size=sp_(13), bold=True,
                            color=ACCENT_DARK, size_hint=(None, None), size=(dp(72), dp(20)))
            bg_rect(sirada, ACCENT)
            eyebrow.add_widget(sirada)
        eyebrow.add_widget(BoxLayout())  # sag tarafi dolduran bosluk
        up = Button(text="↑", size_hint=(None, None), size=(dp(26), dp(26)), background_color=(0,0,0,0), color=FAINT)
        down = Button(text="↓", size_hint=(None, None), size=(dp(26), dp(26)), background_color=(0,0,0,0), color=FAINT)
        dup = Button(text="Kopya", size_hint=(None, None), size=(dp(54), dp(28)), background_color=(0,0,0,0), color=MUTED, font_size=sp_(13))
        delete = Button(text="×", size_hint=(None, None), size=(dp(26), dp(26)), background_color=(0,0,0,0), color=DANGER)
        up.bind(on_release=lambda *_: (core.move_program_day(state, day["id"], -1), app.save(), self.render(keep_scroll=True)))
        down.bind(on_release=lambda *_: (core.move_program_day(state, day["id"], 1), app.save(), self.render(keep_scroll=True)))
        dup.bind(on_release=lambda *_: (core.duplicate_program_day(state, day["id"]), app.save(), self.render(keep_scroll=True)))
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
            card.add_widget(label(meta + f" · {len(day['exercises'])} hareket", size=14, color=MUTED, height=dp(20)))

        for i, ex in enumerate(day["exercises"]):
            row = ClickableRow(size_hint_y=None, height=dp(40), spacing=dp(6), padding=(0, dp(2)))
            row.bind(on_release=lambda *_, d=day, e=ex: self.open_target_editor(d, e["name"]))
            with row.canvas.before:
                Color(*DIVIDER)
                rline = Line(points=[0, row.top, row.width, row.top], width=dp(1))
            row.bind(pos=lambda w, *_: setattr(rline, 'points', [w.x, w.top, w.right, w.top]),
                     size=lambda w, *_: setattr(rline, 'points', [w.x, w.top, w.right, w.top]))
            row.add_widget(label(ex["name"], size=14.5, bold=True, color=TEXT))
            tgt = target_label(ex) or "hedef yok"
            tgt_lbl = mono_label(tgt, size=13.5, color=MUTED, halign="right", size_hint_x=None, width=dp(150))
            row.add_widget(tgt_lbl)
            rm = Button(text="×", size_hint=(None, None), size=(dp(24), dp(24)), background_color=(0,0,0,0), color=MUTED, font_size=sp_(16))
            rm.bind(on_release=lambda *_, d=day, idx=i: (core.remove_exercise_from_day(state, d["id"], idx), app.save(), self.render(keep_scroll=True)))
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
        start = Button(text="BAŞLA", font_name="Oswald", font_size=sp_(15),
                        background_normal="", background_down="", background_color=ACCENT,
                        color=ACCENT_DARK, size_hint_x=None, width=dp(110))
        start.bind(on_release=lambda *_: self.start_session(day["id"]))
        actions.add_widget(start)
        card.add_widget(actions)
        return card

    def confirm_delete_day(self, day_id):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(label("Bu günü silmek istediğine emin misin?"))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title="Günü Sil", content=content, size_hint=(0.85, None))
        fit_popup_to_content(popup, content)
        yes = styled_button("Evet, Sil", color=DANGER, text_color=(1, 1, 1, 1))
        no = styled_button("Vazgeç", color=RAISED, text_color=TEXT)
        yes.bind(on_release=lambda *_: (core.delete_program_day(app.state, day_id), app.save(), popup.dismiss(), self.render(keep_scroll=True)))
        no.bind(on_release=popup.dismiss)
        row.add_widget(no); row.add_widget(yes)
        content.add_widget(row)
        popup.open()

    def open_exercise_picker(self, day_id):
        # KOK NEDEN ("Hareket Ekle"ye basinca donma hissi): bu fonksiyon
        # ONCEDEN, TEK bir dokunma/on_release cagrisinin icinde, kutuphanedeki
        # TUM hareketler icin (80'den fazla) tek tek Button widget'i olusturup
        # her birinin metnini SENKRON olarak font'tan dokup dokusuna (texture)
        # ceviriyordu - bu iş bu (guclu, yazilim GPU'lu) sunucuda hizli olsa
        # da GERCEK bir telefonda (ozellikle ilk acilista, font glyph onbellegi
        # bosken) fark edilir bir sure surebilir. O sure boyunca ekrana HICBIR
        # SEY cizilmiyordu (popup'in kendisi de dahil) - kullaniciya "dokunma
        # algilanmadi, uygulama dondu" hissi veren tam olarak buydu.
        #
        # DUZELTME: Once popup'i (baslik + bos/"Yükleniyor" govde ile) HEMEN
        # aciyoruz - bu, dokunmanin algilandigini ANINDA gosteriyor. Asil agir
        # is (80+ butonun olusturulmasi) bir sonraki Clock karesine
        # devrediliyor - boylece popup'in kendi acilis cizimi ekrana yansidiktan
        # SONRA buton listesi kuruluyor, "donma" hissi ortadan kalkiyor
        # (toplam sure ayni ama kullanici artik bir tepki GORUYOR).
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        loading_lbl = label("Yükleniyor…", color=MUTED, halign="center", height=dp(200))
        content.add_widget(loading_lbl)
        popup = Popup(title="Hareket Seç", size_hint=(0.9, 0.8), content=content)
        popup.open()

        def build_list(*_a):
            names = core.all_exercise_names(app.state)
            content.clear_widgets()
            scroll = ScrollView()
            col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            col.bind(minimum_height=col.setter("height"))
            for n in names:
                b = Button(text=n, size_hint_y=None, height=dp(38), background_normal="", background_down="", background_color=RAISED, color=TEXT)
                b.bind(on_release=lambda *_, name=n: (popup.dismiss(), self.open_target_editor({"id": day_id}, name)))
                col.add_widget(b)
            scroll.add_widget(col)
            content.add_widget(scroll)
            # NOT: serbest metinle "yeni hareket adi" ekleme kaldirildi -
            # klavye acan tek yer buydu. Kutuphanede zaten onceden tanimli
            # genis bir hareket listesi var (bkz. core.DEFAULT_EXERCISES),
            # secim bu listeden yapiliyor.

        Clock.schedule_once(build_list, 0)

    def open_target_editor(self, day, name):
        # Bu popup'taki alanlar (Set/Tekrar min/Tekrar max/Agirlik/RIR/
        # Dinlenme) klavye kullanmiyor - bkz. make_stepper() tanimindaki not.
        app = App.get_running_app()
        state = app.state
        day_obj = next((d for d in state["program"]["days"] if d["id"] == day["id"]), None)
        existing = next((e for e in day_obj["exercises"] if e["name"] == name), {}) if day_obj else {}

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(label(name, size=17, bold=True, height=dp(28)))

        sets_i = make_stepper("Set", existing.get("targetSets"), step=1)
        rmin_i = make_stepper("Tekrar min", existing.get("targetRepsMin"), step=1)
        rmax_i = make_stepper("Tekrar max", existing.get("targetRepsMax"), step=1)
        # targetWeight depoda HER ZAMAN kg - kullaniciya kendi sectigi birimde
        # gosteriyoruz, kaydederken (asagida do_save icinde) tekrar kg'ye ceviriyoruz.
        w_step = 2.5 if weight_unit() == "kg" else 5
        w_i = make_stepper(f"Ağırlık ({weight_unit()})", to_display_weight(existing.get("targetWeight")),
                            step=w_step, decimals=True)
        rir_i = make_stepper("RIR", existing.get("targetRIR"), step=1, max_val=10)
        rest_i = make_stepper("Dinlenme (sn)", existing.get("restSeconds"), step=15)
        for w in (sets_i, rmin_i, rmax_i, w_i, rir_i, rest_i):
            content.add_widget(w)

        popup = Popup(title="Hedef", content=content, size_hint=(0.9, None))
        fit_popup_to_content(popup, content)
        save_btn = styled_button("Kaydet")

        def to_num(value, cast=int):
            if value is None:
                return None
            return cast(value)

        def do_save(*_):
            core.set_day_exercise_target(
                state, day["id"], name,
                target_sets=to_num(sets_i.value), target_reps_min=to_num(rmin_i.value),
                target_reps_max=to_num(rmax_i.value),
                target_weight=to_storage_kg(to_num(w_i.value, float)),
                target_rir=to_num(rir_i.value), rest_seconds=to_num(rest_i.value),
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
        title_row.add_widget(label(sess["dayName"] or "Serbest Antrenman", size=14, bold=True, color=MUTED))
        if sess["isDeload"]:
            deload_tag = Label(text="DELOAD", font_name="Oswald", font_size=sp_(13), bold=True,
                                color=ACCENT_DARK, size_hint=(None, None), size=(dp(62), dp(18)))
            bg_rect(deload_tag, ACCENT)
            title_row.add_widget(deload_tag)
        header.add_widget(title_row)
        tonnage = core.session_tonnage(sess)
        tonnage_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self._tonnage_lbl = mono_label(f"{to_display_weight(tonnage):g}", size=32, color=ACCENT, bold=True, height=dp(44))
        tonnage_row.add_widget(self._tonnage_lbl)
        tonnage_row.add_widget(label(weight_unit(), size=14, color=MUTED, height=dp(44)))
        header.add_widget(tonnage_row)
        col.add_widget(header)

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

    def add_adhoc_exercise(self):
        # open_exercise_picker()'daki AYNI donma hissi buradaki 80+ hareketlik
        # listede de vardi - AYNI cozum (once popup'i bos ac, buton listesini
        # bir Clock karesi sonra kur) burada da uygulaniyor. Detay icin
        # open_exercise_picker()'in basindaki yorum bloguna bak.
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=dp(10))
        loading_lbl = label("Yükleniyor…", color=MUTED, halign="center", height=dp(200))
        content.add_widget(loading_lbl)
        popup = Popup(title="Hareket Ekle", content=content, size_hint=(0.9, 0.8))
        popup.open()

        def build_list(*_a):
            names = core.all_exercise_names(app.state)
            content.clear_widgets()
            scroll = ScrollView()
            col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
            col.bind(minimum_height=col.setter("height"))
            for n in names:
                b = Button(text=n, size_hint_y=None, height=dp(38), background_normal="", background_down="", background_color=RAISED, color=TEXT)
                def pick(*_, name=n):
                    core.add_exercise_to_session(app.state, name)
                    app.save(); popup.dismiss(); self.render()
                b.bind(on_release=pick)
                col.add_widget(b)
            scroll.add_widget(col)
            content.add_widget(scroll)

        Clock.schedule_once(build_list, 0)

    def exercise_card(self, state, sess, ex, idx):
        # Onceden her set eklendiginde/silindiginde TUM ekran (basliktan diger
        # tum hareket kartlarina kadar) yeniden ciziliyordu - bu da her "+" ya
        # basista gozle gorulur bir kasmaya sebep oluyordu. Simdi sadece BU
        # kart kendi icerigini yeniden kuruyor (card.clear_widgets() + rebuild),
        # digerlerine dokunulmuyor; ustteki tonaj sayaci da ayrica hafifce
        # guncelleniyor (bkz. self.refresh_tonnage).
        app = App.get_running_app()
        card = Card(size_hint_y=None, spacing=dp(4))
        card.bind(minimum_height=card.setter("height"))

        def rebuild(*_):
            card.clear_widgets()
            working = [s for s in ex["sets"] if not s.get("isWarmup")]
            prev_max = core.max_weight_for(state, ex["name"])
            head = BoxLayout(size_hint_y=None, height=dp(26))
            head.add_widget(label(ex["name"], size=16, bold=True))
            rm_ex = Button(text="×", size_hint=(None, None), size=(dp(26), dp(26)), background_color=(0, 0, 0, 0), color=MUTED, font_size=sp_(17))
            rm_ex.bind(on_release=lambda *_: (sess["exercises"].pop(idx), app.save(), self.render(keep_scroll=True)))
            head.add_widget(rm_ex)
            card.add_widget(head)
            meta = f"{len(working)} SET" + (f" · ÖNCEKİ REKOR {fmt_weight(prev_max).upper()}" if prev_max else "")
            card.add_widget(mono_label(meta, size=14, color=MUTED, height=dp(20)))

            tgt = target_label(ex)
            if tgt:
                tgt_row = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
                tgt_row.add_widget(label("HEDEF", size=14, bold=True, color=ACCENT, size_hint_x=None, width=dp(56)))
                tgt_row.add_widget(mono_label(tgt, size=14, color=TEXT))
                card.add_widget(tgt_row)
            if ex.get("suggestedWeight") is not None:
                txt = f"{fmt_weight(ex['suggestedWeight'])} — {SUGGEST_TEXT.get(ex.get('suggestReason'), '')}"
                sug_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
                sug_row.add_widget(label("ÖNERİ", size=14, bold=True, color=STEEL, size_hint_x=None, width=dp(56)))
                sug_row.add_widget(label(txt, size=14, color=STEEL))
                card.add_widget(sug_row)

            for si, s in enumerate(ex["sets"]):
                row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
                flag = "ISI" if s.get("isWarmup") else str(si + 1)
                row.add_widget(mono_label(f"{flag}", size=14, color=MUTED, width=dp(28)))
                row.add_widget(mono_label(f"{fmt_weight(s['weight'])} × {s['reps']}", size=14,
                                           color=FAINT if s.get("isWarmup") else TEXT))
                badge = core.rir_badge_info(s, ex)
                if badge:
                    badge_color = {"easy": ACCENT, "hard": DANGER, "ontarget": STEEL, "neutral": MUTED}[badge["kind"]]
                    row.add_widget(mono_label(badge["text"], size=14, color=badge_color, halign="right"))
                rm = Button(text="×", size_hint=(None, None), size=(dp(24), dp(24)), background_color=(0, 0, 0, 0), color=MUTED, font_size=sp_(16))
                def do_remove(*_a, j=si):
                    core.remove_set(state, idx, j)
                    app.save()
                    rebuild()
                    self.refresh_tonnage()
                rm.bind(on_release=do_remove)
                row.add_widget(rm)
                card.add_widget(row)

            # Set eklerken kullanilan agirlik/tekrar/RIR alanlari - klavye
            # acmayan +/- sayaci (bkz. make_stepper() tanimindaki not).
            _sw = ex.get("suggestedWeight") or ex.get("targetWeight")
            w_step = 2.5 if weight_unit() == "kg" else 5
            form = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
            w_stepper = make_stepper(f"Ağırlık ({weight_unit()})", to_display_weight(_sw),
                                      step=w_step, decimals=True)
            r_stepper = make_stepper("Tekrar", ex.get("targetRepsMin"), step=1)
            form.add_widget(w_stepper)
            form.add_widget(r_stepper)
            card.add_widget(form)

            extra = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
            rir_stepper = make_stepper("RIR", ex.get("targetRIR"), step=1, max_val=10, btn_width=dp(36))
            rir_stepper.size_hint_x = 0.4
            warm_toggle = ToggleButton(text="Isınma Seti", size_hint_x=0.6, background_normal="", background_down="", background_color=RAISED, color=TEXT)
            extra.add_widget(rir_stepper)
            extra.add_widget(warm_toggle)
            card.add_widget(extra)

            add_btn = styled_button("+ Seti Ekle", color=ACCENT, text_color=(0.07, 0.08, 0.06, 1))
            card.add_widget(add_btn)

            def submit(*_):
                w = w_stepper.value
                r = r_stepper.value
                if not w or not r:
                    toast(app, "Geçerli değer gir")
                    return
                rir = int(rir_stepper.value) if rir_stepper.value is not None else None
                # Kullanici agirligi kendi sectigi birimde (kg ya da lb) girdi -
                # depoya HER ZAMAN kg olarak yaziyoruz (bkz. dosyanin basindaki
                # birim-sistemi notu).
                is_pr = core.add_set(state, idx, to_storage_kg(w), int(r), is_warmup=warm_toggle.state == "down", rir=rir)
                app.save()
                if is_pr:
                    toast(app, "YENİ REKOR — PR!")
                rebuild()
                self.refresh_tonnage()

            add_btn.bind(on_release=submit)

        rebuild()
        return card

    def refresh_tonnage(self):
        """Set eklendiginde/silindiginde SADECE ustteki tonaj sayacini gunceller;
        tum ekrani yeniden cizmekten (ve bunun yarattigi kasmadan) kacinir."""
        app = App.get_running_app()
        sess = app.state.get("activeSession")
        if sess and getattr(self, "_tonnage_lbl", None) is not None:
            self._tonnage_lbl.text = f"{to_display_weight(core.session_tonnage(sess)):g}"


# ---------------------------------------------------------------------------
# GECMIS EKRANI
# ---------------------------------------------------------------------------
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
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(label("Bu antrenman kaydını kalıcı olarak silmek istediğine emin misin? Bu işlem geri alınamaz."))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title="Antrenmanı Sil", content=content, size_hint=(0.85, None))
        fit_popup_to_content(popup, content)

        def do_delete(*_):
            core.remove_history_session(app.state, session_id)
            app.save()
            popup.dismiss()
            self.render(keep_scroll=True)

        yes = styled_button("Evet, Sil", color=DANGER, text_color=(1, 1, 1, 1))
        no = styled_button("Vazgeç", color=RAISED, text_color=TEXT)
        yes.bind(on_release=do_delete)
        no.bind(on_release=popup.dismiss)
        row.add_widget(no); row.add_widget(yes)
        content.add_widget(row)
        popup.open()

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
            title_col.add_widget(label(s["dayName"], size=14, color=MUTED, height=dp(18)))
        head.add_widget(title_col)
        head.add_widget(mono_label(fmt_weight(tonnage), size=15, color=ACCENT, bold=True, halign="right"))
        del_btn = Button(text="×", size_hint=(None, None), size=(dp(28), dp(28)),
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
                sub_row = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(6))
                sub_row.add_widget(mono_label("hedef " + target_label(ex), size=13, color=FAINT))
                if dtxt:
                    sub_row.add_widget(mono_label(dtxt, size=13, color=color, halign="right", bold=True))
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
            info.add_widget(mono_label(f"{len(pts)} antrenman", size=14, color=MUTED, height=dp(18)))
            row.add_widget(info)
            pr_col = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(70))
            # HATA DUZELTMESI: pts bossa (bu harekete hic set girilmemisse - ör.
            # bir antrenmana eklenip hic calisilmadan bitirilmis) eskiden yine de
            # "0kg / PR" yaziyordu - bu, kullaniciya olmayan bir rekor varmis
            # izlenimi veriyordu. Artik boyle durumda "—" gosteriliyor.
            if pts:
                pr_col.add_widget(mono_label(fmt_weight(pr), size=15, color=ACCENT, bold=True, halign="right", height=dp(22)))
                pr_col.add_widget(label("PR", size=14, color=MUTED, halign="right", height=dp(18)))
            else:
                pr_col.add_widget(mono_label("—", size=15, color=FAINT, bold=True, halign="right", height=dp(22)))
                pr_col.add_widget(label("yok", size=14, color=FAINT, halign="right", height=dp(18)))
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
            cell.add_widget(label(unit_label, size=14, color=MUTED, halign="center", height=dp(18)))
            return cell
        stats.add_widget(stat_cell(f"{to_display_weight(tonnage):g}", f"{weight_unit()} bu hafta"))
        stats.add_widget(stat_cell(str(count), "antrenman"))
        stats.add_widget(stat_cell(str(len(prs)), "yeni rekor"))
        col.add_widget(stats)

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


# ---------------------------------------------------------------------------
# AYARLAR EKRANI
# ---------------------------------------------------------------------------
class SettingsScreen(Screen):
    # Android'in Storage Access Framework (SAF) sonuc kodlari - iki farkli
    # islem (disa aktar / ice aktar) icin ayri kodlar, ayni anda ikisi de
    # tetiklenirse birbirine karismasin diye.
    _REQ_EXPORT = 4001
    _REQ_IMPORT = 4002

    def on_pre_enter(self):
        self.render()

    def section_header(self, text):
        return label(text, size=14, color=MUTED, bold=True, height=dp(26))

    def render(self):
        app = App.get_running_app()
        self.clear_widgets()
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))

        # ---- Birim sistemi ----
        col.add_widget(self.section_header("BİRİM SİSTEMİ"))
        cur_unit = weight_unit()

        def set_unit(u, *_):
            app.state.setdefault("settings", {})["weightUnit"] = u
            app.save()
            self.render()

        unit_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        kg_btn = styled_button("KG", color=ACCENT if cur_unit == "kg" else RAISED,
                                text_color=ACCENT_DARK if cur_unit == "kg" else TEXT)
        lb_btn = styled_button("LB", color=ACCENT if cur_unit == "lb" else RAISED,
                                text_color=ACCENT_DARK if cur_unit == "lb" else TEXT)
        kg_btn.bind(on_release=lambda *_: set_unit("kg"))
        lb_btn.bind(on_release=lambda *_: set_unit("lb"))
        unit_row.add_widget(kg_btn); unit_row.add_widget(lb_btn)
        col.add_widget(unit_row)
        col.add_widget(label(
            "Tüm ağırlıklar bu birimde gösterilir. Kayıtlı veri her zaman kg "
            "olarak tutulur, birim değiştirmek geçmiş verini bozmaz.",
            color=FAINT, size=13, height=dp(40)))

        # ---- Yedekleme ----
        col.add_widget(self.section_header("YEDEKLEME"))
        last_backup = app.state.get("settings", {}).get("lastBackupAt")
        if last_backup:
            from datetime import datetime
            dt = datetime.fromtimestamp(last_backup / 1000)
            info_txt = f"Son yedekleme: {dt.strftime('%d.%m.%Y %H:%M')}"
        else:
            info_txt = "Henüz hiç yedek almadın."
        col.add_widget(label(info_txt, color=FAINT, size=14, height=dp(24)))

        export_btn = styled_button("Yedeği Dışa Aktar")
        export_btn.bind(on_release=lambda *_: self.export_backup())
        col.add_widget(export_btn)

        import_btn = styled_button("Yedekten Geri Yükle", color=RAISED, text_color=TEXT)
        import_btn.bind(on_release=lambda *_: self.confirm_import_backup())
        col.add_widget(import_btn)

        col.add_widget(label(
            "Dışa aktarırken kayıt yerini telefonunda sen seçersin (İndirilenler, "
            "Drive, vb.). Geri yükleme MEVCUT tüm verinin üzerine yazar.",
            color=FAINT, size=13, height=dp(56)))

        # ---- Veri yonetimi ----
        col.add_widget(self.section_header("VERİ YÖNETİMİ"))
        reset_btn = styled_button("Tüm Verileri Sıfırla", color=RAISED, text_color=DANGER)
        reset_btn.bind(on_release=lambda *_: self.confirm_reset_all())
        col.add_widget(reset_btn)
        col.add_widget(label(
            "Programını, geçmişini ve tüm kayıtlarını siler; uygulama sıfırdan "
            "kurulmuş gibi olur. Önce yedek almanı öneririz.",
            color=FAINT, size=13, height=dp(40)))

        # ---- Hakkinda ----
        col.add_widget(self.section_header("HAKKINDA"))
        col.add_widget(label(f"Tonaj — sürüm {APP_VERSION}", color=FAINT, size=14, height=dp(22)))
        col.add_widget(label("Verilerin bu cihazda kalıcı olarak saklanıyor.", color=FAINT, size=14, height=dp(22)))

        scroll.add_widget(col)
        self.add_widget(scroll)

    def confirm_reset_all(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(label(
            "TÜM programın, antrenman geçmişin ve ayarların KALICI olarak "
            "silinecek. Bu işlem GERİ ALINAMAZ. Devam etmeden önce yedek "
            "almanı öneririz.", color=TEXT))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title="Tüm Verileri Sıfırla", content=content, size_hint=(0.85, None))
        fit_popup_to_content(popup, content)

        def do_reset(*_):
            app.state = core.default_state()
            app.save()
            popup.dismiss()
            self.render()
            toast(app, "Tüm veriler sıfırlandı")

        yes = styled_button("Evet, Sıfırla", color=DANGER, text_color=(1, 1, 1, 1))
        no = styled_button("Vazgeç", color=RAISED, text_color=TEXT)
        yes.bind(on_release=do_reset)
        no.bind(on_release=popup.dismiss)
        row.add_widget(no); row.add_widget(yes)
        content.add_widget(row)
        popup.open()

    # ------------------------------------------------------------------
    # DISA AKTAR (export) - Android'in "Storage Access Framework" (SAF)
    # dosya kaydetme dialogu ile: kullanici KENDI SECTIGI bir konuma
    # (Indirilenler, Drive, baska bir klasor...) kaydedebiliyor. Onceki
    # surum sadece uygulamanin kendi ozel/gizli klasorune yaziyordu -
    # kullanici Dosyalar uygulamasindan o dosyayi hicbir zaman goremiyordu.
    # ------------------------------------------------------------------
    def export_backup(self):
        app = App.get_running_app()
        import time
        fname = f"tonaj-yedek-{time.strftime('%Y-%m-%d')}.json"
        payload = json.dumps(app.state, ensure_ascii=False, indent=2).encode("utf-8")

        if platform != "android":
            # Masaustunde (test/gelistirme) SAF yok - dosya secici yerine
            # dogrudan calisma dizinine yaziyoruz ki en azindan islev test
            # edilebilsin. Gercek cihazda asagidaki android dali calisir.
            try:
                path = os.path.join(os.getcwd(), fname)
                with open(path, "wb") as f:
                    f.write(payload)
                app.state["settings"]["lastBackupAt"] = core.now_ms()
                app.save()
                self.render()
                toast(app, f"Yedek kaydedildi: {path}")
            except Exception as e:
                toast(app, f"Yedekleme hatası: {e}")
            return

        try:
            from jnius import autoclass
            from android import activity

            Intent = autoclass("android.content.Intent")
            Activity = autoclass("android.app.Activity")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("application/json")
            intent.putExtra(Intent.EXTRA_TITLE, fname)

            def on_result(request_code, result_code, data_intent):
                if request_code != self._REQ_EXPORT:
                    return
                activity.unbind(on_activity_result=on_result)
                if result_code != Activity.RESULT_OK or data_intent is None:
                    Clock.schedule_once(lambda *_: toast(app, "Dışa aktarma iptal edildi"))
                    return
                try:
                    uri = data_intent.getData()
                    resolver = PythonActivity.mActivity.getContentResolver()
                    out_stream = resolver.openOutputStream(uri)
                    out_stream.write(payload)
                    out_stream.flush()
                    out_stream.close()
                    app.state["settings"]["lastBackupAt"] = core.now_ms()
                    app.save()

                    def _done(*_):
                        self.render()
                        toast(app, "Yedek kaydedildi")
                    Clock.schedule_once(_done)
                except Exception as e:
                    # NOT: Python 3'te "except ... as e" blogu bitince e
                    # OTOMATIK silinir - asagidaki gibi bir lambda'nin
                    # icinde dogrudan e'yi yakalamaya calissaydik, lambda
                    # (Clock tarafindan) daha SONRA cagrildiginda "e" artik
                    # yok olmus olacagindan NameError firlatirdi. Once
                    # duz bir yerel degiskene (err) kopyalayip lambda'nin
                    # ONU yakalamasini sagliyoruz.
                    err = e
                    Clock.schedule_once(lambda *_: toast(app, f"Yedekleme hatası: {err}"))

            activity.bind(on_activity_result=on_result)
            PythonActivity.mActivity.startActivityForResult(intent, self._REQ_EXPORT)
        except Exception as e:
            toast(app, f"Yedekleme başlatılamadı: {e}")

    # ------------------------------------------------------------------
    # ICE AKTAR (import) - kullanicinin SECTIGI bir .json yedek dosyasini
    # okuyup MEVCUT tum uygulama verisinin (program, gecmis, hareketler...)
    # YERINE koyar. Yikici bir islem oldugu icin once onay istiyoruz.
    # ------------------------------------------------------------------
    def confirm_import_backup(self):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(label(
            "Bir yedek dosyası seçeceksin. Seçtiğin dosyadaki veri, bu "
            "cihazdaki TÜM mevcut programın/geçmişin/kayıtların YERİNE "
            "geçecek. Bu işlem geri alınamaz. Devam edilsin mi?"))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title="Yedekten Geri Yükle", content=content, size_hint=(0.85, None))
        fit_popup_to_content(popup, content)

        def go(*_):
            popup.dismiss()
            self.import_backup()

        yes = styled_button("Devam Et", color=DANGER, text_color=(1, 1, 1, 1))
        no = styled_button("Vazgeç", color=RAISED, text_color=TEXT)
        yes.bind(on_release=go)
        no.bind(on_release=popup.dismiss)
        row.add_widget(no); row.add_widget(yes)
        content.add_widget(row)
        popup.open()

    def import_backup(self):
        app = App.get_running_app()

        if platform != "android":
            toast(app, "Bu özellik şu an sadece Android'de kullanılabilir")
            return

        try:
            from jnius import autoclass
            from android import activity

            Intent = autoclass("android.content.Intent")
            Activity = autoclass("android.app.Activity")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            # "*/*" kullaniyoruz: bazi dosya yoneticileri .json'u
            # "application/json" olarak degil "text/plain" gibi farkli bir
            # mime ile isaretliyor - tur kisitlarsak kullanici kendi yedek
            # dosyasini listede goremeyebilirdi. Icerigi zaten kendimiz
            # dogruluyoruz (asagida).
            intent.setType("*/*")

            def on_result(request_code, result_code, data_intent):
                if request_code != self._REQ_IMPORT:
                    return
                activity.unbind(on_activity_result=on_result)
                if result_code != Activity.RESULT_OK or data_intent is None:
                    Clock.schedule_once(lambda *_: toast(app, "Geri yükleme iptal edildi"))
                    return
                try:
                    uri = data_intent.getData()
                    resolver = PythonActivity.mActivity.getContentResolver()
                    input_stream = resolver.openInputStream(uri)

                    BufferedInputStream = autoclass("java.io.BufferedInputStream")
                    ByteArrayOutputStream = autoclass("java.io.ByteArrayOutputStream")
                    buffered = BufferedInputStream(input_stream)
                    byte_out = ByteArrayOutputStream()
                    chunk = bytearray(8192)
                    while True:
                        n = buffered.read(chunk, 0, len(chunk))
                        if n == -1:
                            break
                        byte_out.write(chunk, 0, n)
                    raw = bytes(byte_out.toByteArray())
                    buffered.close()

                    new_state = json.loads(raw.decode("utf-8"))
                    missing = [k for k in ("history", "program", "library", "activeSession")
                               if k not in new_state]
                    if missing:
                        raise ValueError(f"Geçersiz yedek dosyası (eksik alan: {', '.join(missing)})")

                    new_state.setdefault("settings", {})
                    new_state["settings"]["lastBackupAt"] = new_state["settings"].get("lastBackupAt")
                    app.state = new_state
                    app.save()

                    def _done(*_):
                        self.render()
                        toast(app, "Yedek geri yüklendi")
                    Clock.schedule_once(_done)
                except Exception as e:
                    # bkz. export_backup()'taki ayni desendeki not: Clock
                    # tarafindan sonra cagrilacak bir lambda "except as e"
                    # blogu bitince silinen e'yi degil, buradaki duz "err"
                    # kopyasini yakalamali.
                    err = e
                    Clock.schedule_once(lambda *_: toast(app, f"Geri yükleme hatası: {err}"))

            activity.bind(on_activity_result=on_result)
            PythonActivity.mActivity.startActivityForResult(intent, self._REQ_IMPORT)
        except Exception as e:
            toast(app, f"Geri yükleme başlatılamadı: {e}")


# ---------------------------------------------------------------------------
# ANA UYGULAMA
# ---------------------------------------------------------------------------
class RootWidget(FloatLayout):
    def __init__(self, **kw):
        # Not: bu widget onceden BoxLayout idi ve toast_label (PR/kayit bildirimi)
        # olusturulup hicbir yere eklenmiyordu (add_widget cagrisi eksikti) -
        # yani "YENİ REKOR", "ANTRENMAN KAYDEDİLDİ" gibi bildirimler hicbir zaman
        # goruntude cikmiyordu. FloatLayout'a gecip toast'u gercek bir kayan
        # (overlay) etiket olarak eklendi.
        super().__init__(**kw)
        bg_rect(self, BG)
        main_col = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(ProgramScreen(name="program"))
        self.sm.add_widget(HistoryScreen(name="history"))
        self.sm.add_widget(LibraryScreen(name="library"))
        self.sm.add_widget(ReportScreen(name="report"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        main_col.add_widget(self.sm)

        nav = self.build_nav_bar()
        main_col.add_widget(nav)
        self.add_widget(main_col)

        self.toast_label = Label(text="", size_hint=(None, None), size=(dp(280), dp(44)),
                                  pos_hint={"center_x": 0.5, "top": 0.97},
                                  opacity=0, halign="center", valign="middle",
                                  font_name="Oswald", bold=True,
                                  color=(0.07, 0.08, 0.06, 1))
        self.toast_label.bind(size=lambda *_: setattr(self.toast_label, "text_size", self.toast_label.size))
        bg_rect(self.toast_label, ACCENT, radius=dp(8))
        self.add_widget(self.toast_label)


    NAV_ITEMS = [("program", "PROGRAM"), ("history", "GEÇMİŞ"), ("library", "HAREKETLER"),
                 ("report", "RAPOR"), ("settings", "AYARLAR")]

    def build_nav_bar(self):
        nav_wrap = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(58))
        top_border = Widget(size_hint_y=None, height=dp(1))
        bg_rect(top_border, BORDER, radius=0)
        nav_wrap.add_widget(top_border)

        nav = BoxLayout(size_hint_y=None, height=dp(57))
        bg_rect(nav, CARD, radius=0)
        self._nav_tabs = {}
        for i, (name, text) in enumerate(self.NAV_ITEMS):
            if i > 0:
                div = Widget(size_hint_x=None, width=dp(1))
                bg_rect(div, BORDER, radius=0)
                nav.add_widget(div)
            cell = ClickableRow(orientation="vertical", padding=(0, 0, 0, dp(7)))
            indicator = Widget(size_hint_y=None, height=dp(2))
            ind_col = bg_rect(indicator, BG, radius=0)
            lbl = Label(text=text, font_name="Oswald", font_size=sp_(13), bold=True, color=MUTED)
            cell.add_widget(indicator)
            cell.add_widget(lbl)
            cell.bind(on_release=lambda *_, n=name: setattr(self.sm, "current", n))
            nav.add_widget(cell)
            self._nav_tabs[name] = (ind_col, lbl)
        nav_wrap.add_widget(nav)
        self.sm.bind(current=self._refresh_nav)
        self._refresh_nav()
        return nav_wrap

    def _refresh_nav(self, *_):
        for name, (ind_col, lbl) in self._nav_tabs.items():
            active = (self.sm.current == name)
            ind_col.rgba = ACCENT if active else BG
            lbl.color = ACCENT if active else MUTED

    def show_toast(self, msg):
        self.toast_label.text = msg
        self.toast_label.opacity = 1
        Clock.schedule_once(lambda *_: setattr(self.toast_label, "opacity", 0), 1.6)


# ---------------------------------------------------------------------------
# COKME KORUMASI (VERI KAYBI ONLEME)
# ---------------------------------------------------------------------------
# Kullanicinin sordugu soru: "ani kapanmalarda bilgiler gider mi?" - dogru
# cevap oncesinde uc farkli senaryo vardi:
#   1) Kullanici normal sekilde uygulamayi kapatirsa (geri tusu/sistem):
#      TonajApp.on_stop() zaten bekleyen kaydi senkron olarak diske yaziyordu
#      - bu senaryoda veri kaybi YOKTU.
#   2) Kullanici Ana Ekran tusuyla uygulamayi ARKA PLANA atarsa: Kivy'nin
#      varsayilan on_pause() davranisi True donup uygulamayi "duraklatiyor"
#      (kapatmiyor) - AMA save() 0.5 saniyelik bir gecikmeyle (debounce) diske
#      yaziyor ve bu bekleme Clock uzerinden calisiyor; uygulama arka plandayken
#      Android herhangi bir an bellek ihtiyaciyla surecini tamamen
#      SONLANDIRABILIR - bu durumda o 0.5 saniyelik bekleyen kayit hic diske
#      gitmemis olabilirdi. (asagidaki on_pause duzeltmesi bunu kapatiyor)
#   3) Beklenmedik bir HATA/COKME olursa (tipki az once bulup duzelttigimiz
#      "Antrenman Notu Ekle" hatalari gibi - ileride baska/bilinmeyen bir hata
#      cikarsa da gecerli): Python'un normal calisma sekli, yakalanmayan bir
#      exception'i dogrudan yukari firlatip programi sonlandirmaktir - bu,
#      on_stop() GIBI "duzenli kapanis" adimlarini ATLAR, yani bekleyen
#      kaydedilmemis degisiklik (son "+", son not, vs.) diske hic yazilmadan
#      uygulama kapanirdi.
#
# COZUM: Kivy'nin ExceptionManager'ina GLOBAL bir handler kaydediyoruz. Bu,
# UI event dongusu icinde (butona basma, on_release, vb.) yakalanmayan HER
# exception'i - nereden gelirse gelsin, hangi buton/ekran olursa olsun -
# once buradan geciriyor: state'i HEMEN (bekleme olmadan, senkron) diske
# yaziyoruz, SONRA hatanin normal akisina (RAISE) izin veriyoruz. Yani
# uygulama yine de kapanabilir (bu handler hatanin KENDISINI duzeltmez,
# gelecekte cikabilecek baska bir hatayi da engellemez) AMA artik hangi
# hata olursa olsun kullanicinin en son yaptigi degisiklik KAYBOLMAZ.
class _CrashSaveHandler(ExceptionHandler):
    def handle_exception(self, exception):
        try:
            app = App.get_running_app()
            if app is not None and getattr(app, "state", None) is not None:
                if getattr(app, "_save_pending", None) is not None:
                    app._save_pending.cancel()
                    app._save_pending = None
                core.save_state(get_data_path(), app.state)
        except Exception:
            # Kayit sirasinda da bir sorun cikarsa bile orijinal hatanin
            # normal akisini (asagidaki RAISE) engellemiyoruz.
            pass
        return ExceptionManager.RAISE


ExceptionManager.add_handler(_CrashSaveHandler())


class TonajApp(App):
    def build(self):
        self.title = "Tonaj"
        Window.clearcolor = BG
        # Klavye: uygulamada artik HICBIR yerde TextInput/klavye kullanilmiyor
        # (bkz. make_stepper() tanimindaki not) - butun sayisal degerler +/-
        # sayaciyla giriliyor. Bu yuzden Window.softinput_mode ayarlamaya ya
        # da klavye acilis/kapanisini yonetmeye hic gerek kalmadi; manifest'te
        # android:windowSoftInputMode="adjustResize" (bkz. hook.py) sadece
        # Android'in standart/varsayilan davranisi olarak duruyor.
        self.state, _ = core.load_state(get_data_path())
        self._save_pending = None
        self.root_widget = RootWidget()
        return self.root_widget

    def save(self):
        # KOK NEDEN (genel "kasma" sikayeti): save() neredeyse HER tek
        # etkilesimde (set ekleme/silme, gun tasima, egzersiz ekleme/cikarma,
        # hedef kaydetme...) cagriliyordu ve HER cagrida core.save_state()
        # TUM state'i (gecmis biriktikce buyuyen) JSON'a cevirip UI thread'inde
        # SENKRON olarak diske yaziyordu. Bu, her dokunusta kisa bir donma
        # yaratiyordu ve gecmis buyudukce daha da belirginlesiyordu - "genel
        # bir kasma" tarifiyle tam olarak orttusuyor.
        #
        # DUZELTME (iki parca):
        #  1) Art arda gelen save() cagrilarini TEK bir yazmaya birlestiriyoruz
        #     (debounce) - ornegin bir antrenmanda ust uste "+" ya basildiginda
        #     her tikta degil, kisa bir durgunluktan sonra TEK sefer yaziliyor.
        #  2) Gercekten yazilacagi an, JSON serialize etme (hizli, CPU islemi)
        #     ana thread'de yapiliyor ama DOSYAYA YAZMA (yavas ve ongorulemez
        #     olan disk G/C) ayri bir thread'e devrediliyor - boylece UI thread'i
        #     (dolayisiyla dokunma/animasyon tepkisi) hicbir zaman disk
        #     yazimiyla bloke olmuyor. String immutable oldugu icin, o sirada
        #     app.state degismeye devam etse bile yariş (race condition) riski
        #     yok.
        if self._save_pending is not None:
            self._save_pending.cancel()
        self._save_pending = Clock.schedule_once(self._flush_save, 0.5)

    def _flush_save(self, *_):
        self._save_pending = None
        path = get_data_path()
        try:
            payload = json.dumps(self.state, ensure_ascii=False)
        except Exception:
            # Beklenmedik bir serialize hatasi olursa eski (senkron ama
            # guvenilir) yola geri don - veri kaybetmemek daha onemli.
            core.save_state(path, self.state)
            return
        threading.Thread(
            target=_write_json_string_to_file, args=(path, payload), daemon=True
        ).start()

    def on_stop(self):
        # Uygulama kapanirken bekleyen bir kayit varsa kaybetmeden hemen
        # (senkron) yaz - kapanista kisa bir gecikme kabul edilebilir,
        # onemli olan son degisikligin diske gitmesi.
        if getattr(self, "_save_pending", None) is not None:
            self._save_pending.cancel()
            self._save_pending = None
        core.save_state(get_data_path(), self.state)

    def on_pause(self):
        # KOK NEDEN: kullanici Ana Ekran tusuna basip uygulamayi ARKA PLANA
        # attiginda (uygulamayi kapatmadan) Android bu event'i tetikliyor.
        # save()'in 0.5 saniyelik "debounce" gecikmesi tam bu anda beklemede
        # olabilir - ve uygulama arka plandayken Android'in surec bellek
        # ihtiyaciyla uygulamayi HABERSIZ sonlandirma ihtimali her zaman var
        # (on_stop() bu durumda CAGRILMAYABILIR). Bu yuzden arka plana her
        # gecişte bekleyen kaydi burada da senkron olarak hemen diske yaziyoruz.
        # True donmek Android'e "uygulamayi tamamen kapatma, sadece duraklat"
        # diyor - yani kullanici geri donduğunde kaldigi yerden devam eder.
        if getattr(self, "_save_pending", None) is not None:
            self._save_pending.cancel()
            self._save_pending = None
        core.save_state(get_data_path(), self.state)
        return True


if __name__ == "__main__":
    TonajApp().run()
