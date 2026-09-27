"""
python-for-android build hook.

KOK NEDEN: Tonaj gibi duz Kivy uygulamalari icin p4a'nin kullandigi "_sdl_common"
bootstrap sablonu (AndroidManifest.tmpl.xml) ana activity icin HICBIR ZAMAN
android:windowSoftInputMode ayari koymuyor (bu sadece "webview" bootstrap'inda
var, biz onu kullanmiyoruz - p4a'nin kendi kaynak kodundan dogrulandi). Yani
uygulamamizda klavye acilinca pencerenin "adjustResize" ile kucalup buyudugunu
varsaymak YANLISTI - hicbir native yeniden boyutlandirma hic olmuyordu. Bu da
tam olarak sikayet edilen iki soruna denk dusuyor:
  1) Klavyenin arkasinda kalan alanlarin gorunmemesi (pencere hic kucalmiyor)
  2) Alanlar arasi geciste "sacma" bir kayma/zipla(ma) (Kivy'nin kendi ScrollView
     kaydirmasi, hicbir native boyut degisikligi olmadan tek basina calisiyor,
     ki bu tutarsiz/yamali bir his veriyor)

COZUM: p4a'nin resmi "--hook" mekanizmasini (buildozer.spec'te p4a.hook = hook.py)
kullanarak, APK derlenirken uretilen AndroidManifest.xml'e ana activity icin
android:windowSoftInputMode="adjustResize" ozniteligini elle ekliyoruz. Bu,
Android'in klavye acilinca pencereyi GERCEKTEN kucaltmasini saglar; main.py
tarafindaki ScrollView otomatik kaydirma kodu da bu gercek (native) boyut
degisikligiyle artik tutarli calisir.
"""
import os
import re

ACTIVITY_CLASS = "org.kivy.android.PythonActivity"
_ATTR = 'android:windowSoftInputMode="adjustResize"'

_PATTERN = re.compile(
    r'(<activity\s+android:name="%s"[^>]*)(>)' % re.escape(ACTIVITY_CLASS)
)


def _patch(path):
    if not os.path.exists(path):
        print(f"[hook.py] Atlaniyor (bulunamadi): {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        xml = f.read()
    if "windowSoftInputMode" in xml:
        print(f"[hook.py] {path} zaten windowSoftInputMode iceriyor, dokunulmadi.")
        return

    def _add_attr(m):
        return m.group(1) + "\n                  " + _ATTR + m.group(2)

    new_xml, count = _PATTERN.subn(_add_attr, xml, count=1)
    if count:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_xml)
        print(f"[hook.py] {path}: windowSoftInputMode=\"adjustResize\" eklendi.")
    else:
        print(f"[hook.py] UYARI: {path} icinde ana activity etiketi eslesmedi, "
              f"windowSoftInputMode eklenemedi.")


# ---------------------------------------------------------------------------
# KOK NEDEN 2 (videolarda yakalanan "beyaz flash"): p4a'nin _sdl_common
# sablonundaki ANA ACTIVITY, buildozer.spec'teki android.apptheme DEGIL,
# HER ZAMAN sabit "@style/KivySupportCutout" temasini kullanir (bkz.
# AndroidManifest.tmpl.xml - <application> tag'i android_apptheme'i kullanir
# ama asil <activity> etiketi bunu GORMEZDEN GELIP kendi "KivySupportCutout"
# temasini kullanir). Bu "KivySupportCutout" stili (strings.tmpl.xml'de
# tanimli) HICBIR temadan miras almaz ve "windowBackground" tanimlamaz - yani
# arka plan rengi tamamen Android'in/cihazin KENDI varsayilan temasina
# kaliyor, ki bircok cihazda/Android surumunde bu ACIK/BEYAZ oluyor. Klavye
# acilinca pencere yeniden boyutlanirken (adjustResize), Kivy yeni kareyi
# cizene kadar bir an icin iste bu (bizim kontrolumuz DISINDAKI) acik renkli
# varsayilan arka plan gorunuyor - kullanicinin videolarda gordugu beyaz
# "flash" tam olarak budur; scroll/kaydirma ile ilgisi yoktur.
#
# COZUM: Uretilen res/values/strings.xml icindeki KivySupportCutout stiline
# uygulamamizin KENDI koyu arka plan rengini (main.py'daki BG = #121316)
# elle "android:windowBackground" olarak ekliyoruz. Boylece o gecis aninda
# gorunen "bosluk" da koyu oluyor, beyaz flash ortadan kalkiyor.
# ---------------------------------------------------------------------------
_APP_BG_HEX = "#FF121316"  # main.py'daki BG = (0x12,0x13,0x16) + tam opak alfa
_STYLE_PATTERN = re.compile(r'(<style\s+name="KivySupportCutout"\s*>)')
_BG_ITEM = f'<item name="android:windowBackground">{_APP_BG_HEX}</item>'


def _patch_style(path):
    if not os.path.exists(path):
        print(f"[hook.py] Atlaniyor (bulunamadi): {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        xml = f.read()
    if "windowBackground" in xml:
        print(f"[hook.py] {path} zaten windowBackground iceriyor, dokunulmadi.")
        return

    def _add_item(m):
        return m.group(1) + "\n        " + _BG_ITEM

    new_xml, count = _STYLE_PATTERN.subn(_add_item, xml, count=1)
    if count:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_xml)
        print(f"[hook.py] {path}: windowBackground={_APP_BG_HEX} eklendi "
              f"(beyaz resize flash duzeltmesi).")
    else:
        print(f"[hook.py] UYARI: {path} icinde KivySupportCutout stili "
              f"eslesmedi, windowBackground eklenemedi.")


def after_apk_build(toolchain):
    # Bu asamada calisma dizini dist_dir'dir (p4a bunu boyle cagirir).
    _patch(os.path.join("src", "main", "AndroidManifest.xml"))
    _patch("AndroidManifest.xml")
    _patch_style(os.path.join("src", "main", "res", "values", "strings.xml"))
