"""
TONAJ - ekranlar arasinda PAYLASILAN yardimcilar.

KOK NEDEN (Task 18 - kod incelemesinde bulundu): main.py TUM uygulamayi
(5 ekran + App/RootWidget bootstrap + butun kucuk widget fabrikalarini)
TEK ~2000 satirlik dosyada tutuyordu - bir ekranda (orn. Ayarlar) yapilan
degisiklik icin dogru yeri bulmak, hic ilgisi olmayan bin(lerce) satir
arasinda gezinmek gerektiriyordu, ayni renk/boyut sabitleri her ekranda
TEKRAR TANIMLANMA riski tasiyordu.

DUZELTME: main.py, her ekranin kendi dosyasina (screens/program.py,
screens/history.py, screens/library.py, screens/report.py,
screens/settings.py) BOLUNDU; bu dosya da HEPSININ ORTAK kullandigi
seyleri (renk sabitleri, dp()/sp_() ile calisan kucuk widget fabrikalari,
birim donusum yardimcilari) barindiriyor - boylece bir davranis
degisikligi TEK yerden yapilabiliyor. Bu SAF bir tasima (pure refactor) -
davranis/gorunum HICBIR sekilde degismedi, kod sadece farkli dosyalara
yeniden dagitildi.

NOT (APP_VERSION/BUILD_STAMP/get_data_path burada DEGIL): bunlar bilerek
main.py'de birakildi - .github/workflows/build-apk.yml, derleme oncesi
main.py DOSYASININ ICERIGINDE "__BUILD_STAMP__" arayip yerine gercek
commit/zaman damgasini yaziyor (sed -i main.py); o script'in main.py
disinda baska bir dosyaya bakmasi gerekmiyor, o yuzden BUILD_STAMP tanimi
main.py'de kalmali. get_data_path() de main.py'nin kendi TonajApp/
_CrashSaveHandler'i disinda kullanilmadigi icin orada birakildi (ayrica
tests/smoke_test.py main.get_data_path'i doğrudan monkeypatch'liyor -
tanim main.py'de olmayi surdurdukce bu calismaya devam eder).
"""
import os
import re
from kivy.core.text import LabelBase

_FONT_DIR = os.path.dirname(os.path.abspath(__file__))


def _f(name):
    return os.path.join(_FONT_DIR, name)


# Orijinal web uygulamasinin tipografi kimligi: Oswald (baslik/wordmark),
# Inter (govde metni), Space Mono (rakam/veri). Ucu de Turkce karakterleri
# (ğ ş ı İ ö ü ç) tam destekliyor - kaydetmeden once dogrulandi.
# 'Roboto' Kivy'nin TUM widget'larinin varsayilan font adi oldugu icin, onu
# Inter'e cevirmek butun uygulamayi tek satirla Inter'e gecirir.
LabelBase.register(name="Roboto", fn_regular=_f("Inter-Regular.ttf"), fn_bold=_f("Inter-SemiBold.ttf"))
LabelBase.register(name="Oswald", fn_regular=_f("Oswald-Bold.ttf"), fn_bold=_f("Oswald-Bold.ttf"))
LabelBase.register(name="SpaceMono", fn_regular=_f("SpaceMono-Regular.ttf"), fn_bold=_f("SpaceMono-Bold.ttf"))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.metrics import dp
from kivy.clock import Clock

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


def confirm_dialog(title, message, on_confirm, confirm_text="Evet, Sil"):
    """Yikici (geri alinamaz ya da riskli) bir islem oncesi standart
    "Evet/Vazgeç" onay popup'i.

    KOK NEDEN (kod incelemesinde bulundu - "6 adet neredeyse birebir kopya
    onay diyaloğu"): confirm_delete_day, confirm_discard_session,
    confirm_remove_exercise, confirm_delete_session, confirm_reset_all,
    confirm_import_backup fonksiyonlarinin HER BIRI ayni ~15 satirlik
    popup/buton iskeletini (content olustur, "Evet"/"Vazgeç" butonlari,
    fit_popup_to_content, popup.open) kendi icinde ayri ayri kopyalayip
    sadece baslik/mesaj/yapilacak-islemi degistiriyordu - bir davranis
    degisikligi (orn. buton rengi, animasyon ayari) gerektiginde 6 yerde
    ayri ayri yapilmak zorundaydi, biri unutulursa tutarsizlik olusurdu
    (nitekim "Vazgeç" butonlari animasyonsuz degildi, digerleri
    animasyonsuzdu - bkz. asagidaki animation=False notu).

    DUZELTME: ortak iskelet TEK bir yerde - on_confirm SADECE gercek islemi
    (state degisikligi + save + render) yapar, popup'i kapatmak bu
    fonksiyonun sorumlulugundadir.
    """
    content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12), size_hint_y=None)
    content.bind(minimum_height=content.setter("height"))
    content.add_widget(label(message))
    row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    popup = Popup(title=title, content=content, size_hint=(0.85, None))
    fit_popup_to_content(popup, content)

    def do_confirm(*_a):
        # animation=False: dosyadaki diger popup dismiss/open cagrilariyla
        # tutarli olmasi icin (bkz. _build_exercise_picker/open_target_editor
        # icindeki KOK NEDEN notlari - kayma hatasinin asil sebebi buydu).
        popup.dismiss(animation=False)
        on_confirm()

    def do_cancel(*_a):
        popup.dismiss(animation=False)

    yes = styled_button(confirm_text, color=DANGER, text_color=(1, 1, 1, 1))
    no = styled_button("Vazgeç", color=RAISED, text_color=TEXT)
    yes.bind(on_release=do_confirm)
    no.bind(on_release=do_cancel)
    row.add_widget(no); row.add_widget(yes)
    content.add_widget(row)
    popup.open(animation=False)
    return popup


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


class _PickerRow(RecycleDataViewBehavior, Button):
    """Hareket secici (screens/program.py: _build_exercise_picker, Task 17)
    icin RecycleView satir gorunumu.

    KOK NEDEN / DUZELTME (bkz. _build_exercise_picker basindaki KOK NEDEN
    notu): eski kod, arama/filtre her degistiginde eslesen HER hareket icin
    (217'ye kadar) ayri bir Button nesnesi olusturuyordu. RecycleView bunun
    yerine bu sinifin SINIRLI sayida (yalnizca o an EKRANDA GORUNEN + kucuk
    bir tampon kadar) ornegini olusturup kaydirma sirasinda AYNI ornaklari
    YENIDEN KULLANIR (sadece .text ve tiklama geri cagirimini degistirir) -
    217 satirin tamami icin degil, gorunen ~10-15 satir icin widget kurulur.

    Gorunum/stil (RAISED zemin, TEXT renk, dp(38) yukseklik, Button'in
    varsayilan fontu) RecycleView-ONCESI koddaki satir Button'i ile BIREBIR
    AYNI - degisen sadece somutlastirma stratejisi, davranis/gorunum degil.
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = RAISED
        self.color = TEXT
        self.size_hint_y = None
        self.height = dp(38)
        self._pick_cb = None

    def refresh_view_attrs(self, rv, index, data):
        # NOT: data'daki 'on_release' anahtarini KASITLI olarak super()'a
        # AKTARMIYORUZ - o gercek bir Kivy ozelligi degil (Button'da bir
        # EVENT), RecycleDataViewBehavior'un varsayilan otomatik-setattr
        # mekanizmasina verilirse hataya yol acar. Callback'i kendimiz
        # saklayip asagidaki on_release()'te elle cagiriyoruz.
        self._pick_cb = data.get("on_release")
        self.text = data.get("text", "")
        return super().refresh_view_attrs(rv, index, {})

    def on_release(self):
        if self._pick_cb is not None:
            self._pick_cb()


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


def _find_scrollview(widget):
    if isinstance(widget, ScrollView):
        return widget
    for c in widget.children:
        found = _find_scrollview(c)
        if found is not None:
            return found
    return None
