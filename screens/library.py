"""
TONAJ - Hareketler (kutuphane) ekrani (Task 18 refactor: main.py'den
ayrildi).

DUZELTME (UX incelemesi - yanlis docstring): burada ONCEDEN "uygulamanin
butun hareket kutuphanesini (217+ hareket), kas grubuna gore gruplanmis
olarak listeler" yaziyordu - bu, kodun GERCEKTE yaptigindan farkliydi ve
kafa karistirici bir isim/beklenti uyusmazligina isaret ediyordu. Bu ekran
aslinda 217'lik TUM hareket kutuphanesini degil, SADECE kullanicinin
GECMISTE en az bir kez calistigi hareketleri (kisisel rekorlariyla birlikte)
listeler - yani bir "Kisisel Rekorlar" ozetidir, kas grubuna gore
gruplama da YOKTUR (duz alfabetik liste). 217 hareketlik TAM kutuphaneyi
gormek/aramak icin kullanilan yer, program ekranindaki "+ Hareket" secici
popup'udur (bkz. screens/program.py open_exercise_picker).

UX incelemesi guncellemesi (kullanicidan gelen istek - "Hareketler
ekraninda arama/filtre yok"): antrenman gecmisi biriktikce bu liste
uzayabiliyordu, istenen hareketi bulmak icin elle kaydirmak gerekiyordu.
Simdi ustte bir arama kutusu var - shared.exercise_search_input() ile
AYNI (tek, paylasilan) bilesen (bkz. o fonksiyondaki "sifir klavye"
kuralina neden aykiri DEGIL" notu), hareket secici popup'undaki arama ile
BIREBIR ayni gorunum/davranis. Liste, boyutu (genelde 217'lik tam
kutuphaneden COK daha kucuk - sadece GECMISTE calisilan hareketler kadar)
RecycleView gerektirecek kadar buyumedigi icin duz bir ScrollView+BoxLayout
olarak kaldi; sadece FILTRELENMIS satirlar kuruluyor (arama kutusu
degistikce SADECE liste kismi yeniden kuruluyor, arama kutusunun kendisi
YOK EDILIP YENIDEN OLUSTURULMUYOR - aksi halde her tus vurusunda odak/
klavye kaybolurdu, bkz. screens/program.py'deki ayni desenin notu).
"""
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

import core
from shared import MUTED, FAINT, ACCENT, fmt_weight, Card, label, mono_label, exercise_search_input


class LibraryScreen(Screen):
    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        state = app.state
        self.clear_widgets()

        names = set()
        for s in state["history"]:
            for e in s["exercises"]:
                names.add(e["name"])
        names_sorted = sorted(names)

        root_col = BoxLayout(orientation="vertical")

        if names_sorted:
            header = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(12), 0, dp(12), 0))
            search = exercise_search_input(hint="Hareketlerde ara…")
            header.add_widget(search)
            root_col.add_widget(header)

        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(12))
        col.bind(minimum_height=col.setter("height"))
        scroll.add_widget(col)
        root_col.add_widget(scroll)
        self.add_widget(root_col)

        def refresh_rows(query=""):
            col.clear_widgets()
            q = query.strip().lower()
            filtered = [n for n in names_sorted if q in n.lower()] if q else names_sorted

            for n in filtered:
                pts = core.history_for_exercise(state, n)
                pr = max((p["max"] for p in pts), default=0)
                row = Card(size_hint_y=None, height=dp(58), orientation="horizontal", spacing=dp(8))
                info = BoxLayout(orientation="vertical")
                info.add_widget(label(n, size=14, bold=True, height=dp(20)))
                info.add_widget(mono_label(f"{len(pts)} antrenman", size=14, color=MUTED, height=dp(18)))
                row.add_widget(info)
                pr_col = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(70))
                # HATA DUZELTMESI: pts bossa (bu harekete hic set girilmemisse - ör.
                # bir antrenmana eklenip hic calisilmadan bitirilmis) eskiden yine de
                # "0kg / PR" yaziyordu - bu, kullaniciya olmayan bir rekor varmis
                # izlenimi veriyordu. Artik boyle durumda "—" gosteriliyor.
                if pts:
                    pr_col.add_widget(mono_label(fmt_weight(pr), size=15, color=ACCENT, bold=True, halign="right", height=dp(22)))
                    pr_col.add_widget(label("PR", size=14, color=MUTED, halign="right", height=dp(18)))
                else:
                    pr_col.add_widget(mono_label("—", size=15, color=FAINT, bold=True, halign="right", height=dp(22)))
                    pr_col.add_widget(label("yok", size=14, color=FAINT, halign="right", height=dp(18)))
                row.add_widget(pr_col)
                col.add_widget(row)

            if not names_sorted:
                col.add_widget(label("Henüz hiç antrenman kaydın yok.", color=MUTED, height=dp(40)))
            elif not filtered:
                col.add_widget(label("Aramanla eşleşen hareket yok.", color=MUTED, height=dp(40)))

        if names_sorted:
            search.bind(text=lambda _w, val: refresh_rows(val))
        refresh_rows()
