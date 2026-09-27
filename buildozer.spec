[app]
title = Tonaj
package.name = tonaj
package.domain = com.github.keremakgn1tech
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0

requirements = python3,charset_normalizer==3.3.2,kivy==2.3.1

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

# NOT: android.apptheme normalde <application> etiketinin temasini belirler,
# AMA p4a'nin _sdl_common sablonunda asil <activity> (PythonActivity) bunu
# GORMEZDEN GELIP kendi sabit "@style/KivySupportCutout" temasini kullanir -
# yani bu ayar tek basina yeterli DEGIL. Videolarda yakalanan "beyaz flash"in
# gercek duzeltmesi hook.py'da (KivySupportCutout stiline elle
# android:windowBackground eklemek) - detay icin hook.py'a bak. Bu satiri
# yine de <application> seviyesindeki olasi diger pencereler icin bir ek
# guvenlik onlemi olarak birakiyoruz.
android.apptheme = @android:style/Theme.Black.NoTitleBar

# p4a'nin Kivy (sdl2) bootstrap'i AndroidManifest'e windowSoftInputMode HIC
# eklemiyor (bu sadece webview bootstrap'inde var). Bu hook derleme sirasinda
# uretilen manifest'i yamayip android:windowSoftInputMode="adjustPan" ekliyor.
# (ONCEKI SURUM "adjustResize" ekliyordu - bu, video kare-kare analiziyle
# dogrulanan birkac karelik SIYAH EKRAN/kaymaya sebep oluyordu, cunku Android'in
# pencere/GL yuzeyini gercekten yeniden olusturmasini tetikliyordu. "adjustPan"
# + main.py'daki Window.softinput_mode = "below_target" kombinasyonu, yuzeyi
# hic yikmadan sadece gorsel olarak kaydiriyor - detay icin hook.py'a bak.)
p4a.hook = %(source.dir)s/hook.py

android.permissions = INTERNET
android.api = 34
android.minapi = 24
android.ndk_api = 24
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
