"""
python-for-android build hook.

GECMIS (TERK EDILEN) YAKLASIM: Once bu hook AndroidManifest.xml'e
android:windowSoftInputMode="adjustResize" ekliyordu, cunku p4a'nin "_sdl_common"
bootstrap sablonu bu ozniteligi hic koymuyor (klavye acilinca pencere hic
native olarak kucalmiyordu - kod dogrulandi) ve bu da hem "klavyenin icerigi
kapatmasi" hem de "alanlar arasi kayma" sikayetlerine yol aciyordu.

adjustResize kismen ise yaradi ama video kare-kare analizinde YENI ve DAHA
KOTU bir sorun ortaya cikardi: adjustResize, klavye her acilip kapandiginda
Android'e pencerenin GERCEK GL yuzeyini (SurfaceView) yeniden boyutlandirmasini
- yani onu yikip yeniden olusturmasini - soyluyor. Bu cihazda bu yeniden-olusturma
sirasinda birkac kare boyunca ekran tamamen SIYAH kaliyordu (once beyaz kaliyordu,
windowBackground duzeltmesinden sonra siyaha dondu ama sorunun kendisi - yuzeyin
bosalmasi - devam etti). Bu main.py tarafindan cozulebilecek bir sey degildi -
native yuzey yasam donguesunun kendisiydi.

YENI COZUM: adjustResize yerine android:windowSoftInputMode="adjustPan"
ekliyoruz. main.py da artik Kivy'nin SDL2/Android icin resmi olarak destekledigi
Window.softinput_mode = "below_target" moduna gecti (bkz. main.py TonajApp.build).
Bu kombinasyonda Android pencereyi/yuzeyi HICBIR ZAMAN yeniden boyutlandirmiyor -
sadece odaklanmis TextInput'un GERCEK ekran konumu Kivy tarafindan bildirilip
(SDL_SetTextInputRect - below_target modu) butun ekran GORSEL olarak o alan
gorunur kalacak kadar kaydiriliyor (pan). Yuzey hic yikilmadigi/yeniden
kurulmadigi icin o "siyah flash" / kayma artik olusmuyor.
"""
import os
import re

ACTIVITY_CLASS = "org.kivy.android.PythonActivity"
_ATTR = 'android:windowSoftInputMode="adjustPan"'

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
        print(f"[hook.py] {path}: windowSoftInputMode=\"adjustPan\" eklendi.")
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
