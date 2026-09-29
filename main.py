"""
TONAJ - Antrenman Takibi (Kivy / Android)
main.py, uygulamanin GIRIS noktasi: App/RootWidget "bootstrap"unu barindirir
(pencere/tema kurulumu, ekranlar arasi navigasyon, kaydetme/kurtarma,
cokme korumasi). Ekranlarin kendisi (Program/Gecmis/Hareketler/Rapor/
Ayarlar) screens/ paketinde, hepsinin ortak kullandigi kucuk widget
fabrikalari + renk sabitleri shared.py'de yasiyor.

KOK NEDEN (Task 18 - kod incelemesinde bulundu): bu dosya ONCEDEN TUM
uygulamayi (butun ekranlar + bootstrap) tek basina ~2000 satirda
tutuyordu - bkz. shared.py basindaki ayrintili KOK NEDEN/DUZELTME notu.
Bu SAF bir tasima (main.py + core.py'deki Model/Logic fonksiyonlarina
baglanma bicimi dahil davranis HICBIR sekilde degismedi).
"""
import os
import json
import threading

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.base import ExceptionHandler, ExceptionManager

import core
from shared import BG, CARD, BORDER, MUTED, ACCENT, bg_rect, sp_, ClickableRow, toast
from screens.program import ProgramScreen
from screens.history import HistoryScreen
from screens.library import LibraryScreen
from screens.report import ReportScreen
from screens.settings import SettingsScreen

# NOT: buildozer.spec'teki "version" ile ELLE senkron tutulmali (Ayarlar >
# Hakkinda bolumunde gosteriliyor) - APK derlenirken otomatik okunmuyor,
# cunku .spec dosyasi APK'nin icine gomulmuyor (source.include_exts'te yok).
APP_VERSION = "1.0"

# BUILD_STAMP: her APK'nin HANGI koddan derlendigini Ayarlar > Hakkinda'da
# gorunur kilmak icin. KOK NEDEN: APP_VERSION hicbir zaman degismiyordu -
# yani art arda derlenen COK FARKLI APK'lar bile telefonda hep ayni "sürüm
# 1.0" yazisini gosteriyordu; kullanicinin (ve bizim) o an telefonda GERCEKTEN
# hangi duzeltmenin kurulu oldugunu dogrulamanin hicbir yolu yoktu. Bu satir,
# GitHub Actions is akisinda (.github/workflows/build-apk.yml) derlemeden
# HEMEN once gercek git commit kisa hash'i + UTC derleme zamaniyla
# DEGISTIRILIYOR (bkz. o dosyadaki "Build stamp'i main.py'ye gom" adimi).
# Burada duz calistirilirsa (ör. bu ortamda test ederken) placeholder olarak
# kalir - zararsizdir, sadece Ayarlar ekraninda "dev" gorunur.
#
# NOT (Task 18 - bu satir main.py'de KALDI): o CI adimi main.py DOSYASININ
# ICERIGINDE "__BUILD_STAMP__" arayip yerine yaziyor (sed -i main.py) - bu
# yuzden tanim bilerek burada birakildi, screens/settings.py bu degeri
# main.py'yi geri import ETMEDEN (dairesel import'tan kacinmak icin)
# App ornegi uzerinden (app.build_stamp - bkz. TonajApp.build()) okuyor.
BUILD_STAMP = "__BUILD_STAMP__"


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

        self._toast_queue = []
        self.toast_label = Label(text="", size_hint=(None, None), size=(dp(280), dp(44)),
                                  pos_hint={"center_x": 0.5, "top": 0.97},
                                  opacity=0, halign="center", valign="middle",
                                  font_name="Oswald", bold=True,
                                  color=(0.07, 0.08, 0.06, 1))
        self.toast_label.bind(size=lambda *_: setattr(self.toast_label, "text_size", self.toast_label.size))
        bg_rect(self.toast_label, ACCENT, radius=dp(8))
        self.add_widget(self.toast_label)

        # KOK NEDEN (kod incelemesinde bulundu - "donanim geri tusu hic ele
        # alinmamis"): Android'in fiziksel/gesture geri tusu ONCEDEN hicbir
        # yerde yakalanmiyordu - Kivy'nin varsayilan davranisi, acik bir
        # Popup YOKSA geri tusunu dogrudan UYGULAMAYI KAPATMAK icin kullanir.
        # Yani kullanici Gecmis/Hareketler/Rapor/Ayarlar sekmelerinden
        # herhangi birindeyken (ozellikle aktif bir antrenman surerken) yanlis
        # bir geri tusuna basmasi uygulamayi beklenmedik sekilde kapatiyordu.
        # (Acik bir Popup varken bu sorun yok - Kivy'nin kendi ModalView'i
        # escape/geri tusunu zaten yakalayip SADECE popup'i kapatiyor, buraya
        # hic ulasmiyor.)
        #
        # DUZELTME: "program" DISINDA bir sekmedeyken geri tusuna basilinca
        # once "program" sekmesine donuyoruz (tuketiliyor, uygulama KAPANMIYOR);
        # kullanici zaten "program" sekmesindeyken basarsa bu davranisi
        # degistirmiyoruz - Android'in standart "uygulamadan cik" davranisi
        # oradan calismaya devam ediyor.
        Window.bind(on_keyboard=self._on_keyboard)

    def _on_keyboard(self, window, key, *args):
        if key == 27:  # Android geri tusu / masaustunde Esc
            if self.sm.current != "program":
                self.sm.current = "program"
                return True  # tuketildi - uygulamadan CIKILMASIN
        return False

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
        # KOK NEDEN (kod incelemesinde bulundu - "toast bildirimleri
        # kuyruklanmiyor"): ONCEDEN bir toast gosterilirken (orn. "YENİ
        # REKOR — PR!") hemen ardindan bir baskasi (orn. baska bir hareketle
        # art arda gelen ikinci bir PR) gelirse, ikincisi birincinin
        # SUResini/metnini dogrudan USTUNE YAZIYORDU - kullanici ilk
        # bildirimi hic goremeden kaybediyordu. Simdi mesajlar bir kuyrukta
        # birikip SIRAYLA, her biri kendi suresi kadar gorunecek sekilde
        # gosteriliyor.
        self._toast_queue.append(msg)
        if len(self._toast_queue) == 1:
            self._show_next_toast()

    def _show_next_toast(self, *_):
        if not self._toast_queue:
            return
        self.toast_label.text = self._toast_queue[0]
        self.toast_label.opacity = 1
        Clock.schedule_once(self._advance_toast_queue, 1.6)

    def _advance_toast_queue(self, *_):
        self.toast_label.opacity = 0
        if self._toast_queue:
            self._toast_queue.pop(0)
        if self._toast_queue:
            # Bir sonraki mesaja gecmeden once kisa bir bosluk - ust uste
            # iki toast'in ayni anda/kesintisiz gorunmesini (bir onceki
            # solma animasyonuyla cakismasini) onler.
            Clock.schedule_once(self._show_next_toast, 0.3)


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
        # Ayarlar > Hakkinda bolumunun (screens/settings.py) main.py'yi geri
        # import ETMEDEN surum/build bilgisine erisebilmesi icin - bkz.
        # BUILD_STAMP tanimindaki Task 18 notu.
        self.app_version = APP_VERSION
        self.build_stamp = BUILD_STAMP
        # Klavye: uygulamada artik HICBIR yerde TextInput/klavye kullanilmiyor
        # (bkz. make_stepper() tanimindaki not) - butun sayisal degerler +/-
        # sayaciyla giriliyor. Bu yuzden Window.softinput_mode ayarlamaya ya
        # da klavye acilis/kapanisini yonetmeye hic gerek kalmadi; manifest'te
        # android:windowSoftInputMode="adjustResize" (bkz. hook.py) sadece
        # Android'in standart/varsayilan davranisi olarak duruyor.
        self.state, _is_new, recovered_from_corruption = core.load_state(get_data_path())
        self._save_pending = None
        self.root_widget = RootWidget()
        if recovered_from_corruption:
            # KOK NEDEN: kayit dosyasi okunamadi (bkz. core.load_state
            # icindeki not) - sifirdan bos bir state ile basladik. Bunu
            # kullaniciya SESSIZCE yapmak yerine, en azindan neden butun
            # programinin/gecmisinin bos gorundugunu anlayabilsin diye
            # bir toast gosteriyoruz. root_widget henuz ekrana tam
            # yerlesmeden show_toast cagirmak sorunlu olabilecegi icin
            # bir kare erteliyoruz.
            Clock.schedule_once(
                lambda *_: toast(self, "Önceki veri okunamadı, sıfırdan başlandı"), 0)
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
        # KOK NEDEN (kod incelemesinde bulundu - "arka plan yazma thread'i
        # hatasiz"): _write_json_string_to_file bu thread icinde HERHANGI
        # bir hata (disk dolu, izin hatasi, depolama kesintisi) firlatirsa,
        # bu ONCEDEN sessizce (sadece stderr'e giden bir traceback ile)
        # yutuluyordu - kullanici en son yaptigi degisikligin (yeni set,
        # kaydedilen hedef vb.) diske YAZILMADIGINI hic fark edemiyordu.
        # DUZELTME: yazmayi try/except ile sariyoruz; basarisiz olursa ana
        # thread'e donup (Clock.schedule_once thread-safe'tir) kullaniciya
        # aciklayici bir toast gosteriyoruz.
        def write_and_report():
            try:
                _write_json_string_to_file(path, payload)
            except Exception as e:
                print(f"[tonaj] UYARI: diske yazma basarisiz: {e!r}")
                Clock.schedule_once(
                    lambda *_: toast(self, "Kaydetme başarısız oldu — tekrar dene"), 0)

        threading.Thread(target=write_and_report, daemon=True).start()

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
