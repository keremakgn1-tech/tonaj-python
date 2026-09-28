[app]
title = Tonaj
package.name = tonaj
package.domain = com.github.keremakgn1tech
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0

# python3 versiyonu BILEREK 3.11.9'a sabitlendi (once bos birakilmisti - bu
# durumda python-for-android varsayilan olarak en YENI Python surumunu
# (derleme sirasinda 3.14.2) kullaniyordu). Kivy 2.3.1 Subat 2024'te
# yayinlandi, Python 3.14 ise Ekim 2025'te - yani Kivy bu Python surumuyle
# HICBIR ZAMAN test edilmedi. Klavyeden yazi girisinin TextInput'a hic
# ulasmamasi + arka plana alip geri donunce uygulamanin tamamen siyah ekranda
# donup kalmasi gibi dusuk seviyeli (native/Cython) garip davranislar, tam
# olarak boyle bir ABI/surum uyumsuzlugunda beklenecek turden sorunlar.
# 3.11.9, Kivy ekosisteminde en genis test edilmis ve buildozer belgelerinde
# onerilen surumlerden biri - bu yuzden sectik.
requirements = python3==3.11.9,charset_normalizer==3.3.2,kivy==2.3.1

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

# Uygulama acilirken (Python/Kivy daha yuklenmeden once) p4a'nin gosterdigi
# "loading" ekrani - ozellestirilmezse varsayilan Kivy kus logosu +
# "Loading..." yazisi gorunuyordu (kullanicinin ekran goruntusunde gorulen
# ekran budur). presplash.png, uygulamanin kendi ikonu + "TONAJ" + "Yükleniyor..."
# ile bu varsayilani degistiriyor; presplash_color da arka planin uygulamanin
# kendi koyu temasiyla (main.py'daki BG = #121316) birebir eslesmesini saglayip
# kenarlarda/gecislerde renk uyumsuzlugu kalmamasini sagliyor.
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #121316

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
