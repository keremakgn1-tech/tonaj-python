[app]
title = Tonaj
package.name = tonaj
package.domain = com.github.keremakgn1tech
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

requirements = python3,charset_normalizer==3.3.2,kivy==2.3.1

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

android.permissions = INTERNET
android.api = 34
android.minapi = 24
android.ndk_api = 24
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
