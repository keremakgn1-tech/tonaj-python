"""
TONAJ - Program ekrani (Task 18 refactor: main.py'den ayrildi).

Kullaniciyi programini goruntuleyip duzenlemesine, gunlere hareket
ekleyip hedef belirlemesine ve antrenman oturumu baslatip
canli olarak set islemesine izin veren ekran. Davranis main.py'deki
halinden HICBIR sekilde degismedi - bu SAF bir tasima (bkz. shared.py
basindaki Task 18 notu).
"""
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, Rectangle, Line
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout

import core
from shared import (
    RAISED, BORDER, DIVIDER, TEXT, MUTED, FAINT, ACCENT_DARK, ACCENT, DANGER, STEEL,
    TRANSPARENT, ICON_BTN_SIZE,
    weight_unit, to_display_weight, to_storage_kg, fmt_weight,
    bg_rect, fit_popup_to_content, confirm_dialog, Card, styled_button, label, sp_,
    make_stepper, mono_label, ClickableRow, _PickerRow, parse_day_name, tr_upper,
    toast, target_label, _find_scrollview, exercise_search_input, note_input,
)


SUGGEST_TEXT = {
    "ceiling": "geçen sefer tüm setlerde tavana ulaştın, ağırlık artırma zamanı",
    "ceiling-bw": "geçen sefer hedefi tuttun, bu sefer tekrar sayısını artırmayı dene",
    "below": "aynı ağırlık — geçen sefer bazı setler hedefin altında kaldı",
    "inrange": "aynı ağırlık — bu sefer aralığın tavanına ulaşmaya çalış",
}


class ProgramScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        # Antrenmana baslamadan once programa goz atarken (ozellikle telefonu
        # elinde tutarken/hareket halindeyken) sira degistirme/kopyalama/
        # hareket silme gibi YIKICI butonlar HER ZAMAN acik ve tek dokunusla
        # aninda uygulaniyordu - yanlislikla dokunmak programi bozabiliyordu.
        # Simdi varsayilan GORUNUM salt-okunur: sadece gun/hareket/hedef bilgisi
        # + BASLA gorunuyor. Bu duzenleme butonlari SADECE kullanici acikca
        # "Düzenle" moduna gecince ortaya cikiyor (bkz. render_planner/day_card).
        self.edit_mode = False

    def on_pre_enter(self):
        self.render()

    def render(self, keep_scroll=False):
        app = App.get_running_app()
        state = app.state
        prev = _find_scrollview(self)
        prev_scroll_y = prev.scroll_y if (keep_scroll and prev is not None) else None
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")

        if state["activeSession"]:
            root.add_widget(self.render_active_session(state))
        else:
            root.add_widget(self.render_planner(state))
        self.add_widget(root)

        if prev_scroll_y is not None:
            new_scroll = _find_scrollview(self)
            if new_scroll is not None:
                def restore(*_):
                    new_scroll.scroll_y = prev_scroll_y
                Clock.schedule_once(restore, 0)

    # ---- Planlayici (gun listesi) ----
    def render_planner(self, state):
        app = App.get_running_app()
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))

        # Duzenleme kilidi acma/kapama butonu - bkz. __init__'teki not.
        top_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        top_row.add_widget(label("PROGRAM", size=14, bold=True, color=MUTED, height=dp(40)))
        top_row.add_widget(BoxLayout())
        edit_btn = styled_button("Bitti" if self.edit_mode else "Düzenle",
                                  color=ACCENT if self.edit_mode else RAISED,
                                  text_color=ACCENT_DARK if self.edit_mode else TEXT,
                                  size_hint=(None, None), size=(dp(110), dp(36)))
        def toggle_edit(*_):
            self.edit_mode = not self.edit_mode
            self.render()
        edit_btn.bind(on_release=toggle_edit)
        top_row.add_widget(edit_btn)
        col.add_widget(top_row)

        if not state["program"]["days"]:
            msg = ("Program tanımlı değil. Düzenle moduna geçip gün ekle."
                   if not self.edit_mode else "Program tanımlı değil. Aşağıdan gün ekle.")
            col.add_widget(label(msg, color=MUTED, height=dp(60)))

        next_id = core.next_suggested_day_id(state)
        for day in state["program"]["days"]:
            col.add_widget(self.day_card(state, day, is_next=(day["id"] == next_id), editable=self.edit_mode))

        if self.edit_mode:
            add_btn = styled_button("+ GÜN EKLE", color=RAISED, text_color=TEXT)
            add_btn.bind(on_release=lambda *_: (core.add_program_day(state), app.save(), self.render(keep_scroll=True)))
            col.add_widget(add_btn)

        free_btn = styled_button("Serbest Antrenman Başlat", color=RAISED, text_color=TEXT)
        free_btn.bind(on_release=lambda *_: self.start_session(None))
        col.add_widget(free_btn)

        scroll.add_widget(col)
        return scroll

    def day_card(self, state, day, is_next, editable):
        app = App.get_running_app()
        card = Card(size_hint_y=None, spacing=dp(4))
        card.bind(minimum_height=card.setter("height"))
        # Sol kenarda ince vurgu seridi (SIRADA gunlerde limon, digerlerinde sessiz)
        stripe_color = ACCENT if is_next else BORDER
        with card.canvas.after:
            Color(*stripe_color)
            stripe = Rectangle(pos=card.pos, size=(dp(3), card.height))
        def _upd_stripe(*_):
            stripe.pos = card.pos
            stripe.size = (dp(3), card.height)
        card.bind(pos=_upd_stripe, size=_upd_stripe)

        ordinal, headline, meta = parse_day_name(day["name"])

        # Yukseklik ICON_BTN_SIZE (dp32) - asagidaki up/down/delete ikon
        # butonlari bu asgari dokunma hedefine buyutuldugu icin satir da
        # onlara sigacak kadar yuksek olmali (Task 19).
        eyebrow = BoxLayout(size_hint_y=None, height=ICON_BTN_SIZE, spacing=dp(8))
        if ordinal:
            eyebrow.add_widget(mono_label(ordinal, size=14, color=MUTED, width=dp(24)))
        if is_next:
            sirada = Label(text="SIRADA", font_name="Oswald", font_size=sp_(13), bold=True,
                            color=ACCENT_DARK, size_hint=(None, None), size=(dp(72), dp(20)))
            bg_rect(sirada, ACCENT)
            eyebrow.add_widget(sirada)
        eyebrow.add_widget(BoxLayout())  # sag tarafi dolduran bosluk
        # Sirayi degistirme/kopyalama/gunu silme - YIKICI/programi degistiren
        # butonlar, SADECE "Düzenle" modu acikken gorunur (bkz. render_planner).
        if editable:
            up = Button(text="↑", size_hint=(None, None), size=(ICON_BTN_SIZE, ICON_BTN_SIZE), background_color=TRANSPARENT, color=FAINT)
            down = Button(text="↓", size_hint=(None, None), size=(ICON_BTN_SIZE, ICON_BTN_SIZE), background_color=TRANSPARENT, color=FAINT)
            dup = Button(text="Kopya", size_hint=(None, None), size=(dp(54), ICON_BTN_SIZE), background_color=TRANSPARENT, color=MUTED, font_size=sp_(13))
            delete = Button(text="×", size_hint=(None, None), size=(ICON_BTN_SIZE, ICON_BTN_SIZE), background_color=TRANSPARENT, color=DANGER)
            up.bind(on_release=lambda *_: (core.move_program_day(state, day["id"], -1), app.save(), self.render(keep_scroll=True)))
            down.bind(on_release=lambda *_: (core.move_program_day(state, day["id"], 1), app.save(), self.render(keep_scroll=True)))
            dup.bind(on_release=lambda *_: (core.duplicate_program_day(state, day["id"]), app.save(), self.render(keep_scroll=True)))
            delete.bind(on_release=lambda *_: self.confirm_delete_day(day["id"]))
            for w in (up, down, dup, delete):
                eyebrow.add_widget(w)
        card.add_widget(eyebrow)

        head_lbl = Label(text=tr_upper(headline), font_name="Oswald", font_size=sp_(24), color=TEXT,
                          halign="left", valign="middle", shorten=True, shorten_from="right",
                          size_hint_y=None, height=dp(30))
        head_lbl.bind(size=lambda *_: setattr(head_lbl, "text_size", head_lbl.size))
        card.add_widget(head_lbl)
        if meta:
            card.add_widget(label(meta + f" · {len(day['exercises'])} hareket", size=14, color=MUTED, height=dp(20)))

        # KOK NEDEN (kullanicidan gelen istek - "eklediğim hareketlerin
        # yerlerini nasıl değiştirebilirim"): gunler arasinda sira degistirme
        # (yukaridaki eyebrow'daki ↑/↓) zaten vardi, ama bir GUNUN KENDI
        # hareket listesi icin YOKTU - hareketler SADECE eklendikleri sirada
        # duruyordu, degistirmenin tek yolu hareketi silip yeniden (dogru
        # sirada) eklemekti. Gun-seviyesindeki move_program_day() ile AYNI
        # deseni (core.move_day_exercise) tek bir hareket satirina da
        # uyguluyoruz - SADECE Düzenle modunda gorunur, tipki "×" gibi.
        for i, ex in enumerate(day["exercises"]):
            ex_wrap = BoxLayout(orientation="vertical", size_hint_y=None, padding=(0, dp(2)))
            ex_wrap.bind(minimum_height=ex_wrap.setter("height"))
            with ex_wrap.canvas.before:
                Color(*DIVIDER)
                rline = Line(points=[0, ex_wrap.top, ex_wrap.width, ex_wrap.top], width=dp(1))
            ex_wrap.bind(pos=lambda w, *_: setattr(rline, 'points', [w.x, w.top, w.right, w.top]),
                         size=lambda w, *_: setattr(rline, 'points', [w.x, w.top, w.right, w.top]))

            row = ClickableRow(size_hint_y=None, height=dp(40), spacing=dp(4))
            row.add_widget(label(ex["name"], size=14.5, bold=True, color=TEXT))
            tgt = target_label(ex) or "hedef yok"
            tgt_lbl = mono_label(tgt, size=13.5, color=MUTED, halign="right",
                                  size_hint_x=None, width=dp(150) if editable else dp(174))
            row.add_widget(tgt_lbl)
            # Hedefi acip degistirme ve hareketi programdan cikarma da program
            # YAPISINI degistiren islemler - sadece Düzenle modunda aktif.
            if editable:
                row.bind(on_release=lambda *_, d=day, e=ex: self.open_target_editor(d, e["name"]))
                up = Button(text="↑", size_hint=(None, None), size=(ICON_BTN_SIZE, ICON_BTN_SIZE), background_color=TRANSPARENT, color=FAINT, font_size=sp_(15))
                down = Button(text="↓", size_hint=(None, None), size=(ICON_BTN_SIZE, ICON_BTN_SIZE), background_color=TRANSPARENT, color=FAINT, font_size=sp_(15))
                up.bind(on_release=lambda *_, d=day, idx=i: (core.move_day_exercise(state, d["id"], idx, -1), app.save(), self.render(keep_scroll=True)))
                down.bind(on_release=lambda *_, d=day, idx=i: (core.move_day_exercise(state, d["id"], idx, 1), app.save(), self.render(keep_scroll=True)))
                rm = Button(text="×", size_hint=(None, None), size=(ICON_BTN_SIZE, ICON_BTN_SIZE), background_color=TRANSPARENT, color=MUTED, font_size=sp_(17))
                rm.bind(on_release=lambda *_, d=day, idx=i: (core.remove_exercise_from_day(state, d["id"], idx), app.save(), self.render(keep_scroll=True)))
                for w in (up, down, rm):
                    row.add_widget(w)
            ex_wrap.add_widget(row)

            # UX (kullanicidan gelen istek - "hareket notu eklemek
            # istiyorum"): notu olan hareketlerde, satirin altinda kisa bir
            # onizleme satiri gosteriyoruz - notun TAMAMINI gormek/duzenlemek
            # icin satira dokunup Hedef popup'ini acmak yeterli (asagida
            # open_target_editor icindeki not alani).
            if ex.get("note"):
                note_lbl = label(ex["note"], size=12.5, color=FAINT, height=dp(18))
                note_lbl.shorten = True
                note_lbl.shorten_from = "right"
                ex_wrap.add_widget(note_lbl)

            card.add_widget(ex_wrap)

        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(16), padding=(0, dp(10), 0, 0))
        if editable:
            add_ex = Button(text="+ Hareket", background_color=TRANSPARENT, color=MUTED, font_size=sp_(13), size_hint_x=None, width=dp(90))
            add_ex.bind(on_release=lambda *_: self.open_exercise_picker(day["id"]))
            actions.add_widget(add_ex)
        deload = Button(text="Deload", background_color=TRANSPARENT, color=MUTED, font_size=sp_(13), size_hint_x=None, width=dp(70))
        deload.bind(on_release=lambda *_: self.start_session(day["id"], is_deload=True))
        actions.add_widget(deload)
        actions.add_widget(BoxLayout())
        start = Button(text="BAŞLA", font_name="Oswald", font_size=sp_(15),
                        background_normal="", background_down="", background_color=ACCENT,
                        color=ACCENT_DARK, size_hint_x=None, width=dp(110))
        start.bind(on_release=lambda *_: self.start_session(day["id"]))
        actions.add_widget(start)
        card.add_widget(actions)
        return card

    def confirm_delete_day(self, day_id):
        app = App.get_running_app()

        def on_confirm():
            core.delete_program_day(app.state, day_id)
            app.save()
            self.render(keep_scroll=True)

        confirm_dialog("Günü Sil", "Bu günü silmek istediğine emin misin?", on_confirm)

    def _build_exercise_picker(self, title, on_pick):
        # KOK NEDEN ("Hareket Ekle"ye basinca donma hissi): bu fonksiyon
        # ONCEDEN, TEK bir dokunma/on_release cagrisinin icinde, kutuphanedeki
        # TUM hareketler icin (80'den fazla, simdi 217) tek tek Button widget'i
        # olusturup her birinin metnini SENKRON olarak font'tan dokup dokusuna
        # (texture) ceviriyordu - bu iş bu (guclu, yazilim GPU'lu) sunucuda
        # hizli olsa da GERCEK bir telefonda (ozellikle ilk acilista, font
        # glyph onbellegi bosken) fark edilir bir sure surebilir. O sure
        # boyunca ekrana HICBIR SEY cizilmiyordu (popup'in kendisi de dahil) -
        # kullaniciya "dokunma algilanmadi, uygulama dondu" hissi veren tam
        # olarak buydu.
        #
        # DUZELTME: Once popup'i (baslik + bos/"Yükleniyor" govde ile) HEMEN
        # aciyoruz - bu, dokunmanin algilandigini ANINDA gosteriyor. Asil agir
        # is (217 butonun olusturulmasi) bir sonraki Clock karesine
        # devrediliyor - boylece popup'in kendi acilis cizimi ekrana yansidiktan
        # SONRA buton listesi kuruluyor, "donma" hissi ortadan kalkiyor
        # (toplam sure ayni ama kullanici artik bir tepki GORUYOR).
        #
        # NOT (klavye): Hareket kutuphanesi 217 hareme cikinca elle arama
        # pratik hale geldi. Bu TextInput, uygulamada bilincli olarak geri
        # getirilen TEK klavye kullanan yer - kalan her yerde (Set/Tekrar/
        # Agirlik/RIR/Dinlenme vb.) hala +/- stepper var, klavye hic acilmiyor.
        # Eger bu arama kutusu eskisi gibi donmaya sebep olursa, geri almak
        # kolay: sadece bu fonksiyonu (ve search TextInput'i) eski, arama
        # kutusu olmayan haline dondurmek yeterli - baska hicbir ekran
        # etkilenmiyor.
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        loading_lbl = label("Yükleniyor…", color=MUTED, halign="center", height=dp(200))
        content.add_widget(loading_lbl)
        popup = Popup(title=title, size_hint=(0.9, 0.9), content=content)
        # animation=False: bu popup'in acilisi ONCEDEN animasyonluydu (tek
        # istisna - dosyadaki BASKA HICBIR popup.open() cagrisinda animasyon
        # yok). Kullanicinin gonderdigi ekran goruntusunde (Bench Dip) eski
        # Hedef popup'inin kalintisinin gorunmesi, tam olarak "‹ Geri" ->
        # do_back() -> BU popup'i acan open_exercise_picker() akisinda
        # oluyordu - do_back() onceki Hedef popup'ini animasyonsuz kapatiyor
        # ama BU popup fade-in ile aciliyordu, o solma suresi boyunca eski
        # icerigin kalintisi gorunebiliyordu. Diger butun popup.open()
        # cagrilariyla tutarli olmasi icin burada da kapatiyoruz.
        popup.open(animation=False)

        def build_body(*_a):
            content.clear_widgets()

            # Klavye HENUZ acilmadan once pencerenin "tam" (kucultulmemis)
            # yuksekligini referans olarak saklıyoruz - asagidaki pick()
            # icinde klavyenin GERCEKTEN kapanip kapanmadigini (sabit bir
            # sure tahmin etmek yerine) buna gore anliyoruz.
            full_window_height = Window.height

            # NOT (Geri butonu tasindi): burada ayri bir "‹ Geri" butonu
            # ARTIK YOK - kullanici geri bildirimiyle bunun "yanlis yerde"
            # oldugunu, asil ihtiyacin bir hareket SECTIKTEN SONRA (Hedef
            # ekraninda) "vazgecip baska hareket seçeyim" durumunda oldugunu
            # belirtti. Bkz. open_target_editor()'daki on_back parametresi.
            # Bu listeyi hicbir sey secmeden kapatmak icin popup'in disina
            # dokunmak yeterli (Popup varsayilani auto_dismiss=True).
            header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            # UX incelemesi (Task: Hareketler ekranina da arama eklendi) -
            # bu TextInput artik shared.exercise_search_input() FABRIKASI
            # uzerinden kuruluyor (bkz. o fonksiyondaki KOK NEDEN notu) -
            # gorunum/davranis BIREBIR AYNI kaldi, sadece tanim tekilleşti.
            search = exercise_search_input()
            header.add_widget(search)
            content.add_widget(header)

            names_sorted = sorted(core.all_exercise_names(app.state))

            # Task 17 (217 elemanli listede performans - "sadece gorunen
            # satirlar somutlastirilsin"): eskiden burada arama/filtre HER
            # degistiginde eslesen HER hareket icin ayri bir Button nesnesi
            # olusturuluyordu (yukaridaki fonksiyon-basi KOK NEDEN notundaki
            # "donma hissi" ile ayni kok sebep - sadece ilk acilista degil,
            # HER tus vurusunda tekrarlaniyordu). RecycleView'e gecildi:
            # _PickerRow'un SINIRLI sayida (sadece ekranda gorunen + kucuk
            # bir tampon kadar) ornegi olusturulup kaydirma sirasinda AYNI
            # orneklar YENIDEN KULLANILIR - artik arama kutusuna her harf
            # yazildiginda 217 degil, sadece rv.data (hafif dict listesi)
            # degisiyor; gercek Button widget'lari sadece kaydirilarak
            # GORUNUR hale geldikce kurulur. Davranis (arama-yaz-filtrele,
            # dokunup-sec, bos sonuc mesaji) BIREBIR AYNI kaldi.
            # KOK NEDEN (kullanicidan gelen gercek hata - "Hareketlerin
            # hiçbiri yok", Hareket Seç popup'i tamamen bos aciliyordu):
            # rv.viewclass, Kivy'de bir AliasProperty - SETTER'i
            # "self.layout_manager varsa ONA ata, yoksa hicbir sey yapma"
            # seklinde calisiyor (bkz. kivy/uix/recycleview/__init__.py
            # RecycleView._set_viewclass). rv.add_widget(rv_layout)
            # CAGRILMADAN ONCE rv.layout_manager HENUZ YOK (RecycleView,
            # layout_manager'i SADECE kendisine bir RecycleLayoutManagerBehavior
            # COCUGU EKLENINCE otomatik atar). Yani "rv.viewclass = _PickerRow"
            # SATIRI, rv_layout EKLENMEDEN once cagrilirsa SESSIZCE HICBIR
            # SEY YAPMAZ - hata da vermez, sadece viewclass hep None kalir,
            # RecycleDataAdapter hicbir gercek satir widget'i olusturamaz
            # (rv.data dolu olsa, minimum_height/scrollbar dogru hesaplansa
            # BILE - tam ekranda gordugumuz: arama kutusu var, altinda BOS,
            # ince bir kaydirma cubugu var ama hic satir yok). Bu, GERCEK
            # cihazda VE bu depodaki xvfb tabanli duman testinde AYNI sekilde
            # tekrarlanan, ortam-bagimsiz gercek bir sira/mantik hatasiydi -
            # daha once (yanlislikla) "RecycleView headless ortamda gercek
            # widget kurmuyor" diye test-ortami sinirlamasi sanilmisti; asil
            # sebep BUYMUS.
            #
            # DUZELTME: rv.viewclass ATANMASI, rv.add_widget(rv_layout)
            # CAGRISINDAN SONRAYA tasindi - artik layout_manager zaten
            # atanmisken viewclass gercekten layout_manager'a gecebiliyor.
            rv = RecycleView(size_hint=(1, 1))
            rv_layout = RecycleBoxLayout(
                orientation="vertical", size_hint_y=None, spacing=dp(4),
                default_size=(None, dp(38)), default_size_hint=(1, None),
            )
            rv_layout.bind(minimum_height=rv_layout.setter("height"))
            rv.add_widget(rv_layout)
            rv.viewclass = _PickerRow

            empty_lbl = label("Sonuç bulunamadı.", color=MUTED, halign="center", height=dp(60))

            def refresh(query):
                q = query.strip().lower()
                matches = [n for n in names_sorted if q in n.lower()] if q else names_sorted
                if not matches:
                    # bos sonuc: listeyi (rv) kaldirip mesaji goster - eski
                    # kodda ayni gorsel sonuc col.add_widget(empty_lbl) ile
                    # elde ediliyordu.
                    if rv.parent is content:
                        content.remove_widget(rv)
                    if empty_lbl.parent is None:
                        content.add_widget(empty_lbl)
                    return
                if empty_lbl.parent is content:
                    content.remove_widget(empty_lbl)
                if rv.parent is None:
                    content.add_widget(rv)

                def make_pick(name):
                    # KOK NEDEN NOTU: bu fabrika fonksiyonu, eski koddaki
                    # "def pick(*_a, name=n):" varsayilan-parametre hilesinin
                    # (dongudeki gec-baglanma/late-binding tuzagini onlemek
                    # icin) RecycleView data-listesi bağlaminda karsiligidir -
                    # her make_pick(n) cagrisi KENDI izole "name" degiskenine
                    # sahip yeni bir pick() dondurur, tipki eskisi gibi HER
                    # satirin DOGRU hareket adiyla eslesmesini garanti eder.
                    def pick():
                        # KOK NEDEN 1 (dogrudan tiklamada da olan eski kayma):
                        # normal (animasyonlu) dismiss ~0.25sn boyunca solarak
                        # kapanir - bu sure icinde on_pick(name) HEMEN yeni bir
                        # popup (Hedef) actigi icin iki popup ayni anda yari
                        # saydam ust uste biniyordu. Aninda (animasyonsuz)
                        # kapatarak bunu cozduk.
                        #
                        # KOK NEDEN 2 (SADECE arama kutusu kullanildiginda
                        # devam eden kayma): arama kutusuna dokunulunca Android
                        # klavyeyi acar ve pencereyi kucultur (adjustResize).
                        # Sonuca dokununca klavye ODAK KAYBEDINCE kapanmaya
                        # BASLAR ama bu KAPANMA/yeniden-buyume ANLIK degil -
                        # Android'in kendi (cihazdan cihaza degisen suredeki)
                        # kapanma animasyonu var. O animasyon bitmeden Hedef
                        # popup'ini acip fit_popup_to_content() ile boyutunu
                        # HESAPLARSAK, hesaplama HALA kucuk (klavye acikken
                        # kucultulmus) pencereye gore yapiliyor.
                        #
                        # ONCEKI DUZELTME (sabit 0.3sn bekleme) YETERSIZ
                        # CIKTI - kullanici ayni kaymayi tekrar bildirdi.
                        # Sabit bir sure TAHMIN ETMEK yerine, pencerenin
                        # GERCEKTEN eski (klavyesiz) yuksekligine donmesini
                        # Window.on_resize event'i ile BEKLIYORUZ - boylece
                        # cihaz ne kadar yavas/hizli olursa olsun doğru
                        # anda aciliyoruz. Resize event hic gelmezse (bazi
                        # cihaz/durumlarda olabilir) 1.5sn'lik bir guvenlik
                        # agi var, sonsuza kadar beklemeyelim diye.
                        # KOK NEDEN 3 (kullanici bildirimiyle bulundu - "her
                        # cihazda, her zaman SADECE bu ekranda" - yani rastgele
                        # bir GPU/zamanlama sorunu DEGIL, deterministik bir
                        # sıralama hatasi): Bu picker popup'ini dismiss()
                        # ettikten HEMEN sonra, AYNI Python cagrisi icinde
                        # (hicbir Kivy karesi/cizimi araya girmeden) Hedef
                        # popup'ini acmak (on_pick -> open_target_editor ->
                        # yeni Popup + fit_popup_to_content + popup.open),
                        # Kivy'e "once eskisini tamamen kaldir, SONRA
                        # yenisini ciz" diyecek bir kare sinirini hic
                        # yasatmiyordu. Sonuc: eskisinin canvas/arka plan
                        # kalintisi, yenisinin arkasinda/icinde gorunebiliyordu
                        # - btun cihazlarda ayni sekilde, cunku bu bir donanim
                        # rastgeleligi degil, kod sirasi meselesi. Aralarina
                        # Clock.schedule_once(..., 0) ile TAM BIR KARE
                        # sinirini bilerek sokuyoruz: dismiss() bir sonraki
                        # karede tamamen islensin, Hedef popup'i ONDAN
                        # SONRAKI karede acilsin.
                        def open_next(*_c, _name=name):
                            on_pick(_name)

                        had_focus = search.focus
                        search.focus = False
                        popup.dismiss(animation=False)

                        if not had_focus or Window.height >= full_window_height - dp(2):
                            # Klavye hic acilmadiysa (dogrudan listeden secim)
                            # VEYA pencere zaten tam yuksekligindeyse (klavye
                            # zaten kapanmis) ekstra bekleme yok - ama yine de
                            # bir kare sinirini (yukaridaki not) bilerek
                            # birakiyoruz.
                            Clock.schedule_once(open_next, 0)
                            return

                        state = {"done": False}

                        def proceed(*_b):
                            if state["done"]:
                                return
                            state["done"] = True
                            Window.unbind(on_resize=on_resize_cb)
                            Clock.schedule_once(open_next, 0)

                        def on_resize_cb(*_b):
                            if Window.height >= full_window_height - dp(2):
                                proceed()

                        Window.bind(on_resize=on_resize_cb)
                        Clock.schedule_once(proceed, 1.5)  # guvenlik agi

                    return pick

                rv.data = [{"text": n, "on_release": make_pick(n)} for n in matches]

            search.bind(text=lambda _w, val: refresh(val))
            refresh("")
            # NOT: serbest metinle "yeni hareket adi" ekleme HALA yok -
            # arama sadece kutuphanedeki 217 onceden tanimli hareketi
            # filtreliyor, olmayan bir ismi yazip "ekle" diye bir yol yok.

        Clock.schedule_once(build_body, 0)
        return popup

    def open_exercise_picker(self, day_id):
        def on_pick(name):
            # on_back: kullanici Hedef ekranindayken "‹ Geri"ye basarsa,
            # tekrar hareket arama/secme listesine donsun (baska bir
            # hareket secebilsin) - bkz. open_target_editor()'daki not.
            def on_back():
                self.open_exercise_picker(day_id)
            self.open_target_editor({"id": day_id}, name, on_back=on_back)
        self._build_exercise_picker("Hareket Seç", on_pick)

    def open_target_editor(self, day, name, on_back=None):
        # Bu popup'taki alanlar (Set/Tekrar min/Tekrar max/Agirlik/RIR/
        # Dinlenme) klavye kullanmiyor - bkz. make_stepper() tanimindaki not.
        #
        # on_back (kullanici bildirimiyle eklendi - "Geri" butonu ONCEDEN
        # hareket arama listesinde idi, kullanici bunun "yanlis yerde"
        # oldugunu, asil ihtiyacin bir hareket SECTIKTEN SONRA "vazgecip
        # baska hareket seçeyim" durumunda oldugunu belirtti): SADECE
        # day_card()'daki "+ Hareket" -> secim akisindan (open_exercise_picker
        # uzerinden) gelindiginde doludur - o zaman "‹ Geri" gorunur ve
        # tekrar hareket listesini acar. Gundeki VAROLAN bir harekete
        # dokunup (day_card icindeki row.on_release) hedefini duzenlerken
        # None kalir - donulecek bir "onceki liste ekrani" olmadigi icin
        # orada "‹ Geri" hic gosterilmez.
        app = App.get_running_app()
        state = app.state
        day_obj = next((d for d in state["program"]["days"] if d["id"] == day["id"]), None)
        existing = next((e for e in day_obj["exercises"] if e["name"] == name), {}) if day_obj else {}

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        title_row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
        content.add_widget(title_row)

        sets_i = make_stepper("Set", existing.get("targetSets"), step=1)
        rmin_i = make_stepper("Tekrar min", existing.get("targetRepsMin"), step=1)
        rmax_i = make_stepper("Tekrar max", existing.get("targetRepsMax"), step=1)
        # targetWeight depoda HER ZAMAN kg - kullaniciya kendi sectigi birimde
        # gosteriyoruz, kaydederken (asagida do_save icinde) tekrar kg'ye ceviriyoruz.
        w_step = 2.5 if weight_unit() == "kg" else 5
        w_i = make_stepper(f"Ağırlık ({weight_unit()})", to_display_weight(existing.get("targetWeight")),
                            step=w_step, decimals=True)
        rir_i = make_stepper("RIR", existing.get("targetRIR"), step=1, max_val=10)
        rest_i = make_stepper("Dinlenme (sn)", existing.get("restSeconds"), step=15)
        for w in (sets_i, rmin_i, rmax_i, w_i, rir_i, rest_i):
            content.add_widget(w)

        # UX (kullanicidan gelen istek - "bazı hareketlere not eklemek
        # istiyorum") - bkz. shared.note_input()'taki KOK NEDEN notu.
        content.add_widget(label("Not", size=12, color=MUTED, height=dp(16)))
        note_i = note_input(text=existing.get("note") or "")
        content.add_widget(note_i)

        # KOK NEDEN (kullanicinin gonderdigi ekran goruntusunde "‹ Geri"
        # kutusu duzgun ama hemen yanindaki hareket adi ve altindaki alanlar
        # arka plansiz gorunup arkadaki gun kartinin satiri sizmasi): Popup
        # ONCEDEN yari-dolu bir content ile OLUSTURULUYOR, SONRA title_row'a
        # (geri butonu + isim) ve content'e (Kaydet butonu) daha fazla widget
        # EKLENIYORDU. Popup'in kendi arka plan/boyut hesaplamasi
        # (fit_popup_to_content -> content.bind(minimum_height=...)) her
        # ekleme ile TEKRAR TEKRAR tetikleniyordu - Popup zaten ACILMIS
        # (veya acilmaya hazirlanirken) boyle asamali buyumeler, gercek
        # cihazda Popup'in kendi arka plan dikdortgeninin YENI icerigin
        # tamamini henuz kapsamadigi bir ara kareyi GORUNUR kilabiliyordu.
        # DUZELTME: content'i (title_row'un TAM icerigi + tum steplar + Kaydet
        # butonu dahil) TAMAMEN bitirdikten SONRA Popup'i olusturup boyutunu
        # TEK SEFERDE hesapliyoruz - Popup hic yari-dolu bir content ile var
        # olmuyor.
        if on_back is not None:
            def do_back(*_a):
                # KOK NEDEN (kullanicinin "Bench Dip" ekran goruntusunde
                # gorulen, eski Hedef popup'inin kalintisinin yeni popup'in
                # arkasinda gorunmesi): "hareket sec -> Hedef" yonunu daha
                # once duzelttik (bkz. pick() icindeki KOK NEDEN 3 notu -
                # dismiss() ile bir sonraki popup.open() arasina bilerek bir
                # Clock karesi koyduk) AMA "‹ Geri" ile TERS yonde (Hedef'ten
                # cikip tekrar hareket listesini acarken) ayni duzeltmeyi
                # UNUTMUSTUK - burada da dismiss() hemen ardindan (ayni Python
                # cagrisinda) on_back() -> open_exercise_picker() -> yeni bir
                # Popup aciliyordu. Ayni sekilde bir kare araya koyuyoruz.
                note_i.focus = False
                popup.dismiss(animation=False)
                Clock.schedule_once(lambda *_b: on_back(), 0)
            back_btn = styled_button("‹ Geri", color=RAISED, text_color=TEXT,
                                      size_hint=(None, None), size=(dp(84), dp(32)))
            back_btn.bind(on_release=do_back)
            title_row.add_widget(back_btn)
        title_row.add_widget(label(name, size=17, bold=True, height=dp(28)))

        save_btn = styled_button("Kaydet")

        def to_num(value, cast=int):
            if value is None:
                return None
            return cast(value)

        def do_save(*_):
            core.set_day_exercise_target(
                state, day["id"], name,
                target_sets=to_num(sets_i.value), target_reps_min=to_num(rmin_i.value),
                target_reps_max=to_num(rmax_i.value),
                target_weight=to_storage_kg(to_num(w_i.value, float)),
                target_rir=to_num(rir_i.value), rest_seconds=to_num(rest_i.value),
                note=note_i.text.strip(),
            )
            app.save()
            # search.focus = False (bkz. _build_exercise_picker'daki pick()
            # icindeki AYNI desen) - not alaninda hala odak/klavye acikken
            # dismiss edersek, klavye kapanma animasyonu popup kapandiktan
            # SONRA da bir sure devam edebilir; once odaktan cikariyoruz.
            note_i.focus = False
            # animation=False: diger tum popup gecislerinde oldugu gibi (bkz.
            # _build_exercise_picker'daki notlar) - kullanici hemen ardindan
            # baska bir hareketin hedefini acarsa, eski (hala solmakta olan)
            # Hedef popup'i ile yenisi ust uste binmesin.
            popup.dismiss(animation=False)
            self.render()

        save_btn.bind(on_release=do_save)
        content.add_widget(save_btn)
        # content ARTIK TAMAMEN HAZIR (title_row + 6 stepper + Kaydet) -
        # Popup'i ve boyutunu SIMDI, TEK SEFERDE olusturuyoruz.
        popup = Popup(title="Hedef", content=content, size_hint=(0.9, None))
        fit_popup_to_content(popup, content)
        # animation=False: Popup.open() de VARSAYILAN olarak solarak
        # (alpha 0->1) acilir - bu popup ozellikle arama+klavye akisindan
        # (yukaridaki Window.on_resize bekleyisinden) HEMEN sonra acildigi
        # icin, ayni anda hem pencere yeniden duzeni hem de bu fade-in
        # animasyonu calisirsa cihazda ekstra agir/tutarsiz bir kare
        # olusabilir - bildirilen kaymanin bir parcasi bu da olabilir.
        # Aninda (solmadan) acarak bu ihtimali de ortadan kaldiriyoruz.
        popup.open(animation=False)

    # ---- Aktif antrenman ----
    def start_session(self, day_id, is_deload=False):
        app = App.get_running_app()
        core.start_session(app.state, day_id, is_deload)
        app.save()
        self.render()

    def render_active_session(self, state):
        app = App.get_running_app()
        sess = state["activeSession"]
        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))

        header = Card(size_hint_y=None, height=dp(92), spacing=dp(2))
        title_row = BoxLayout(size_hint_y=None, height=dp(22))
        title_row.add_widget(label(sess["dayName"] or "Serbest Antrenman", size=14, bold=True, color=MUTED))
        if sess["isDeload"]:
            deload_tag = Label(text="DELOAD", font_name="Oswald", font_size=sp_(13), bold=True,
                                color=ACCENT_DARK, size_hint=(None, None), size=(dp(62), dp(18)))
            bg_rect(deload_tag, ACCENT)
            title_row.add_widget(deload_tag)
        header.add_widget(title_row)
        tonnage = core.session_tonnage(sess)
        tonnage_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self._tonnage_lbl = mono_label(f"{to_display_weight(tonnage):g}", size=32, color=ACCENT, bold=True, height=dp(44))
        tonnage_row.add_widget(self._tonnage_lbl)
        tonnage_row.add_widget(label(weight_unit(), size=14, color=MUTED, height=dp(44)))
        header.add_widget(tonnage_row)
        col.add_widget(header)

        for i, ex in enumerate(sess["exercises"]):
            col.add_widget(self.exercise_card(state, sess, ex, i))

        add_ex = styled_button("+ HAREKET EKLE", color=RAISED, text_color=TEXT)
        add_ex.bind(on_release=lambda *_: self.add_adhoc_exercise())
        col.add_widget(add_ex)

        finish = styled_button("Antrenmanı Bitir ve Kaydet")
        finish.bind(on_release=lambda *_: (core.finish_session(state), app.save(), toast(app, "ANTRENMAN KAYDEDİLDİ"), self.render()))
        col.add_widget(finish)

        discard = styled_button("Antrenmanı Sil", color=(0.2, 0.1, 0.1, 1), text_color=DANGER)
        discard.bind(on_release=lambda *_: self.confirm_discard_session())
        col.add_widget(discard)

        scroll.add_widget(col)
        return scroll

    def confirm_discard_session(self):
        # KOK NEDEN (yanlislikla dokunma riski): bu buton ONCEDEN hicbir onay
        # istemeden TEK dokunusla butun antrenmani (o ana kadar girilen tum
        # setleri) siliyordu - antrenman sirasinda telefon elde/terlemisken
        # en riskli buton tam olarak buydu. Artik diger tum yikici islemlerle
        # (gunu sil, kaydi sil, verileri sifirla) AYNI onay deseni kullaniyor.
        app = App.get_running_app()

        def on_confirm():
            core.discard_session(app.state)
            app.save()
            self.render()

        confirm_dialog(
            "Antrenmanı Sil",
            "Bu antrenmanı silmek istediğine emin misin? Şimdiye kadar "
            "girdiğin tüm setler kaybolacak. Bu işlem geri alınamaz.",
            on_confirm)

    def add_adhoc_exercise(self):
        # _build_exercise_picker()'daki AYNI donma hissi buradaki hareket
        # listesinde de vardi - AYNI ortak yardimci burada da kullaniliyor.
        # Detay icin _build_exercise_picker()'in basindaki yorum bloguna bak.
        app = App.get_running_app()

        def on_pick(name):
            core.add_exercise_to_session(app.state, name)
            app.save()
            self.render()

        self._build_exercise_picker("Hareket Ekle", on_pick)

    def confirm_remove_exercise(self, sess, idx, name):
        # KOK NEDEN (yanlislikla dokunma riski): antrenman sirasinda bir
        # hareketi karttan cikaran "×" ONCEDEN hicbir onay istemeden TEK
        # dokunusla o harekete o ana kadar girilmis TUM setleri de birlikte
        # siliyordu. Antrenman sirasinda telefon elde/terlemisken bu, "Antrenmanı
        # Sil" kadar tehlikeli bir yanlislik riskiydi - simdi ayni onay deseni
        # burada da var.
        app = App.get_running_app()

        def on_confirm():
            sess["exercises"].pop(idx)
            app.save()
            self.render(keep_scroll=True)

        confirm_dialog(
            "Hareketi Çıkar",
            f'"{name}" hareketini antrenmandan çıkarmak istediğine emin misin? '
            "Bu harekete girdiğin setler varsa onlar da silinir.",
            on_confirm, confirm_text="Evet, Çıkar")

    def exercise_card(self, state, sess, ex, idx):
        # Onceden her set eklendiginde/silindiginde TUM ekran (basliktan diger
        # tum hareket kartlarina kadar) yeniden ciziliyordu - bu da her "+" ya
        # basista gozle gorulur bir kasmaya sebep oluyordu. Simdi sadece BU
        # kart kendi icerigini yeniden kuruyor (card.clear_widgets() + rebuild),
        # digerlerine dokunulmuyor; ustteki tonaj sayaci da ayrica hafifce
        # guncelleniyor (bkz. self.refresh_tonnage).
        app = App.get_running_app()
        card = Card(size_hint_y=None, spacing=dp(4))
        card.bind(minimum_height=card.setter("height"))

        # KOK NEDEN (kod incelemesinde bulundu - "max_weight_for her set
        # eklemede tum gecmisi tariyor"): rebuild() bir antrenman sirasinda
        # bu harekete HER set eklendiginde/silindiginde YENIDEN cagriliyor
        # ve HER seferinde core.max_weight_for() ile TUM gecmisi (yuzlerce
        # seans olabilir) bastan taniyordu. Oysa prev_max, state["history"]'ye
        # bakar - AKTIF seans icindeki set ekleme/silme HICBIR ZAMAN
        # gecmisi degistirmez, yani bu deger bu kartin omru boyunca
        # SABITTIR. Tekrar tekrar hesaplamak yerine BIR KEZ hesaplayip
        # closure'da saklıyoruz.
        prev_max = core.max_weight_for(state, ex["name"])

        def rebuild(*_):
            card.clear_widgets()
            working = [s for s in ex["sets"] if not s.get("isWarmup")]
            head = BoxLayout(size_hint_y=None, height=dp(32))
            head.add_widget(label(ex["name"], size=16, bold=True))
            # dp(32): kod incelemesinde bulunan "dokunma hedefi cok kucuk"
            # bulgusuna karsi - Android'in onerdigi ~44-48dp'ye tam
            # ulasamasak da (satir yuksekligi/yogun liste gorunumu
            # korunarak) ONCEKI dp(26)'dan belirgin sekilde buyutuldu.
            rm_ex = Button(text="×", size_hint=(None, None), size=(ICON_BTN_SIZE, ICON_BTN_SIZE), background_color=TRANSPARENT, color=MUTED, font_size=sp_(18))
            rm_ex.bind(on_release=lambda *_: self.confirm_remove_exercise(sess, idx, ex["name"]))
            head.add_widget(rm_ex)
            card.add_widget(head)
            meta = f"{len(working)} SET" + (f" · ÖNCEKİ REKOR {fmt_weight(prev_max).upper()}" if prev_max else "")
            card.add_widget(mono_label(meta, size=14, color=MUTED, height=dp(20)))

            tgt = target_label(ex)
            if tgt:
                tgt_row = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
                tgt_row.add_widget(label("HEDEF", size=14, bold=True, color=ACCENT, size_hint_x=None, width=dp(56)))
                tgt_row.add_widget(mono_label(tgt, size=14, color=TEXT))
                card.add_widget(tgt_row)
            if ex.get("suggestedWeight") is not None:
                txt = f"{fmt_weight(ex['suggestedWeight'])} — {SUGGEST_TEXT.get(ex.get('suggestReason'), '')}"
                sug_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
                sug_row.add_widget(label("ÖNERİ", size=14, bold=True, color=STEEL, size_hint_x=None, width=dp(56)))
                sug_row.add_widget(label(txt, size=14, color=STEEL))
                card.add_widget(sug_row)
            if ex.get("note"):
                # UX (kullanicidan gelen istek - "bazı hareketlere not
                # eklemek istiyorum"): notun asil faydasi TAM DA antrenman
                # SIRASINDA gorunmesi (ör. "dirsekleri içeride tut") - bu
                # yuzden HEDEF/ONERI ile AYNI "etiket + metin" satir desenini
                # kullaniyoruz, ama notlar (steppers'in aksine) uzun/coklu
                # satir olabilecegi icin, sabit dp(30) yerine label()'in
                # kendi (texture_size'a gore otomatik buyuyen, bkz. label()
                # tanimindaki KOK NEDEN notu) yuksekligini satira da
                # yansitiyoruz - not KIRPILMADAN tam okunabilsin.
                note_lbl = label(ex["note"], size=14, color=MUTED)
                note_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
                note_row.add_widget(label("NOT", size=14, bold=True, color=MUTED, size_hint_x=None, width=dp(56)))
                note_row.add_widget(note_lbl)
                note_lbl.bind(height=lambda _w, h: setattr(note_row, "height", max(dp(30), h)))
                card.add_widget(note_row)

            for si, s in enumerate(ex["sets"]):
                row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
                flag = "ISI" if s.get("isWarmup") else str(si + 1)
                row.add_widget(mono_label(f"{flag}", size=14, color=MUTED, width=dp(28)))
                row.add_widget(mono_label(f"{fmt_weight(s['weight'])} × {s['reps']}", size=14,
                                           color=FAINT if s.get("isWarmup") else TEXT))
                badge = core.rir_badge_info(s, ex)
                if badge:
                    badge_color = {"easy": ACCENT, "hard": DANGER, "ontarget": STEEL, "neutral": MUTED}[badge["kind"]]
                    row.add_widget(mono_label(badge["text"], size=14, color=badge_color, halign="right"))
                rm = Button(text="×", size_hint=(None, None), size=(ICON_BTN_SIZE, ICON_BTN_SIZE), background_color=TRANSPARENT, color=MUTED, font_size=sp_(17))
                def do_remove(*_a, j=si):
                    core.remove_set(state, idx, j)
                    app.save()
                    rebuild()
                    self.refresh_tonnage()
                rm.bind(on_release=do_remove)
                row.add_widget(rm)
                card.add_widget(row)

            # Set eklerken kullanilan agirlik/tekrar/RIR alanlari - klavye
            # acmayan +/- sayaci (bkz. make_stepper() tanimindaki not).
            _sw = ex.get("suggestedWeight") or ex.get("targetWeight")
            w_step = 2.5 if weight_unit() == "kg" else 5
            form = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
            w_stepper = make_stepper(f"Ağırlık ({weight_unit()})", to_display_weight(_sw),
                                      step=w_step, decimals=True)
            r_stepper = make_stepper("Tekrar", ex.get("targetRepsMin"), step=1)
            form.add_widget(w_stepper)
            form.add_widget(r_stepper)
            card.add_widget(form)

            extra = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(8))
            rir_stepper = make_stepper("RIR", ex.get("targetRIR"), step=1, max_val=10, btn_width=dp(36))
            rir_stepper.size_hint_x = 0.4
            warm_toggle = ToggleButton(text="Isınma Seti", size_hint_x=0.6, background_normal="", background_down="", background_color=RAISED, color=TEXT)
            extra.add_widget(rir_stepper)
            extra.add_widget(warm_toggle)
            card.add_widget(extra)

            add_btn = styled_button("+ Seti Ekle", color=ACCENT, text_color=(0.07, 0.08, 0.06, 1))
            card.add_widget(add_btn)

            def submit(*_):
                w = w_stepper.value
                r = r_stepper.value
                if not w or not r:
                    toast(app, "Geçerli değer gir")
                    return
                rir = int(rir_stepper.value) if rir_stepper.value is not None else None
                # Kullanici agirligi kendi sectigi birimde (kg ya da lb) girdi -
                # depoya HER ZAMAN kg olarak yaziyoruz (bkz. dosyanin basindaki
                # birim-sistemi notu).
                is_pr = core.add_set(state, idx, to_storage_kg(w), int(r), is_warmup=warm_toggle.state == "down", rir=rir)
                app.save()
                if is_pr:
                    toast(app, "YENİ REKOR — PR!")
                rebuild()
                self.refresh_tonnage()

            add_btn.bind(on_release=submit)

        rebuild()
        return card

    def refresh_tonnage(self):
        """Set eklendiginde/silindiginde SADECE ustteki tonaj sayacini gunceller;
        tum ekrani yeniden cizmekten (ve bunun yarattigi kasmadan) kacinir."""
        app = App.get_running_app()
        sess = app.state.get("activeSession")
        if sess and getattr(self, "_tonnage_lbl", None) is not None:
            self._tonnage_lbl.text = f"{to_display_weight(core.session_tonnage(sess)):g}"
