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


def after_apk_build(toolchain):
    # Bu asamada calisma dizini dist_dir'dir (p4a bunu boyle cagirir).
    _patch(os.path.join("src", "main", "AndroidManifest.xml"))
    _patch("AndroidManifest.xml")
