"""
TONAJ - Ayarlar ekrani (Task 18 refactor: main.py'den ayrildi).

Birim sistemi (kg/lb), yedekleme (disa aktar/geri yukle), tum verileri
sifirlama ve "Hakkinda" (surum/build damgasi) bolumlerini barindirir.
Davranis main.py'deki halinden HICBIR sekilde degismedi - bu SAF bir
tasima (bkz. shared.py basindaki Task 18 notu).

NOT (APP_VERSION/BUILD_STAMP): main.py'de TANIMLI KALDILAR (bkz. o
dosyadaki/CI is akisindaki KOK NEDEN notu - sed script'i main.py
icerigini arar) - TonajApp.build() bunlari app.app_version/
app.build_stamp olarak App ornegine ISLIYOR, bu ekran de degerleri
buradan (app uzerinden) okuyor - main.py'yi buraya import ETMEDEN
(dairesel import'tan kacinmak icin main.py bu modulu ICE ALDIGI icin
bu modul main.py'yi geri import edemez).
"""
import os
import json
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform

import core
from shared import (
    RAISED, TEXT, MUTED, FAINT, ACCENT_DARK, ACCENT, DANGER,
    weight_unit, font_scale, FONT_SCALE_CHOICES,
    confirm_dialog, styled_button, label, toast, dp,
)


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

        # ---- Yazi tipi boyutu ----
        # KOK NEDEN (kullanicidan gelen istek - Task 21): uygulamadaki tum
        # yazi boyutlari sabitti, kucuk ekranli/gorme guclugu olan
        # kullanicilar icin ayarlanamiyordu. sp_() artik shared.font_scale()
        # ile carpiliyor (bkz. o fonksiyondaki not) - burada SADECE bu
        # olcegi secip app.state["settings"]["fontScale"]'a yaziyoruz.
        col.add_widget(self.section_header("YAZI TİPİ BOYUTU"))
        cur_scale = font_scale()

        def set_font_scale(v, *_):
            app.state.setdefault("settings", {})["fontScale"] = v
            app.save()
            self.render()

        scale_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        for name, val in FONT_SCALE_CHOICES:
            is_cur = abs(val - cur_scale) < 0.001
            btn = styled_button(name, color=ACCENT if is_cur else RAISED,
                                 text_color=ACCENT_DARK if is_cur else TEXT)
            btn.bind(on_release=lambda *_, v=val: set_font_scale(v))
            scale_row.add_widget(btn)
        col.add_widget(scale_row)
        col.add_widget(label(
            "Uygulamadaki tüm yazıların boyutunu değiştirir. Değişiklik "
            "diğer ekranlara bir sonraki girişinde yansır.",
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
        col.add_widget(label(f"Tonaj — sürüm {app.app_version}", color=FAINT, size=14, height=dp(22)))
        # Hangi APK'nin telefonda kurulu oldugunu (hangi commit'ten, ne zaman
        # derlendigini) dogrulamak icin - bkz. BUILD_STAMP tanimindaki not.
        col.add_widget(label(f"Build: {app.build_stamp}", color=FAINT, size=12, height=dp(20)))
        col.add_widget(label("Verilerin bu cihazda kalıcı olarak saklanıyor.", color=FAINT, size=14, height=dp(22)))

        scroll.add_widget(col)
        self.add_widget(scroll)

    def confirm_reset_all(self):
        app = App.get_running_app()

        def on_confirm():
            app.state = core.default_state()
            app.save()
            self.render()
            toast(app, "Tüm veriler sıfırlandı")

        confirm_dialog(
            "Tüm Verileri Sıfırla",
            "TÜM programın, antrenman geçmişin ve ayarların KALICI olarak "
            "silinecek. Bu işlem GERİ ALINAMAZ. Devam etmeden önce yedek "
            "almanı öneririz.",
            on_confirm, confirm_text="Evet, Sıfırla")

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
        confirm_dialog(
            "Yedekten Geri Yükle",
            "Bir yedek dosyası seçeceksin. Seçtiğin dosyadaki veri, bu "
            "cihazdaki TÜM mevcut programın/geçmişin/kayıtların YERİNE "
            "geçecek. Bu işlem geri alınamaz. Devam edilsin mi?",
            self.import_backup, confirm_text="Devam Et")

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
                    # KOK NEDEN (kod incelemesinde bulundu - "ice aktarilan
                    # yedegin ic yapisi dogrulanmiyor"): burada ONCEDEN
                    # SADECE 4 ust-seviye anahtarin VAR OLUP OLMADIGINA
                    # bakiliyordu - ic yapi (orn. her set'teki weight/reps
                    # alanlarinin sayisal olmasi) hic kontrol edilmiyordu.
                    # Bozuk/elle duzenlenmis bir yedek boylece "gecerli"
                    # kabul edilip app.state'e atanabiliyor, SONRA
                    # session_tonnage gibi fonksiyonlarda anlasilmaz bir
                    # cokmeye yol aciyordu. core.validate_state_schema artik
                    # bunu daha kapsamli kontrol edip aciklayici bir
                    # ValueError firlatiyor (asagidaki except tarafindan
                    # yakalanip kullaniciya Turkce gosteriliyor).
                    core.validate_state_schema(new_state)

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
