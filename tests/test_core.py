"""
Tonaj - core.py icin otomatik test paketi.

KOK NEDEN (kod incelemesinde bulundu - "hic otomatik test yok"): core.py
bilerek Kivy'den bagimsiz tasarlanmis (dosyanin kendi docstring'i de bunu
soyluyor) ama bu potansiyel hic kullanilmiyordu - main.py'nin UI degisiklikleri
sirasinda is mantiginin sessizce bozulup bozulmadigini anlamanin hicbir hizli
yolu yoktu. Bu dosya, kod incelemesinde "regresyon riski en yuksek" olarak
isaretlenen ucaklari (kayit/okuma, onerilen agirlik/PR mantigi, gecmis
karsilastirma dallanmalari) ve genel CRUD islemlerini kapsar.

Calistirmak icin: python3 -m pytest tests/ -v  (repo kokunden)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------
def make_set(weight, reps, is_warmup=False, rir=None):
    s = {"weight": weight, "reps": reps}
    if is_warmup:
        s["isWarmup"] = True
    if rir is not None:
        s["rir"] = rir
    return s


def make_history_session(name, sets, started_at=1000, day_id=None, is_deload=False,
                          session_id="s1", target=None):
    ex = {"name": name, "sets": sets}
    if target:
        ex.update(target)
    return {
        "id": session_id, "startedAt": started_at, "dayId": day_id,
        "dayName": None, "isDeload": is_deload, "exercises": [ex], "note": "",
    }


# ---------------------------------------------------------------------------
# default_state / save_state / load_state
# ---------------------------------------------------------------------------
def test_default_state_shape():
    s = core.default_state()
    assert s["activeSession"] is None
    assert s["history"] == []
    assert s["program"] == {"days": []}
    assert s["library"] == []
    assert s["settings"]["fontScale"] == 1.0


def test_save_and_load_round_trip(tmp_path):
    path = str(tmp_path / "tonaj_state.json")
    state = core.default_state()
    state["library"].append("Özel Hareket")
    core.save_state(path, state)

    loaded, is_new, recovered = core.load_state(path)
    assert is_new is False
    assert recovered is False
    assert loaded["library"] == ["Özel Hareket"]


def test_load_state_creates_default_when_missing(tmp_path):
    path = str(tmp_path / "does_not_exist.json")
    state, is_new, recovered = core.load_state(path)
    assert is_new is True
    assert recovered is False
    assert state["program"]["days"] == []
    assert os.path.exists(path)  # ilk acilista dosya olusturulmus olmali


def test_load_state_recovers_from_corrupt_json(tmp_path):
    # KOK NEDEN regresyon testi: bozuk JSON'un uygulamayi KALICI olarak
    # cokertmemesi gerekiyor - bkz. core.load_state icindeki not.
    path = str(tmp_path / "tonaj_state.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{bu gecerli bir json degil!!!")

    state, is_new, recovered = core.load_state(path)
    assert recovered is True
    assert is_new is True
    assert state["program"]["days"] == []
    # bozuk dosya SILINMEMIS, yeniden adlandirilmis olmali
    corrupt_files = [f for f in os.listdir(tmp_path) if ".corrupt-" in f]
    assert len(corrupt_files) == 1
    # ve yeni, gecerli bir dosya yerine yazilmis olmali
    assert os.path.exists(path)
    with open(path) as f:
        import json
        json.load(f)  # patlamamali


def test_load_state_recovers_when_json_is_not_a_dict(tmp_path):
    path = str(tmp_path / "tonaj_state.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("[1, 2, 3]")  # gecerli JSON ama dict degil

    state, is_new, recovered = core.load_state(path)
    assert recovered is True
    assert state["history"] == []


def test_load_state_repairs_minor_inner_problems_without_losing_data(tmp_path):
    # ic yapida kucuk hata (sets liste degil): eskiden TUM dosya kenara alinip
    # veri kayboluyordu; artik onarilir ve gecmis korunur.
    path = str(tmp_path / "tonaj_state.json")
    import json
    bad = core.default_state()
    bad["history"] = [{"id": "x", "startedAt": 1, "exercises": [
        {"name": "Bench Press", "sets": "bu bir liste olmali ama string"}
    ]}]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bad, f)

    state, is_new, recovered = core.load_state(path)
    assert recovered is False
    assert len(state["history"]) == 1
    assert state["history"][0]["exercises"][0]["sets"] == []


def test_load_state_recovers_when_structure_is_invalid(tmp_path):
    path = str(tmp_path / "tonaj_state.json")
    import json
    bad = core.default_state()
    bad["history"] = "liste degil"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bad, f)
    state, is_new, recovered = core.load_state(path)
    assert recovered is True
    assert state["history"] == []


# ---------------------------------------------------------------------------
# validate_state_schema
# ---------------------------------------------------------------------------
def test_validate_state_schema_accepts_default_state():
    core.validate_state_schema(core.default_state())  # patlamamali


def test_validate_state_schema_rejects_non_dict():
    with pytest.raises(ValueError):
        core.validate_state_schema([1, 2, 3])


def test_validate_state_schema_rejects_missing_keys():
    with pytest.raises(ValueError, match="eksik alan"):
        core.validate_state_schema({"history": []})


def test_validate_state_schema_rejects_non_list_history():
    data = core.default_state()
    data["history"] = "olmamali"
    with pytest.raises(ValueError):
        core.validate_state_schema(data)


def test_validate_state_schema_rejects_bad_set_weight_type():
    data = core.default_state()
    data["history"] = [make_history_session("Bench Press", [
        {"weight": "cok-agir", "reps": 5}
    ])]
    with pytest.raises(ValueError, match="sayısal"):
        core.validate_state_schema(data)


def test_validate_state_schema_accepts_valid_history():
    data = core.default_state()
    data["history"] = [make_history_session("Bench Press", [make_set(100, 5)])]
    core.validate_state_schema(data)  # patlamamali


# ---------------------------------------------------------------------------
# validate_state_schema - settings.fontScale (Task 21)
# ---------------------------------------------------------------------------
def test_validate_state_schema_rejects_non_numeric_font_scale():
    data = core.default_state()
    data["settings"]["fontScale"] = "buyuk"
    with pytest.raises(ValueError, match="fontScale"):
        core.validate_state_schema(data)


def test_validate_state_schema_rejects_bool_font_scale():
    # bool, Python'da int'in alt sinifi (isinstance(True, int) == True) -
    # yanlislikla kabul edilmesin diye ayri bir test.
    data = core.default_state()
    data["settings"]["fontScale"] = True
    with pytest.raises(ValueError, match="fontScale"):
        core.validate_state_schema(data)


def test_validate_state_schema_rejects_out_of_range_font_scale():
    data = core.default_state()
    data["settings"]["fontScale"] = 5.0
    with pytest.raises(ValueError, match="fontScale"):
        core.validate_state_schema(data)


def test_validate_state_schema_accepts_missing_settings():
    # Eski yedeklerde "settings" hic olmayabilir - zorunlu degil.
    data = core.default_state()
    del data["settings"]
    core.validate_state_schema(data)  # patlamamali


def test_validate_state_schema_accepts_valid_font_scale_choices():
    for _name, val in (("Küçük", 0.85), ("Normal", 1.0), ("Büyük", 1.2)):
        data = core.default_state()
        data["settings"]["fontScale"] = val
        core.validate_state_schema(data)  # patlamamali


# ---------------------------------------------------------------------------
# Antrenman oturumu: start/add_set/finish/discard + tonaj
# ---------------------------------------------------------------------------
def test_session_tonnage_ignores_warmup_sets():
    session = {"exercises": [{"name": "Squat", "sets": [
        make_set(60, 10, is_warmup=True),   # ısınma, sayılmamalı
        make_set(100, 5),
        make_set(100, 5),
    ]}]}
    assert core.session_tonnage(session) == 1000.0  # sadece 2x(100*5)


def test_add_set_detects_pr():
    state = core.default_state()
    state["history"] = [make_history_session("Deadlift", [make_set(140, 3)])]
    core.start_session(state)
    core.add_exercise_to_session(state, "Deadlift")
    is_pr = core.add_set(state, 0, weight=150, reps=3)
    assert is_pr is True


def test_add_set_below_previous_max_is_not_pr():
    state = core.default_state()
    state["history"] = [make_history_session("Deadlift", [make_set(140, 3)])]
    core.start_session(state)
    core.add_exercise_to_session(state, "Deadlift")
    is_pr = core.add_set(state, 0, weight=130, reps=3)
    assert is_pr is False


def test_add_set_pr_check_only_looks_at_history_not_current_session():
    # NOT (davranis notu, hata degil): max_weight_for() SADECE state["history"]
    # taramasi yapar - aktif seansta bu ANDA eklenmis setler prev_max'a dahil
    # DEGILDIR. Yani ayni agirlikla ust uste iki set girilirse HER IKISI de
    # (tarihsel rekore gore) PR sayilir - UI tarafinda bu bilincli bir
    # tasarim (her set kendi basina degerlendirilir).
    state = core.default_state()
    state["history"] = [make_history_session("Deadlift", [make_set(140, 3)])]
    core.start_session(state)
    core.add_exercise_to_session(state, "Deadlift")
    assert core.add_set(state, 0, weight=150, reps=3) is True
    assert core.add_set(state, 0, weight=150, reps=3) is True


def test_add_set_warmup_never_counts_as_pr():
    state = core.default_state()
    core.start_session(state)
    core.add_exercise_to_session(state, "Squat")
    is_pr = core.add_set(state, 0, weight=200, reps=1, is_warmup=True)
    assert is_pr is False


def test_remove_set():
    state = core.default_state()
    core.start_session(state)
    core.add_exercise_to_session(state, "Squat")
    core.add_set(state, 0, 100, 5)
    core.add_set(state, 0, 105, 5)
    core.remove_set(state, 0, 0)
    sets = state["activeSession"]["exercises"][0]["sets"]
    assert len(sets) == 1
    assert sets[0]["weight"] == 105


def test_finish_session_moves_to_history():
    state = core.default_state()
    core.start_session(state)
    core.add_exercise_to_session(state, "Squat")
    core.add_set(state, 0, 100, 5)
    core.finish_session(state)
    assert state["activeSession"] is None
    assert len(state["history"]) == 1
    assert state["history"][0]["exercises"][0]["name"] == "Squat"


def test_finish_session_with_no_exercises_is_discarded_not_saved():
    # KOK NEDEN: bos bir antrenmani (hic hareket eklenmeden "Bitir"e basilirsa)
    # gecmise kaydetmek anlamsiz gecmis kayitlari biriktirir.
    state = core.default_state()
    core.start_session(state)
    core.finish_session(state)
    assert state["activeSession"] is None
    assert state["history"] == []


def test_discard_session_does_not_touch_history():
    state = core.default_state()
    core.start_session(state)
    core.add_exercise_to_session(state, "Squat")
    core.add_set(state, 0, 100, 5)
    core.discard_session(state)
    assert state["activeSession"] is None
    assert state["history"] == []


def test_remove_history_session():
    state = core.default_state()
    state["history"] = [
        make_history_session("A", [make_set(10, 1)], session_id="keep"),
        make_history_session("B", [make_set(10, 1)], session_id="drop"),
    ]
    core.remove_history_session(state, "drop")
    assert [s["id"] for s in state["history"]] == ["keep"]


# ---------------------------------------------------------------------------
# suggested_weight_for (cift ilerleme mantigi)
# ---------------------------------------------------------------------------
def test_suggested_weight_below_floor_keeps_same_weight():
    state = core.default_state()
    state["history"] = [make_history_session("Bench Press", [make_set(80, 4)])]  # hedef min 6, 4 < 6
    result = core.suggested_weight_for(state, "Bench Press", target_min=6, target_max=8)
    assert result == {"weight": 80, "reason": "below"}


def test_suggested_weight_at_ceiling_increments():
    state = core.default_state()
    state["history"] = [make_history_session("Bench Press", [make_set(80, 8), make_set(80, 9)])]
    result = core.suggested_weight_for(state, "Bench Press", target_min=6, target_max=8)
    assert result["reason"] == "ceiling"
    assert result["weight"] == 82.5  # Bench Press EXERCISE_INCREMENT'te yoksa "compound" varsayilan -> +2.5


def test_suggested_weight_in_range_keeps_same_weight():
    state = core.default_state()
    state["history"] = [make_history_session("Bench Press", [make_set(80, 7)])]
    result = core.suggested_weight_for(state, "Bench Press", target_min=6, target_max=8)
    assert result == {"weight": 80, "reason": "inrange"}


def test_suggested_weight_ignores_deload_sessions():
    state = core.default_state()
    state["history"] = [
        make_history_session("Bench Press", [make_set(50, 8)], is_deload=True, session_id="d"),
        make_history_session("Bench Press", [make_set(80, 7)], session_id="normal"),
    ]
    result = core.suggested_weight_for(state, "Bench Press", target_min=6, target_max=8)
    assert result["weight"] == 80  # deload seansi atlanip normal seansa bakilmali


def test_suggested_weight_returns_none_with_no_history():
    state = core.default_state()
    assert core.suggested_weight_for(state, "Bench Press", 6, 8) is None


def test_suggested_weight_bodyweight_exercise_stays_same_at_ceiling():
    state = core.default_state()
    state["history"] = [make_history_session("Chin-up", [make_set(0, 10), make_set(0, 10)])]
    result = core.suggested_weight_for(state, "Chin-up", target_min=6, target_max=8)
    assert result["reason"] == "ceiling-bw"
    assert result["weight"] == 0  # bodyweight artis kategorisinde artis 0


# ---------------------------------------------------------------------------
# max_weight_for
# ---------------------------------------------------------------------------
def test_max_weight_for_ignores_warmup_and_other_exercises():
    state = core.default_state()
    state["history"] = [make_history_session("Squat", [
        make_set(200, 1, is_warmup=True),  # ısınma - sayılmamalı
        make_set(150, 5),
    ])]
    assert core.max_weight_for(state, "Squat") == 150
    assert core.max_weight_for(state, "Bilinmeyen Hareket") == 0


# ---------------------------------------------------------------------------
# Program gunu CRUD
# ---------------------------------------------------------------------------
def test_add_and_delete_program_day():
    state = core.default_state()
    day = core.add_program_day(state)
    assert len(state["program"]["days"]) == 1
    core.delete_program_day(state, day["id"])
    assert state["program"]["days"] == []


def test_move_program_day():
    state = core.default_state()
    d1 = core.add_program_day(state)
    d2 = core.add_program_day(state)
    core.move_program_day(state, d2["id"], -1)
    assert [d["id"] for d in state["program"]["days"]] == [d2["id"], d1["id"]]


def test_move_program_day_out_of_bounds_is_noop():
    state = core.default_state()
    d1 = core.add_program_day(state)
    core.move_program_day(state, d1["id"], -1)  # zaten en basta, disariya cikilamaz
    assert state["program"]["days"] == [d1]


def test_duplicate_program_day():
    state = core.default_state()
    d1 = core.add_program_day(state)
    core.set_day_exercise_target(state, d1["id"], "Squat", target_sets=3)
    copy_day = core.duplicate_program_day(state, d1["id"])
    assert copy_day["name"] == d1["name"] + " (Kopya)"
    assert len(state["program"]["days"]) == 2
    assert copy_day["exercises"][0]["name"] == "Squat"
    # kopya bagimsiz olmali (referans paylasilmamali)
    copy_day["exercises"][0]["targetSets"] = 99
    assert d1["exercises"][0]["targetSets"] == 3


def test_set_day_exercise_target_adds_then_updates():
    state = core.default_state()
    day = core.add_program_day(state)
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=3, target_reps_min=6)
    assert len(day["exercises"]) == 1
    assert day["exercises"][0]["targetSets"] == 3

    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=5)
    assert len(day["exercises"]) == 1  # ayni isim -> guncellenmeli, yeni satir eklenmemeli
    assert day["exercises"][0]["targetSets"] == 5
    assert day["exercises"][0]["targetRepsMin"] is None  # yeni cagri eski degeri TASIMAZ, tamamen yeniden yazar


def test_set_day_exercise_target_updates_active_session_live():
    # KOK NEDEN regresyon: aktif bir antrenmanda hedef degistirilince o anki
    # seansa da yansimali (bkz. set_day_exercise_target sonundaki not).
    state = core.default_state()
    day = core.add_program_day(state)
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=3)
    core.start_session(state, day_id=day["id"])
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=5)
    assert state["activeSession"]["exercises"][0]["targetSets"] == 5


def test_move_day_exercise():
    # UX (kullanicidan gelen istek - "eklediğim hareketlerin yerlerini
    # nasıl değiştirebilirim") - move_program_day ile AYNI desen, tek bir
    # gunun KENDI hareket listesi icinde.
    state = core.default_state()
    day = core.add_program_day(state)
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=3)
    core.set_day_exercise_target(state, day["id"], "Bench Press", target_sets=3)
    core.move_day_exercise(state, day["id"], 1, -1)
    assert [e["name"] for e in day["exercises"]] == ["Bench Press", "Squat"]


def test_move_day_exercise_out_of_bounds_is_noop():
    state = core.default_state()
    day = core.add_program_day(state)
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=3)
    core.move_day_exercise(state, day["id"], 0, -1)  # zaten en basta
    assert [e["name"] for e in day["exercises"]] == ["Squat"]
    core.move_day_exercise(state, day["id"], 0, 1)  # zaten TEK eleman, disariya cikamaz
    assert [e["name"] for e in day["exercises"]] == ["Squat"]


def test_move_day_exercise_unknown_day_is_noop():
    state = core.default_state()
    core.move_day_exercise(state, "olmayan-id", 0, 1)  # hata firlatmamali


def test_set_day_exercise_target_note_saved_and_updated():
    # UX (kullanicidan gelen istek - "bazı hareketlere not eklemek
    # istiyorum").
    state = core.default_state()
    day = core.add_program_day(state)
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=3,
                                  note="dizleri dışarı doğru it")
    assert day["exercises"][0]["note"] == "dizleri dışarı doğru it"

    # not GONDERILMEZSE (None) - obj yine SIFIRDAN kuruldugu icin eski not
    # KORUNMAZ, None olur. Bu, targetRepsMin gibi diger tum alanlarla AYNI
    # ("yeni cagri eski degeri tasimaz") davranis - UI (open_target_editor)
    # notu HER ZAMAN (degismemis olsa bile) geri gonderdigi icin gercek
    # kullanimda bu bir sorun yaratmaz.
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=5)
    assert day["exercises"][0]["note"] is None


def test_set_day_exercise_target_empty_note_stored_as_none():
    # UI, bos bir not kutusunu note="" olarak gonderir (strip() sonrasi) -
    # bunun disariya "" olarak degil None olarak sizmasi, "not var mi"
    # kontrollerini (ex.get("note")) sadece bos-string kontrolu YAPMADAN
    # dogru calistirir.
    state = core.default_state()
    day = core.add_program_day(state)
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=3, note="")
    assert day["exercises"][0]["note"] is None


def test_start_session_carries_exercise_note():
    # UX (kullanicidan gelen istek): not, antrenman SIRASINDA da
    # gorunebilsin diye aktif seansa da tasinmali.
    state = core.default_state()
    day = core.add_program_day(state)
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=3,
                                  note="dizleri dışarı doğru it")
    core.start_session(state, day_id=day["id"])
    assert state["activeSession"]["exercises"][0]["note"] == "dizleri dışarı doğru it"


def test_remove_exercise_from_day():
    state = core.default_state()
    day = core.add_program_day(state)
    core.set_day_exercise_target(state, day["id"], "Squat", target_sets=3)
    core.remove_exercise_from_day(state, day["id"], 0)
    assert day["exercises"] == []


def test_all_exercise_names_includes_library_and_history():
    state = core.default_state()
    state["library"] = ["Özel Egzersiz"]
    state["history"] = [make_history_session("Tarihi Hareket", [make_set(10, 1)])]
    names = core.all_exercise_names(state)
    assert "Özel Egzersiz" in names
    assert "Tarihi Hareket" in names
    assert "Bench Press" in names  # DEFAULT_EXERCISES'ten


# ---------------------------------------------------------------------------
# rir_badge_info
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rir,target_rir,expected_kind", [
    (4, 2, "easy"),      # cok kolay - hedeften 2+ fazla
    (0, 2, "hard"),      # cok zor - hedeften 2+ az
    (2, 2, "ontarget"),  # tam hedefte
])
def test_rir_badge_info_kinds(rir, target_rir, expected_kind):
    s = make_set(100, 5, rir=rir)
    ex = {"targetRIR": target_rir}
    badge = core.rir_badge_info(s, ex)
    assert badge["kind"] == expected_kind


def test_rir_badge_info_neutral_without_target():
    s = make_set(100, 5, rir=3)
    badge = core.rir_badge_info(s, {})
    assert badge["kind"] == "neutral"


def test_rir_badge_info_none_without_rir_logged():
    s = make_set(100, 5)  # rir hic girilmemis
    assert core.rir_badge_info(s, {"targetRIR": 2}) is None


# ---------------------------------------------------------------------------
# history_exercise_compare
# ---------------------------------------------------------------------------
def test_history_exercise_compare_no_sets_with_target():
    ex = {"name": "Squat", "sets": [], "targetSets": 3}
    result = core.history_exercise_compare(ex)
    assert result["delta"] == ("none", "SET GİRİLMEDİ")


def test_history_exercise_compare_weight_target_up():
    ex = {"name": "Squat", "sets": [make_set(105, 5)], "targetWeight": 100}
    result = core.history_exercise_compare(ex)
    assert result["delta"][0] == "up"
    assert result["weightDiffKg"] == 5


def test_history_exercise_compare_weight_target_eq():
    ex = {"name": "Squat", "sets": [make_set(100, 5)], "targetWeight": 100}
    result = core.history_exercise_compare(ex)
    assert result["delta"] == ("eq", "HEDEFTE")


def test_history_exercise_compare_reps_target_reached_ceiling():
    ex = {"name": "Squat", "sets": [make_set(100, 8), make_set(100, 9)],
          "targetRepsMin": 6, "targetRepsMax": 8}
    result = core.history_exercise_compare(ex)
    assert result["delta"][0] == "up"


def test_history_exercise_compare_reps_below_floor():
    ex = {"name": "Squat", "sets": [make_set(100, 4)], "targetRepsMin": 6, "targetRepsMax": 8}
    result = core.history_exercise_compare(ex)
    assert result["delta"][0] == "down"


def test_history_exercise_compare_sets_badge():
    ex = {"name": "Squat", "sets": [make_set(100, 5)], "targetSets": 3}
    result = core.history_exercise_compare(ex)
    assert result["setsBadge"] == (1, 3, "under")


# ---------------------------------------------------------------------------
# compute_all_prs / muscle_group_volume
# ---------------------------------------------------------------------------
def test_compute_all_prs_only_flags_new_maxima():
    state = core.default_state()
    state["history"] = [
        make_history_session("Squat", [make_set(100, 5)], started_at=1000, session_id="a"),
        make_history_session("Squat", [make_set(90, 5)], started_at=2000, session_id="b"),   # PR degil (dustu)
        make_history_session("Squat", [make_set(110, 5)], started_at=3000, session_id="c"),  # yeni PR
    ]
    prs = core.compute_all_prs(state)
    weights = [p["weight"] for p in prs if p["name"] == "Squat"]
    assert weights == [100, 110]


def test_muscle_group_volume_counts_working_sets_per_group():
    state = core.default_state()
    state["muscleGroups"] = {"Squat": ["Bacak"], "Bench Press": ["Göğüs"]}
    cur_key = core.period_key(1000, "week")
    state["history"] = [make_history_session("Squat", [make_set(100, 5), make_set(100, 5)],
                                              started_at=1000)]
    result = core.muscle_group_volume(state, "week", cur_key)
    assert result == [("Bacak", 2)]


# ---------------------------------------------------------------------------
# weekly_tonnage_trend (UX incelemesi - Rapor ekrani trend grafigi)
# ---------------------------------------------------------------------------
def test_weekly_tonnage_trend_returns_requested_number_of_weeks_oldest_first():
    state = core.default_state()
    now = core.now_ms()
    trend = core.weekly_tonnage_trend(state, weeks=8, now_ms_value=now)
    assert len(trend) == 8
    starts = [p["weekStart"] for p in trend]
    assert starts == sorted(starts)  # en eski -> en yeni
    assert starts[-1] == core.period_key(now, "week")


def test_weekly_tonnage_trend_empty_weeks_are_zero_not_missing():
    state = core.default_state()
    now = core.now_ms()
    trend = core.weekly_tonnage_trend(state, weeks=4, now_ms_value=now)
    assert all(p["tonnage"] == 0 for p in trend)


def test_weekly_tonnage_trend_sums_sessions_into_correct_week():
    state = core.default_state()
    now = core.now_ms()
    week_ms = 7 * 24 * 60 * 60 * 1000
    cur_week_start = core.period_key(now, "week")
    prev_week_ts = cur_week_start - week_ms + 1000  # bir onceki haftanin icinde bir an
    state["history"] = [
        make_history_session("Squat", [make_set(100, 5)], started_at=now),          # bu hafta: 500kg
        make_history_session("Bench Press", [make_set(50, 10)], started_at=prev_week_ts),  # onceki hafta: 500kg
    ]
    trend = core.weekly_tonnage_trend(state, weeks=8, now_ms_value=now)
    assert trend[-1]["tonnage"] == 500  # bu hafta
    assert trend[-2]["tonnage"] == 500  # bir onceki hafta
    assert all(p["tonnage"] == 0 for p in trend[:-2])


def test_weekly_tonnage_trend_ignores_sessions_older_than_window():
    state = core.default_state()
    now = core.now_ms()
    week_ms = 7 * 24 * 60 * 60 * 1000
    too_old_ts = now - 20 * week_ms  # istenen pencerenin (8 hafta) cok disinda
    state["history"] = [make_history_session("Squat", [make_set(100, 5)], started_at=too_old_ts)]
    trend = core.weekly_tonnage_trend(state, weeks=8, now_ms_value=now)
    assert sum(p["tonnage"] for p in trend) == 0


# ---------------------------------------------------------------------------
# increment_for
# ---------------------------------------------------------------------------
def test_increment_for_known_categories():
    assert core.increment_for("Barbell Curl") == 1.25       # isolation
    assert core.increment_for("Bench Press") == 2.5          # compound
    assert core.increment_for("Chin-up") == 0                # bodyweight


def test_increment_for_unknown_exercise_defaults_to_compound():
    assert core.increment_for("Hic Tanimli Olmayan Hareket XYZ") == 2.5


def _state_with_exercise(name):
    st = core.default_state()
    st["program"]["days"] = [{"id": "d1", "name": "G", "exercises": [{"name": name}]}]
    st["history"] = [
        {"id": "h1", "startedAt": 1, "exercises": [{"name": name, "sets": [{"weight": 50, "reps": 8}]}]},
        {"id": "h2", "startedAt": 2, "exercises": [{"name": name, "sets": [{"weight": 55, "reps": 8}]}]},
    ]
    st["library"] = [name]
    st["muscleGroups"] = {name: ["Sırt"]}
    return st


def test_rename_exercise_updates_everywhere_and_keeps_sets():
    st = _state_with_exercise("Yanlis Isim")
    ok, _ = core.rename_exercise(st, "Yanlis Isim", "  Dogru Isim ")
    assert ok
    assert st["program"]["days"][0]["exercises"][0]["name"] == "Dogru Isim"
    assert [s["exercises"][0]["name"] for s in st["history"]] == ["Dogru Isim"] * 2
    assert st["history"][1]["exercises"][0]["sets"][0]["weight"] == 55
    assert st["library"] == ["Dogru Isim"]
    assert st["muscleGroups"] == {"Dogru Isim": ["Sırt"]}
    assert len(core.history_for_exercise(st, "Dogru Isim")) == 2
    assert core.history_for_exercise(st, "Yanlis Isim") == []


def test_rename_exercise_rejects_empty_same_and_conflict():
    st = _state_with_exercise("A")
    st["history"][0]["exercises"].append({"name": "B", "sets": []})
    assert core.rename_exercise(st, "A", "  ")[0] is False
    assert core.rename_exercise(st, "A", "A")[0] is False
    assert core.rename_exercise(st, "A", "B")[0] is False
    assert st["history"][0]["exercises"][0]["name"] == "A"  # hicbir sey degismedi


def test_rename_exercise_updates_active_session():
    st = _state_with_exercise("A")
    st["activeSession"] = {"exercises": [{"name": "A", "sets": []}]}
    assert core.rename_exercise(st, "A", "C")[0]
    assert st["activeSession"]["exercises"][0]["name"] == "C"


# ---------------------------------------------------------------------------
# Detayli inceleme duzeltmeleri (veri guvenligi + cekirdek mantik)
# ---------------------------------------------------------------------------
import json as _json
import threading as _threading


def test_save_state_bare_filename_works(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    core.save_state("s.json", core.default_state())
    assert (tmp_path / "s.json").exists()


def test_save_state_keeps_bak_of_previous_good_file(tmp_path):
    path = str(tmp_path / "st.json")
    a = core.default_state(); a["library"] = ["ilk"]
    core.save_state(path, a)
    b = core.default_state(); b["library"] = ["ikinci"]
    core.save_state(path, b)
    with open(path + ".bak", encoding="utf-8") as f:
        assert _json.load(f)["library"] == ["ilk"]


def test_load_state_falls_back_to_bak_when_main_is_truncated(tmp_path):
    path = str(tmp_path / "st.json")
    a = core.default_state(); a["library"] = ["ilk"]
    core.save_state(path, a)
    b = core.default_state(); b["library"] = ["ikinci"]
    core.save_state(path, b)
    with open(path, "w", encoding="utf-8") as f:
        f.write("")  # yarim kalmis/bos dosya
    state, is_new, recovered = core.load_state(path)
    assert state["library"] == ["ilk"] and recovered is True and is_new is False


def test_stale_write_does_not_overwrite_newer(tmp_path):
    path = str(tmp_path / "st.json")
    old_seq = core.next_write_seq()
    new_seq = core.next_write_seq()
    assert core.write_json_atomic(path, '{"v": "yeni"}', new_seq) is True
    assert core.write_json_atomic(path, '{"v": "eski"}', old_seq) is False
    with open(path, encoding="utf-8") as f:
        assert _json.load(f) == {"v": "yeni"}


def test_concurrent_saves_always_leave_valid_json(tmp_path):
    path = str(tmp_path / "st.json")
    def work(n):
        for i in range(20):
            st = core.default_state(); st["library"] = [f"t{n}-{i}"]
            core.save_state(path, st)
    ts = [_threading.Thread(target=work, args=(n,)) for n in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    with open(path, encoding="utf-8") as f:
        assert isinstance(_json.load(f), dict)
    assert not [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]


def test_load_state_out_of_range_font_scale_is_repaired_not_wiped(tmp_path):
    path = str(tmp_path / "st.json")
    st = core.default_state()
    st["settings"]["fontScale"] = 3
    st["history"] = [{"id": "h", "startedAt": 5, "exercises": [{"name": "A", "sets": [{"weight": 5, "reps": 5}]}]}]
    with open(path, "w", encoding="utf-8") as f:
        _json.dump(st, f)
    loaded, _, recovered = core.load_state(path)
    assert recovered is False
    assert loaded["settings"]["fontScale"] == 1.0
    assert len(loaded["history"]) == 1


def test_load_state_never_overwrites_file_it_cannot_move(tmp_path, monkeypatch):
    path = str(tmp_path / "st.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{bozuk")
    monkeypatch.setattr(core.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    state, _, recovered = core.load_state(path)
    assert recovered is True
    with open(path, encoding="utf-8") as f:
        assert f.read() == "{bozuk"          # orijinale dokunulmadi
    monkeypatch.undo()
    core._SAVE_BLOCKED.discard(path)


def test_sanitize_state_fills_missing_keys_and_none_weights():
    raw = {"history": [{"exercises": [{"name": " Squat ", "sets": [
        {"weight": None, "reps": 5}, {"reps": 3}, {"weight": 50}, "x"]}]}],
        "program": {"days": []}, "library": [], "activeSession": None}
    st = core.sanitize_state(raw)
    sess = st["history"][0]
    assert sess["id"] and sess["startedAt"] == 0
    assert sess["exercises"][0]["name"] == "Squat"
    assert [s["weight"] for s in sess["exercises"][0]["sets"]] == [0.0, 0.0]  # tekrari olmayanlar atildi
    assert st["muscleGroups"] and st["bodyweightLog"] == [] and st["settings"]["weightUnit"] == "kg"
    assert core.session_tonnage(sess) == 0.0   # artik cokmuyor
    core.validate_state_schema(st)


def test_prepare_import_rejects_non_tonaj_json_and_repairs_old_backup():
    import pytest
    with pytest.raises(ValueError, match="eksik alan"):
        core.prepare_import({"foo": 1})
    old = {"history": [], "program": {"days": [{"id": "d", "name": "G", "exercises": [{"name": "A"}]}]},
           "library": [], "activeSession": None}      # muscleGroups/settings/bodyweightLog yok
    st = core.prepare_import(old)
    core.set_day_exercise_target(st, "d", "A", muscle_groups=["Sırt"])   # eskiden KeyError
    assert st["muscleGroups"]["A"] == ["Sırt"]


def test_make_safety_copy_keeps_only_last_three(tmp_path):
    path = str(tmp_path / "st.json")
    core.save_state(path, core.default_state())
    import time as _t
    for i in range(5):
        core.make_safety_copy(path, "pre-import")
        _t.sleep(1.01)
    copies = [f for f in os.listdir(tmp_path) if ".pre-import-" in f]
    assert len(copies) == 3


def test_start_session_does_not_discard_active_session():
    st = core.default_state()
    st["program"]["days"] = [{"id": "d", "name": "n", "exercises": [{"name": "Squat"}]}]
    core.start_session(st, "d")
    core.add_set(st, 0, 100, 5)
    again = core.start_session(st, "d")
    assert again is st["activeSession"]
    assert len(st["activeSession"]["exercises"][0]["sets"]) == 1


def test_add_set_zero_weight_ok_but_invalid_rejected():
    import pytest
    st = core.default_state()
    core.start_session(st); core.add_exercise_to_session(st, "Chin-up")
    core.add_set(st, 0, 0, 8)                       # vucut agirligi
    with pytest.raises(ValueError):
        core.add_set(st, 0, -5, 8)
    with pytest.raises(ValueError):
        core.add_set(st, 0, 20, 0)
    assert len(st["activeSession"]["exercises"][0]["sets"]) == 1


def test_exercise_names_are_normalized_and_case_resolved():
    st = core.default_state()
    core.start_session(st)
    assert core.add_exercise_to_session(st, "squat ") is True
    assert core.add_exercise_to_session(st, "  SQUAT") is False
    assert [e["name"] for e in st["activeSession"]["exercises"]] == ["Squat"]


def test_finish_session_without_working_sets_is_not_saved():
    st = core.default_state()
    st["program"]["days"] = [{"id": "d", "name": "n", "exercises": [{"name": "Squat"}]}]
    core.start_session(st, "d")
    assert core.finish_session(st) is False and st["history"] == [] and st["activeSession"] is None
    core.start_session(st, "d"); core.add_set(st, 0, 60, 5, is_warmup=True)
    assert core.finish_session(st) is False and st["history"] == []
    core.start_session(st, "d"); core.add_set(st, 0, 60, 5)
    assert core.finish_session(st) is True and len(st["history"]) == 1


def test_rename_keeps_increment_category_and_hides_renamed_default():
    st = _state_with_exercise("Barbell Curl")           # hazir, izolasyon (1.25)
    ok, _ = core.rename_exercise(st, "Barbell Curl", "Benim Curl")
    assert ok
    assert core.increment_for("Benim Curl", st) == 1.25
    assert "Barbell Curl" not in core.all_exercise_names(st)
    assert core.rename_exercise(st, "Benim Curl", "Barbell Curl")[0]   # geri donunce tekrar gorunur
    assert "Barbell Curl" in core.all_exercise_names(st)


def test_rename_to_case_variant_merges_into_existing_name():
    st = _state_with_exercise("squat")
    ok, _ = core.rename_exercise(st, "squat", "SQUAT ")
    assert ok and st["history"][0]["exercises"][0]["name"] == "Squat"


def test_weekly_trend_survives_dst_timezone(monkeypatch):
    import time as _t
    monkeypatch.setenv("TZ", "Europe/Berlin"); _t.tzset()
    try:
        st = core.default_state()
        sess_ts = int(datetime_ts(2026, 10, 20, 12))
        st["history"] = [{"id": "a", "startedAt": sess_ts, "exercises": [
            {"name": "A", "sets": [{"weight": 100, "reps": 10}]}]}]
        trend = core.weekly_tonnage_trend(st, weeks=3, now_ms_value=sess_ts + 3 * 86400 * 1000)
        assert sum(p["tonnage"] for p in trend) == 1000.0
    finally:
        monkeypatch.delenv("TZ"); _t.tzset()


def datetime_ts(y, m, d, h):
    from datetime import datetime as _dt
    return _dt(y, m, d, h).timestamp() * 1000


def test_suggested_weight_ignores_light_backoff_sets():
    st = core.default_state()
    st["history"] = [{"id": "a", "startedAt": 2, "exercises": [{"name": "Bench Press", "sets": [
        {"weight": 100, "reps": 6}, {"weight": 60, "reps": 12}]}]}]
    r = core.suggested_weight_for(st, "Bench Press", 6, 8)
    assert r["weight"] == 100 and r["reason"] == "inrange"


def test_history_order_does_not_depend_on_list_order():
    st = core.default_state()
    new = {"id": "n", "startedAt": 200, "exercises": [{"name": "A", "sets": [{"weight": 60, "reps": 8}]}]}
    old = {"id": "o", "startedAt": 100, "exercises": [{"name": "A", "sets": [{"weight": 50, "reps": 8}]}]}
    st["history"] = [old, new]        # bozuk sira
    assert [p["max"] for p in core.history_for_exercise(st, "A")] == [50, 60]
    assert core.suggested_weight_for(st, "A", 8, 8)["weight"] == 62.5


def test_set_day_exercise_target_copies_muscle_group_list():
    st = core.default_state()
    st["program"]["days"] = [{"id": "d", "name": "n", "exercises": []}]
    groups = ["Sırt"]
    core.set_day_exercise_target(st, "d", "A", muscle_groups=groups)
    groups.append("Biceps")
    assert st["muscleGroups"]["A"] == ["Sırt"]
