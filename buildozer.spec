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

# p4a'nin Kivy (sdl2) bootstrap'i AndroidManifest'e windowSoftInputMode HIC
# eklemiyor (bu sadece webview bootstrap'inde var) - yani klavye acilinca
# pencere native olarak hicbir zaman "adjustResize" ile kucalmiyordu. Bu hook
# derleme sirasinda uretilen manifest'i yamayip bu ozelligi ekliyor - klavye
# kasma/kayma sorunlarinin gercek kok nedeni buydu. Detay icin hook.py'a bak.
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
