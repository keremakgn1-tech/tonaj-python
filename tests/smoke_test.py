"""
Tonaj - Kivy arayuzu icin uctan uca "duman testi" (smoke test).

main.py'yi GERCEK bir Kivy Window/Clock ile (xvfb + SDL "dummy" video
suruculeriyle headless olarak) baslatip ekranlar arasinda gercek
dokunma/tiklama olaylari simule eder. core.py'nin aksine bu dosya Kivy'ye
BAGIMLIDIR ve calismasi icin sistemde Kivy + xvfb kurulu olmasini gerektirir
(bkz. .github/workflows/build-apk.yml'deki "UI duman testini calistir" adimi).

Bu dosya, bu oturumda cozulen "kayma" (popup render glitch) hatasi basta
olmak uzere, defalarca elle telefonda test edilerek bulunan davranis
kurallarinin HEPSINI bir daha bozulmadan kalici olarak kod icinde tutar -
daha once SADECE gecici bir calisma dizininde duruyordu ve repoya hic
kaydedilmemisti (kod incelemesinde bulunan bir eksiklik).

Calistirmak icin (repo kokunden): xvfb-run -a python3 tests/smoke_test.py
"""
import os, sys, tempfile, time, traceback
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.recycleview import RecycleView
from kivy.core.window import Window
import main
import core

# KOK NEDEN (once sebepsiz gorunen "Düzenle butonu bulunamadi" tipi
# kaskad hatalari - hepsi tek bir yerden geliyordu): main.get_data_path()
# durumu App.user_data_dir (ör. ~/.config/tonaj/tonaj_state.json) altina
# yaziyor - bu, repo disinda, calisma dizininden BAGIMSIZ, KALICI bir yer.
# Onceki bir duman testi calismasi yarida kesilir/patlarsa (ör. Ctrl-C,
# CI runner'in ani sonlandirilmasi) orada YARIM KALMIS bir aktif seans
# (activeSession) diskte kalabiliyordu; bir SONRAKI test calismasi bu
# eski durumu MIRAS ALIP uygulamayi "planlayici" yerine "aktif seans"
# ekraniyla acardi - butun "Düzenle"/"+ Hareket" vb. testleri bu yuzden
# baştan patlardi (bu calisma dizinindeki tonaj_state.json'i silmek YETERSIZ
# kaliyordu, cunku gercek dosya oradaydi). DUZELTME: her duman testi
# calismasi kendi izole, gecici veri dizinini kullansin - baska hicbir
# calismadan durum miras almasin, boylece test HER ZAMAN temiz/sifir
# durumdan baslar ve calistirilma sirasi/gecmisinden bagimsiz hale gelir.
_smoke_data_dir = tempfile.mkdtemp(prefix="tonaj_smoke_")
main.get_data_path = lambda: os.path.join(_smoke_data_dir, "tonaj_state.json")

errors = []

def safe(step_name, fn):
    try:
        fn()
        print(f"OK   - {step_name}")
    except Exception as e:
        print(f"FAIL - {step_name}: {e!r}")
        traceback.print_exc()
        errors.append((step_name, e))

app = main.TonajApp()
root = app.build()

def click(btn):
    # Simulate a real tap: dispatch press+release like Kivy would.
    btn.dispatch("on_press")
    btn.dispatch("on_release")

def find_text(container, text, exact=True):
    for w in container.walk():
        if hasattr(w, "text"):
            if (w.text == text) if exact else (text in w.text):
                return w
    return None

def find_all_text(container, text):
    return [w for w in container.walk() if hasattr(w, "text") and w.text == text]

def top_popup(title=None):
    for w in reversed(Window.children):
        if isinstance(w, Popup) and (title is None or w.title == title):
            return w
    return None


# KOK NEDEN (Task 17 - hareket secici popup'i RecycleView'e gecti): eskiden
# bu testler popup icindeki her esleşen hareket icin GERCEKTEN olusturulmus
# bir Button widget'ini walk() ile arayip dogrudan tikliyordu - o zaman
# TUM eslesenler (217'ye kadar) her zaman widget agacindaydi. RecycleView
# ise (performans icin, bkz. main.py._PickerRow) SADECE O AN EKRANDA
# GORUNEN satirlar icin gercek widget kurar; listenin geri kalani sadece
# hafif "rv.data" dict'leri olarak var olur. Bu yuzden picker'la ilgili
# testler artik Button widget'lari yerine dogrudan rv.data uzerinden
# calisiyor - bu, GERCEK bir dokunmanin tetikleyecegi AYNI "on_release"
# geri cagirimini calistirdigi icin davranissal olarak birebir esdeger
# (sadece "widget agacinda arama" yerine "veri listesinde arama" oluyor).
def _find_picker_rv(popup):
    for w in popup.walk():
        if isinstance(w, RecycleView):
            return w
    return None


def picker_texts(popup):
    rv = _find_picker_rv(popup)
    return [d.get("text") for d in (rv.data if rv else [])]


def tap_picker_row(popup, text):
    """Bir hareket secici satirina 'dokunmayi' simule eder - eslesen
    rv.data ogesinin 'on_release' geri cagirimini dogrudan cagirir (gercek
    bir Button.dispatch('on_release') ile AYNI kod yolunu tetikler, bkz.
    main.py._PickerRow.on_release)."""
    rv = _find_picker_rv(popup)
    assert rv is not None, "picker RecycleView not found"
    for d in rv.data:
        if d.get("text") == text:
            d["on_release"]()
            return
    raise AssertionError(f"picker row {text!r} not found in rv.data")

print("root:", root)
print("children:", root.children)

sm = None
for w in root.walk():
    if w.__class__.__name__ == "ScreenManager":
        sm = w
        break
print("ScreenManager found:", sm)

def go(screen_name):
    sm.current = screen_name

program_screen = sm.get_screen("program")
history_screen = sm.get_screen("history")
library_screen = sm.get_screen("library")
report_screen = sm.get_screen("report")
settings_screen = sm.get_screen("settings")


def step_program_starts_view_only():
    go("program")
    program_screen.on_pre_enter()
    assert program_screen.edit_mode is False, "program should start in view-only (edit_mode False)"
    # destructive/structural controls must be ABSENT in view mode
    for txt in ("+ GÜN EKLE",):
        assert find_text(program_screen, txt) is None, f"{txt!r} should be hidden outside edit mode"
    edit_btn = find_text(program_screen, "DÜZENLE")
    assert edit_btn is not None, "Düzenle toggle button not found"

safe("program screen starts view-only (edit mode gate)", step_program_starts_view_only)


def step_enter_edit_mode_and_add_day():
    go("program")
    program_screen.render()
    edit_btn = find_text(program_screen, "DÜZENLE")
    assert edit_btn is not None, "Düzenle button not found"
    click(edit_btn)
    assert program_screen.edit_mode is True
    btn = find_text(program_screen, "+ GÜN EKLE")
    assert btn is not None, "gun ekle button not found after entering edit mode"
    click(btn)

safe("enter edit mode -> add day", step_enter_edit_mode_and_add_day)


def step_add_exercise_via_picker():
    go("program")
    program_screen.render()
    assert program_screen.edit_mode is True, "edit mode should persist across renders"
    btn = find_text(program_screen, "+ Hareket")
    assert btn is not None, "+ Hareket button not found in edit mode"
    click(btn)
    Clock.tick()

safe("open exercise picker", step_add_exercise_via_picker)


def step_expanded_exercise_library_is_wired_up():
    popup = top_popup()
    assert popup is not None, "picker popup not found"
    names = core.all_exercise_names(app.state)
    assert len(names) >= 217, f"expected expanded library (>=217), got {len(names)}"
    # Machine and free-weight variants must both exist for the same movement.
    assert "Barbell Shrug" in names and "Machine Shrug" in names, \
        "expected both barbell and machine shrug variants"
    assert "Smith Machine Squat" in names or "Smith Machine Bench Press" in names, \
        "expected at least one Smith Machine variant"
    assert "Trapez" in core.MUSCLE_GROUPS, "Trapez muscle group missing"
    assert core.MUSCLE_GROUP_DEFAULTS.get("Barbell Shrug") == ["Trapez"], \
        "Barbell Shrug should map to Trapez"
    # Every row wired into the picker's RecycleView data must be a real,
    # tap-able exercise name pulled from the (now much larger) library - not
    # stale UI. (Task 17: only visible rows are ever instantiated as actual
    # Button widgets, so we check the data feeding the list, not the widget
    # tree - see tap_picker_row()/picker_texts() above.)
    assert "Barbell Shrug" in picker_texts(popup), "Barbell Shrug not wired into picker data"
    # close this picker without selecting, so later steps get a clean popup
    for w in list(Window.children):
        if isinstance(w, Popup):
            # animation=False: animasyonlu dismiss() widget'i Window'dan
            # ANINDA kaldirmiyor (fade animasyonu bitince kaldiriyor) - tek
            # bir Clock.tick() bunu bitirmeye yetmiyor, sonraki adimlarda
            # Window.children'da HAYALET bir popup kalip top_popup()'in
            # yanlis popup'i bulmasina sebep olabiliyordu.
            w.dismiss(animation=False)

safe("expanded exercise library (217+) wired into picker UI", step_expanded_exercise_library_is_wired_up)


def step_reopen_picker_after_library_check():
    go("program")
    program_screen.render()
    btn = find_text(program_screen, "+ Hareket")
    assert btn is not None, "+ Hareket button not found in edit mode"
    click(btn)
    Clock.tick()

safe("reopen exercise picker", step_reopen_picker_after_library_check)


def step_search_filters_exercise_list():
    # NOT: picker'in kendi "‹ Geri" butonu kaldirildi (kullanici geri
    # bildirimiyle - asil ihtiyac hareket SECTIKTEN SONRA, Hedef ekraninda).
    # Bu listeyi hicbir sey secmeden kapatmak artik sadece popup'in disina
    # dokunmakla (auto_dismiss=True) oluyor - burada onu dogrudan
    # popup.dismiss() ile simule ediyoruz.
    popup = top_popup()
    assert popup is not None, "picker popup not found (search test)"
    search_widgets = [w for w in popup.walk() if isinstance(w, TextInput)]
    assert len(search_widgets) == 1, f"expected exactly one search TextInput, got {len(search_widgets)}"
    search = search_widgets[0]

    # Task 17: the filtered list lives in the picker RecycleView's `data`,
    # not as one real Button per match (see picker_texts() above) - only
    # visible rows are ever instantiated as widgets.
    before = picker_texts(popup)
    assert len(before) >= 217, f"expected full list before typing, got {len(before)}"

    search.text = "Barbell Shrug"
    Clock.tick()
    matches = [n for n in picker_texts(popup) if n == "Barbell Shrug"]
    assert matches, "typing an exact name should surface it in the filtered list"
    others = [n for n in picker_texts(popup) if n != "Barbell Shrug"]
    assert not others, f"search should filter OUT non-matching exercises, {len(others)} left over"

    search.text = "zzz-no-such-exercise-zzz"
    Clock.tick()
    assert picker_texts(popup) == [], "an unmatched query should show zero exercise rows"

    search.text = ""
    Clock.tick()
    after = picker_texts(popup)
    assert len(after) == len(before), "clearing the search box should restore the full list"

    popup.dismiss(animation=False)
    assert top_popup() is None, "dismissing (tap-outside equivalent) should close the picker without picking anything"

safe("search box filters exercise list + tap-outside closes popup", step_search_filters_exercise_list)


def step_reopen_picker_for_back_button_test():
    go("program")
    program_screen.render()
    btn = find_text(program_screen, "+ Hareket")
    assert btn is not None, "+ Hareket button not found in edit mode"
    click(btn)
    Clock.tick()

safe("reopen exercise picker for Hedef back-button test", step_reopen_picker_for_back_button_test)


def step_hedef_back_button_returns_to_picker():
    # KOK NEDEN: kullanici "Geri" butonunun hareket arama listesinde degil,
    # bir hareket SECTIKTEN SONRA (Hedef ekraninda, "vazgecip baska hareket
    # seçeyim" icin) olmasi gerektigini bildirdi. Bu test, YENI bir hareket
    # secilince Hedef popup'inda "‹ Geri" oldugunu VE gercekten tekrar
    # hareket listesini actigini dogruluyor.
    popup = top_popup()
    assert popup is not None, "picker popup not found"
    items = picker_texts(popup)
    assert items, "no exercise rows in picker"
    picked_name = items[0]
    tap_picker_row(popup, picked_name)
    # Hedef popup artik dismiss()'ten bir Clock karesi SONRA aciliyor (bkz.
    # pick() icindeki Clock.schedule_once(open_next, 0)) - araya bilerek
    # sokulan kare sinirini burada Clock.tick() ile geciyoruz.
    Clock.tick()

    hedef_popup = top_popup("Hedef")
    assert hedef_popup is not None, "Hedef popup should open one Clock tick after dismiss (no search was used)"
    back_btn = find_text(hedef_popup, "‹ GERİ")
    assert back_btn is not None, "Hedef popup should show a '‹ Geri' button for a newly-picked exercise"
    click(back_btn)
    # do_back() artik on_back()'i (picker'i acan cagri) bir Clock karesi
    # sonraya erteliyor (bkz. do_back() icindeki KOK NEDEN notu).
    Clock.tick()

    reopened_picker = top_popup()
    assert reopened_picker is not None and reopened_picker.title == "Hareket Seç", \
        "clicking '‹ Geri' in Hedef should reopen the exercise picker"
    # secilen hareket program gunune KAYDEDILMEMIS olmali (sadece goz atildi)
    day = app.state["program"]["days"][0]
    assert not any(e["name"] == picked_name for e in day["exercises"]), \
        "going back without saving should not have added the exercise to the day"

    reopened_picker.dismiss(animation=False)

safe("Hedef popup's '‹ Geri' returns to the exercise picker (new-pick flow only)",
     step_hedef_back_button_returns_to_picker)


def step_actually_save_one_exercise_for_edit_test():
    # Onceki testler bilerek KAYDETMEDEN vazgecti (Geri / disariya dokunma) -
    # "varolan hareketi duzenleme" testinin calisabilmesi icin gunde
    # GERCEKTEN kayitli en az bir hareket olmasi lazim.
    go("program")
    program_screen.render()
    btn = find_text(program_screen, "+ Hareket")
    assert btn is not None, "+ Hareket button not found"
    click(btn)
    Clock.tick()
    popup = top_popup()
    assert popup is not None, "picker popup not found"
    items = picker_texts(popup)
    assert items, "no exercise rows in picker"
    name_to_save = items[0]
    tap_picker_row(popup, name_to_save)
    Clock.tick()  # Hedef popup bir kare sonra acilir (bkz. KOK NEDEN 3)

    hedef_popup = top_popup("Hedef")
    assert hedef_popup is not None, "Hedef popup not found"
    save_btn = find_text(hedef_popup, "KAYDET")
    assert save_btn is not None, "Kaydet button not found"
    click(save_btn)

    day = app.state["program"]["days"][0]
    assert any(e["name"] == name_to_save for e in day["exercises"]), \
        "exercise should now be actually saved in the day"

safe("actually save a picked exercise (setup for edit-existing test)",
     step_actually_save_one_exercise_for_edit_test)


def step_editing_existing_exercise_has_no_back_button():
    # KOK NEDEN: gundeki VAROLAN bir harekete dokunup hedefini duzenlerken
    # donulecek bir "onceki liste ekrani" yok - orada "‹ Geri" GORUNMEMELI.
    go("program")
    program_screen.render()
    day = app.state["program"]["days"][0]
    assert day["exercises"], "expected at least one exercise already in the day to edit"
    existing_name = day["exercises"][0]["name"]
    # NOT: find_text() burada da (arama kutusu vakasindaki gibi) yanlis
    # widget'i buluyor - satirin kendisi (ClickableRow, on_release burada
    # bagli) bir .text ozelligine sahip degil, ama icindeki isim Label'i
    # var VE onun .text'i eslesiyor. Label'a tiklamak (on_press yok)
    # KeyError verir - asil tiklanmasi gereken, Label'in EBEVEYNI olan satir.
    name_lbl = find_text(program_screen, existing_name)
    assert name_lbl is not None, f"row label for existing exercise {existing_name!r} not found"
    row_btn = name_lbl.parent
    assert row_btn is not None
    click(row_btn)

    hedef_popup = top_popup("Hedef")
    assert hedef_popup is not None, "Hedef popup should open when editing an existing exercise"
    back_btn = find_text(hedef_popup, "‹ GERİ")
    assert back_btn is None, "editing an EXISTING exercise's target should NOT show a '‹ Geri' button"
    hedef_popup.dismiss(animation=False)

safe("editing an existing exercise's target has no '‹ Geri' button",
     step_editing_existing_exercise_has_no_back_button)


def step_reopen_picker_after_search_test():
    go("program")
    program_screen.render()
    btn = find_text(program_screen, "+ Hareket")
    assert btn is not None, "+ Hareket button not found in edit mode"
    click(btn)
    Clock.tick()

safe("reopen exercise picker after search test", step_reopen_picker_after_search_test)


def step_picking_via_focused_search_waits_for_window_resize():
    # KOK NEDEN testi (v2 - sabit sureli bekleme YETERSIZ CIKTI, kullanici
    # ayni kaymayi tekrar bildirdi): arama kutusu odaktayken (klavye acik
    # varsayimiyla) bir sonuca dokununca, Hedef popup'i pencere GERCEKTEN
    # eski (klavyesiz) yuksekligine DONENE KADAR acilmamali - sabit bir
    # sure tahmin etmek yerine Window.on_resize event'i bekleniyor artik.
    # Burada Window.size'i ELLE kucultup buyuterek klavyenin
    # acilip/kapanmasini simule ediyoruz (xvfb ortaminda gercek IME yok).
    popup = top_popup()
    assert popup is not None, "picker popup not found"
    search_widgets = [w for w in popup.walk() if isinstance(w, TextInput)]
    assert len(search_widgets) == 1
    search = search_widgets[0]
    search.text = "Ab Wheel Rollout"
    Clock.tick()
    search.focus = True  # klavye acikmis gibi davran

    full_w, full_h = Window.size
    Window.size = (full_w, full_h - 300)  # "klavye acildi, pencere kucüldu"

    # Task 17: picker satirlari artik rv.data uzerinden - tap_picker_row()
    # gercek bir dokunmanin tetikleyecegi AYNI on_release callback'ini
    # cagirir (bkz. bu dosyanin basindaki tap_picker_row() notu).
    assert "Ab Wheel Rollout" in picker_texts(popup), "expected exact-match exercise row"
    tap_picker_row(popup, "Ab Wheel Rollout")

    # Picker popup'i ANINDA kapanmali (animasyonsuz).
    assert top_popup() is popup or top_popup() is None
    Clock.tick()
    still_no_hedef = top_popup("Hedef")
    assert still_no_hedef is None, \
        "pencere HALA kucukken (klavye 'acik') Hedef popup'i acilmamali"

    # Klavye "kapanmis" gibi pencereyi eski boyutuna geri getiriyoruz - bu,
    # gercek cihazda Android'in adjustResize ile yaptigi seyin (klavye
    # kapaninca pencerenin eski boyutuna donmesinin) simulasyonu. Bu,
    # Window.on_resize event'ini tetiklemeli ve KOD BUNU YAKALAYIP Hedef
    # popup'ini simdi acmali - sabit bir sure BEKLEMEDEN.
    Window.size = (full_w, full_h)
    # on_resize_cb senkron tetiklenir ama artik on_pick'i dogrudan degil
    # Clock.schedule_once(open_next, 0) ile bir kare SONRA cagiriyor (bkz.
    # pick() icindeki KOK NEDEN 3 notu) - o kareyi burada geciyoruz.
    Clock.tick()
    hedef_popup = top_popup("Hedef")
    assert hedef_popup is not None, \
        "pencere eski (klavyesiz) yuksekligine donunce Hedef popup'i bir kare sonra (resize event'iyle) acilmis olmali"
    hedef_popup.dismiss(animation=False)  # secmeden temizle

safe("picking via a focused search box waits for the real window resize (not a fixed delay)",
     step_picking_via_focused_search_waits_for_window_resize)


def step_picking_via_focused_search_has_safety_net_timeout():
    # Eger resize event HIC gelmezse (bazi cihaz/durumlarda olabilir),
    # sonsuza kadar beklemek yerine 1.5sn'lik bir guvenlik agi devreye
    # girip Hedef popup'ini yine de acmali.
    go("program")
    program_screen.render()
    btn = find_text(program_screen, "+ Hareket")
    assert btn is not None
    click(btn)
    Clock.tick()
    popup = top_popup()
    assert popup is not None
    search_widgets = [w for w in popup.walk() if isinstance(w, TextInput)]
    assert len(search_widgets) == 1
    search = search_widgets[0]
    search.text = "Arnold Press"
    Clock.tick()
    search.focus = True

    full_w, full_h = Window.size
    Window.size = (full_w, full_h - 300)  # klavye "acik" kalsin, hic kapanmayacak

    assert "Arnold Press" in picker_texts(popup)
    tap_picker_row(popup, "Arnold Press")
    Clock.tick()
    assert top_popup("Hedef") is None, "resize gelmeden hemen acilmamali"

    time.sleep(1.6)
    Clock.tick()
    # guvenlik agi (proceed) artik on_pick'i dogrudan degil
    # Clock.schedule_once(open_next, 0) ile bir kare SONRA cagiriyor - o
    # kareyi burada geciyoruz.
    Clock.tick()
    hedef_popup = top_popup("Hedef")
    assert hedef_popup is not None, \
        "resize event hic gelmese bile guvenlik agi (1.5sn) sonunda Hedef acilmis olmali"
    hedef_popup.dismiss(animation=False)
    Window.size = (full_w, full_h)  # sonraki testler icin pencereyi duzelt

safe("safety-net timeout opens Hedef even if the resize event never fires",
     step_picking_via_focused_search_has_safety_net_timeout)


def step_reopen_picker_after_focused_search_test():
    go("program")
    program_screen.render()
    btn = find_text(program_screen, "+ Hareket")
    assert btn is not None, "+ Hareket button not found in edit mode"
    click(btn)
    Clock.tick()

safe("reopen exercise picker after focused-search test", step_reopen_picker_after_focused_search_test)


def step_pick_first_exercise_and_open_target_editor():
    popup = top_popup()
    assert popup is not None, "picker popup not found"
    names = core.all_exercise_names(app.state)
    first_name = sorted(names)[0]
    assert first_name in picker_texts(popup), f"exercise row {first_name!r} not found"
    tap_picker_row(popup, first_name)
    # Hedef popup artik bir Clock karesi sonra aciliyor (bkz. KOK NEDEN 3).
    Clock.tick()

safe("pick exercise -> open target editor", step_pick_first_exercise_and_open_target_editor)


def step_use_steppers_in_target_editor_and_save():
    popup = top_popup("Hedef")
    assert popup is not None, "Hedef popup not found"
    plus_buttons = find_all_text(popup, "+")
    minus_buttons = [w for w in popup.walk() if hasattr(w, "text") and w.text in ("−", "-")]
    assert len(plus_buttons) == 6, f"expected 6 plus buttons, got {len(plus_buttons)}"
    assert len(minus_buttons) == 6, f"expected 6 minus buttons, got {len(minus_buttons)}"
    for b in plus_buttons:
        click(b); click(b)
    b = plus_buttons[0]
    b.dispatch("on_press")
    for _ in range(3):
        Clock.tick()
    b.dispatch("on_release")
    for b in minus_buttons:
        click(b)
    save_btn = find_text(popup, "KAYDET")
    assert save_btn is not None, "Kaydet button not found"
    click(save_btn)

safe("use +/- steppers in Hedef popup + save", step_use_steppers_in_target_editor_and_save)


def step_view_mode_hides_edit_controls_for_exercise_row():
    go("program")
    program_screen.edit_mode = False
    program_screen.render()
    assert find_text(program_screen, "+ Hareket") is None
    assert find_text(program_screen, "Kopya") is None
    # BAŞLA must still be visible (view mode is not a dead end)
    assert find_text(program_screen, "BAŞLA") is not None

safe("view mode hides edit-only controls, keeps BAŞLA", step_view_mode_hides_edit_controls_for_exercise_row)


def step_start_session():
    go("program")
    program_screen.render()
    start_btn = find_text(program_screen, "BAŞLA")
    assert start_btn is not None, "BAŞLA button not found"
    click(start_btn)
    program_screen.render()

safe("start session", step_start_session)


def step_add_set_via_stepper():
    go("program")
    plus_buttons = find_all_text(program_screen, "+")
    assert len(plus_buttons) >= 3, f"expected >=3 plus buttons in active session, got {len(plus_buttons)}"
    for b in plus_buttons[:3]:
        for _ in range(3):
            click(b)
    add_set_btn = find_text(program_screen, "+ SETİ EKLE")
    assert add_set_btn is not None, "+ Seti Ekle button not found"
    click(add_set_btn)

safe("log a set via +/- steppers", step_add_set_via_stepper)


def step_remove_set():
    go("program")
    rm_buttons = find_all_text(program_screen, "×")
    assert rm_buttons, "no remove (x) buttons found"
    click(rm_buttons[-1])

safe("remove a set", step_remove_set)


def step_add_adhoc_exercise_during_session():
    go("program")
    btn = find_text(program_screen, "+ HAREKET EKLE")
    assert btn is not None, "+ HAREKET EKLE not found"
    click(btn)
    Clock.tick()
    popup = top_popup("Hareket Ekle")
    assert popup is not None, "Hareket Ekle popup not found"
    names = core.all_exercise_names(app.state)
    other_name = sorted(names)[1]
    assert other_name in picker_texts(popup), f"row for {other_name!r} not found"
    tap_picker_row(popup, other_name)

safe("add adhoc exercise during session", step_add_adhoc_exercise_during_session)


def step_remove_exercise_requires_confirm():
    go("program")
    program_screen.render()
    rm_ex_buttons = find_all_text(program_screen, "×")
    assert rm_ex_buttons, "no exercise-remove (x) buttons found"
    before = len(app.state["activeSession"]["exercises"])
    click(rm_ex_buttons[0])  # should only OPEN a confirm popup, not remove yet
    after_click = len(app.state["activeSession"]["exercises"])
    assert after_click == before, "exercise was removed WITHOUT confirmation (regression)"
    popup = top_popup("Hareketi Çıkar")
    assert popup is not None, "confirm popup for exercise removal not found"
    vazgec = find_text(popup, "VAZGEÇ")
    assert vazgec is not None
    click(vazgec)  # cancel -> nothing removed
    assert len(app.state["activeSession"]["exercises"]) == before, "cancel should not remove the exercise"
    # now really confirm removal
    click(rm_ex_buttons[0])
    popup = top_popup("Hareketi Çıkar")
    assert popup is not None
    evet = find_text(popup, "EVET, ÇIKAR")
    assert evet is not None, "confirm (Evet, Çıkar) button not found"
    click(evet)
    assert len(app.state["activeSession"]["exercises"]) == before - 1, "exercise should be removed after confirming"

safe("removing an exercise mid-session requires confirmation", step_remove_exercise_requires_confirm)


def step_discard_session_requires_confirm():
    go("program")
    program_screen.render()
    discard_btn = find_text(program_screen, "ANTRENMANI SİL")
    assert discard_btn is not None, "Antrenmanı Sil button not found"
    assert app.state["activeSession"] is not None
    click(discard_btn)  # should only open a confirm popup
    assert app.state["activeSession"] is not None, "session was discarded WITHOUT confirmation (regression)"
    popup = top_popup("Antrenmanı Sil")
    assert popup is not None, "confirm popup for discard not found"
    vazgec = find_text(popup, "VAZGEÇ")
    click(vazgec)
    assert app.state["activeSession"] is not None, "cancel should not discard the session"
    # now really confirm discard
    click(discard_btn)
    popup = top_popup("Antrenmanı Sil")
    assert popup is not None
    evet = find_text(popup, "EVET, SİL")
    assert evet is not None
    click(evet)
    assert app.state["activeSession"] is None, "session should be discarded after confirming"

safe("discarding the active session requires confirmation", step_discard_session_requires_confirm)


def step_start_and_finish_session_normally():
    go("program")
    program_screen.render()
    start_btn = find_text(program_screen, "BAŞLA")
    assert start_btn is not None
    click(start_btn)
    program_screen.render()
    finish_btn = find_text(program_screen, "ANTRENMANI BİTİR VE KAYDET")
    assert finish_btn is not None, "finish button not found"
    click(finish_btn)
    assert app.state["activeSession"] is None
    assert app.state["history"], "finished session should land in history"

safe("start and finish a session normally", step_start_and_finish_session_normally)


def step_visit_other_screens():
    for name, screen in (("history", history_screen), ("library", library_screen),
                          ("report", report_screen), ("settings", settings_screen)):
        go(name)
        screen.on_pre_enter()

safe("visit history/library/report/settings screens", step_visit_other_screens)


def step_hardware_back_button_returns_to_program_tab():
    # KOK NEDEN: Android'in fiziksel/gesture geri tusu ONCEDEN "program"
    # disindaki bir sekmedeyken dogrudan UYGULAMAYI KAPATIYORDU (Kivy'nin
    # acik Popup yokken varsayilan davranisi budur). Simdi RootWidget bunu
    # yakalayip once "program" sekmesine donduruyor (return True = tuketildi,
    # uygulama kapanmiyor), "program" sekmesindeyken ise varsayilan
    # davranisa (return False = uygulamadan cik) izin veriyor.
    go("history")
    assert sm.current == "history"
    consumed = root._on_keyboard(Window, 27)
    assert consumed is True, "gecmis sekmesindeyken geri tusu tuketilmeli (uygulama kapanmamali)"
    assert sm.current == "program", "geri tusu once program sekmesine donmeli"

    consumed_again = root._on_keyboard(Window, 27)
    assert consumed_again is False, \
        "zaten program sekmesindeyken geri tusu tuketilmemeli (Android'in normal 'uygulamadan cik' davranisi calismali)"

safe("hardware back button returns to program tab first", step_hardware_back_button_returns_to_program_tab)


def step_toast_queue_does_not_overwrite_pending_messages():
    # KOK NEDEN: art arda iki toast (orn. iki ayri harekette ust uste PR)
    # gelince ikincisi birincinin ustune yazip birincisini kullaniciya hic
    # gosterilmeden kaybettiriyordu - artik bir kuyrukta birikip sirayla
    # gosteriliyorlar.
    root._toast_queue.clear()
    root.toast_label.opacity = 0
    root.show_toast("Birinci mesaj")
    assert root._toast_queue == ["Birinci mesaj"]
    assert root.toast_label.text == "Birinci mesaj"
    assert root.toast_label.opacity == 1

    root.show_toast("İkinci mesaj")
    assert root._toast_queue == ["Birinci mesaj", "İkinci mesaj"], \
        "ikinci mesaj kuyruga eklenmeli, birinciyi silmemeli"
    assert root.toast_label.text == "Birinci mesaj", \
        "ikinci mesaj gelince ekrandaki BIRINCI mesaj degismemeli"

    # KOK NEDEN (bu testte gozlemlenen flaky basarisizlik): _advance_toast_queue
    # bir sonraki toast'i Clock.schedule_once(self._show_next_toast, 0.3) ile
    # 0.3s SONRA gostermek uzere zamanliyor - test bunu once sabit bir sure
    # (0.31s, sonra 0.5s) uyuyup Clock.tick() cagirarak "simule" etmeye
    # calisiyordu. Ama Kivy'nin Clock'u dt'yi GERCEK duvar saatine gore, EN
    # SON tick() cagrisindan bu yana gecen sureyle hesapliyor - bu smoke
    # testinin GERISINDE, bu adimdan cok once, baska adimlarda (orn.
    # time.sleep(1.6) kullanan toast-suresi testi) Clock.tick() cagrilmadan
    # gecen gercek sureler BIRIKIYOR. Sonuc: bu adimdaki ILK Clock.tick()
    # cagrisi bazen (ortamin hizina/yukune bagli olarak degisken sekilde)
    # tek basina hem 0.3s'lik hem de "bir sonraki" 1.6s'lik zamanlanmis geri
    # cagirmayi ayni anda ateşleyebiliyordu - kuyruk beklenenden erken
    # BOŞALIYORDU (assert root._toast_queue == ["İkinci mesaj"] rastgele
    # basarisiz oluyordu). Gercek zamana (sleep/tick) bagli kalmak yerine,
    # 0.3s'lik zamanlayicinin SÜRESİ DOLDUĞUNDA calisacak fonksiyonu
    # (_show_next_toast) DOGRUDAN cagirarak ayni davranisi (kuyruktaki
    # sonraki mesajin gosterilmesi, kuyrugun degismesi) sifir zamanlama
    # belirsizligiyle dogruluyoruz.
    root._advance_toast_queue()  # birincinin suresi doldu -> kuyruktan cikar, 0.3s sonrasi icin zamanlar
    assert root._toast_queue == ["İkinci mesaj"], \
        "birinci mesaj kuyruktan cikmali, ikincisi kuyrukta beklemeli"
    root._show_next_toast()  # 0.3s'lik zamanlayicinin SÜRESİ DOLDUĞUNDA calisacak olan
    assert root.toast_label.text == "İkinci mesaj", "sirada bekleyen ikinci mesaj simdi gosterilmeli"
    assert root._toast_queue == ["İkinci mesaj"]

    root._advance_toast_queue()
    assert root._toast_queue == [], "kuyruk sonunda bos kalmali"

safe("toast queue shows messages in order without overwriting", step_toast_queue_does_not_overwrite_pending_messages)


def step_settings_shows_build_stamp():
    # KOK NEDEN: APP_VERSION hicbir zaman degismiyordu, kullanici hangi
    # APK'nin telefonunda kurulu oldugunu dogrulayamiyordu. Ayarlar >
    # Hakkinda'da artik bir "Build: ..." satiri olmali (CI disinda,
    # bu testte oldugu gibi, placeholder olarak gorunur - o da kabul).
    go("settings")
    settings_screen.on_pre_enter()
    build_lbl = find_text(settings_screen, "Build: " + main.BUILD_STAMP, exact=True)
    assert build_lbl is not None, "Ayarlar ekraninda 'Build: ...' satiri bulunamadi"

safe("settings screen shows a build stamp", step_settings_shows_build_stamp)


def step_font_scale_setting_persists_and_applies():
    # Task 21 - yazi tipi boyutu ayari: Ayarlar > "Büyük" secilince
    # app.state["settings"]["fontScale"] guncellenmeli, kalici olarak
    # kaydedilmeli (app.save() cagrilmali) VE shared.sp_() bir SONRAKI
    # cagrisinda bu yeni degeri yansitmali (bkz. shared.font_scale()
    # deki "weight_unit() ile ayni desen" notu - ayri bir global/cache
    # yok, her seferinde app.state'ten canli okunuyor).
    from shared import sp_, tr_upper
    import kivy.metrics as kivy_metrics

    go("settings")
    settings_screen.on_pre_enter()

    normal_sp16 = sp_(16)

    # styled_button() gorunen metni tr_upper() ile BUYUK harfe cevirir
    # (bkz. o fonksiyondaki not) - button.text "Büyük" degil "BÜYÜK" olur.
    buyuk_btn = find_text(settings_screen, tr_upper("Büyük"), exact=True)
    assert buyuk_btn is not None, "Ayarlar ekraninda 'Büyük' yazi boyutu butonu bulunamadi"
    click(buyuk_btn)

    assert app.state["settings"]["fontScale"] == 1.2, \
        "Büyük secilince fontScale 1.2 olarak kaydedilmeli"
    # app.save() gercekte debounce edilmis (0.5s sonra, ayri bir thread'de
    # yazan) bir Clock.schedule_once - bkz. TonajApp.save()'deki KOK NEDEN
    # notu. Testte gercek 0.5s+thread beklemek yerine, o zamanlayici
    # ateslendiginde calisacak olan _flush_save()'i DOGRUDAN cagirip ayni
    # yazmayi senkron/deterministik olarak tetikliyoruz.
    if app._save_pending is not None:
        app._save_pending.cancel()
    app._flush_save()
    # _flush_save() asil dosya yazmasini AYRI BIR THREAD'e devrediyor (bkz.
    # oradaki KOK NEDEN notu) - yani cagirdiktan hemen sonra dosya HENUZ
    # yazilmamis olabilir. Sabit bir sleep yerine, kisa araliklarla dosyayi
    # okuyup beklenen degeri gorene kadar (ya da makul bir sure sonra
    # pes edip asagidaki assert'in patlamasina izin vererek) bekliyoruz.
    for _ in range(50):
        try:
            _probe, _n, _r = core.load_state(main.get_data_path())
            if _probe.get("settings", {}).get("fontScale") == 1.2:
                break
        except Exception:
            pass
        time.sleep(0.05)

    buyuk_sp16 = sp_(16)
    assert buyuk_sp16 > normal_sp16, \
        "fontScale buyuyunce sp_() de daha buyuk bir piksel degeri dondurmeli"
    assert abs(buyuk_sp16 - kivy_metrics.sp(16) * 1.2) < 0.01

    # Ekran gercekten yeniden render edildi mi (secili buton artik
    # vurgulanmis mi) - on_pre_enter zaten render() cagiriyor, click()
    # de set_font_scale() icinde self.render() cagiriyor, yeni bir
    # on_pre_enter'a gerek yok.
    buyuk_btn_after = find_text(settings_screen, tr_upper("Büyük"), exact=True)
    assert buyuk_btn_after is not None

    # Kaydin GERCEKTEN kalici oldugunu (sadece bellekte degil) dogrula -
    # core.load_state ile diskten TEKRAR oku.
    saved, _is_new, _recovered = core.load_state(main.get_data_path())
    assert saved["settings"]["fontScale"] == 1.2, \
        "fontScale diske kaydedilmemis (app.save() calismamis olabilir)"

    # Sonraki testleri etkilememesi icin Normal'a geri don.
    normal_btn = find_text(settings_screen, tr_upper("Normal"), exact=True)
    assert normal_btn is not None
    click(normal_btn)
    assert app.state["settings"]["fontScale"] == 1.0
    assert abs(sp_(16) - normal_sp16) < 0.01, "Normal'a donunce eski sp_() degerine donmeli"

safe("settings: font-size (yazı tipi boyutu) setting persists and applies to sp_()",
     step_font_scale_setting_persists_and_applies)


def step_delete_day():
    go("program")
    program_screen.edit_mode = True
    program_screen.render()
    days = app.state["program"]["days"]
    if days:
        program_screen.confirm_delete_day(days[0]["id"])
        popup = top_popup("Günü Sil")
        assert popup is not None
        yes_btn = find_text(popup, "EVET, SİL")
        assert yes_btn is not None, "Evet Sil button not found"
        click(yes_btn)

safe("delete day flow", step_delete_day)


def step_settings_export_import_desktop():
    go("settings")
    settings_screen.on_pre_enter()
    settings_screen.export_backup()  # platform != android -> writes to cwd
    import glob
    files = glob.glob("tonaj-yedek-*.json")
    assert files, "backup file not created"
    for f in files:
        os.remove(f)

safe("settings: export backup (desktop path)", step_settings_export_import_desktop)


def step_settings_reset_confirm_popup():
    go("settings")
    settings_screen.confirm_reset_all()
    popup = top_popup("Tüm Verileri Sıfırla")
    assert popup is not None
    vazgec = find_text(popup, "VAZGEÇ")
    assert vazgec is not None
    click(vazgec)

safe("settings: open reset confirm popup", step_settings_reset_confirm_popup)


print()
print("=" * 60)
if errors:
    print(f"{len(errors)} STEP(S) FAILED:")
    for name, e in errors:
        print(f" - {name}: {e!r}")
    sys.exit(1)
else:
    print("ALL STEPS PASSED")
