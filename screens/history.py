"""
TONAJ - Gecmis ekrani (Task 18 refactor: main.py'den ayrildi).

Tamamlanmis antrenman oturumlarinin listesini, PR'lari ve hareket bazli
karsilastirmalari gosterir.

UX incelemesi guncellemesi (kullanicidan gelen istek - "Gecmis ekrani hic
sayfalanmiyor/virtualize edilmiyor"): render() ONCEDEN state["history"]'deki
HER oturum icin TAM bir kart widget'i kurup TUMUNU ayni anda bir ScrollView
icine yigiyordu - aylarca kullanildikca (yuzlerce kayit) bu hem ilk
render'da (her seferinde HEPSI YENIDEN kuruluyordu) hem de bellek acisindan
gittikce agirlasirdi. Artik hareket secici popup'inda (Task 17) kullanilan
AYNI RecycleView deseni burada da var: sadece EKRANDA GORUNEN (+ kucuk bir
tampon) kart kadar gercek widget kuruluyor, geri kalani hafif rv.data
sozlukleri olarak bekliyor (bkz. shared._HistorySessionRow).
"""
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.metrics import dp
from kivy.clock import Clock

import core
from shared import (
    MUTED,
    confirm_dialog, label, _HistorySessionRow, history_card_height, _find_scrollview,
)


class HistoryScreen(Screen):
    def on_pre_enter(self):
        self.render()

    def render(self, keep_scroll=False):
        app = App.get_running_app()
        state = app.state
        # RecycleView, kivy.uix.recycleview.RecycleView -> ScrollView alt
        # sinifidir - yani ONCEKI koddaki _find_scrollview() yardimcisi
        # (butun digger ekranlarda kullanilan AYNI "kaydirma konumunu
        # koru" deseni) burada da HICBIR degisiklik gerekmeden calisir.
        prev = _find_scrollview(self)
        prev_scroll_y = prev.scroll_y if (keep_scroll and prev is not None) else None
        self.clear_widgets()

        if not state["history"]:
            col = BoxLayout(orientation="vertical", padding=dp(12))
            col.add_widget(label("Henüz antrenman kaydın yok.", color=MUTED, height=dp(40)))
            self.add_widget(col)
            return

        # KOK NEDEN / DUZELTME (kullanicidan gelen gercek hata, Hareket Seç
        # popup'inda bulundu - bkz. screens/program.py _build_exercise_picker
        # icindeki AYNI hatanin KOK NEDEN notu): rv.viewclass bir AliasProperty
        # ve setter'i "layout_manager varsa ona ata" seklinde calisiyor;
        # rv.add_widget(rv_layout) CAGRILMADAN ONCE layout_manager henuz
        # atanmamis oldugu icin "rv.viewclass = ..." SESSIZCE hicbir sey
        # yapmiyordu - bu ekran da (Gecmis) picker ile AYNI sirayi (once
        # viewclass, sonra add_widget) kullandigi icin ayni sekilde
        # etkileniyordu (kullanici henuz bildirmemis olsa da). Viewclass
        # atamasi artik add_widget(rv_layout)'tan SONRA yapiliyor.
        rv = RecycleView(size_hint=(1, 1))
        rv_layout = RecycleBoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(12),
        )
        rv_layout.bind(minimum_height=rv_layout.setter("height"))
        rv.add_widget(rv_layout)
        rv.viewclass = _HistorySessionRow

        # Gecmis, en YENI oturum en ustte gorunecek sekilde (kullanicidan
        # gelen orijinal davranis) ters kronolojik sirada tutulmuyor olabilir
        # (bkz. core.add) - session_card sirasi ONCEKI kodda state["history"]
        # sirasiyla AYNIYDI, burada da ayni sira korunuyor (davranis degismedi).
        rv.data = [
            {
                "session": s,
                "on_delete": (lambda sid=s["id"]: self.confirm_delete_session(sid)),
                "height": history_card_height(len(s["exercises"])),
                "size_hint_y": None,
            }
            for s in state["history"]
        ]
        self.add_widget(rv)

        if prev_scroll_y is not None:
            def restore(*_):
                rv.scroll_y = prev_scroll_y
            Clock.schedule_once(restore, 0)

    def confirm_delete_session(self, session_id):
        app = App.get_running_app()

        def on_confirm():
            core.remove_history_session(app.state, session_id)
            app.save()
            self.render(keep_scroll=True)

        confirm_dialog(
            "Antrenmanı Sil",
            "Bu antrenman kaydını kalıcı olarak silmek istediğine emin misin? Bu işlem geri alınamaz.",
            on_confirm)
