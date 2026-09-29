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


def test_load_state_recovers_when_schema_is_invalid(tmp_path):
    # gecerli JSON + dict, ama ic yapi bozuk (sets bir liste degil)
    path = str(tmp_path / "tonaj_state.json")
    import json
    bad = core.default_state()
    bad["history"] = [{"id": "x", "startedAt": 1, "exercises": [
        {"name": "Bench Press", "sets": "bu bir liste olmali ama string"}
    ]}]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bad, f)

    state, is_new, recovered = core.load_state(path)
    assert recovered is True


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
# increment_for
# ---------------------------------------------------------------------------
def test_increment_for_known_categories():
    assert core.increment_for("Barbell Curl") == 1.25       # isolation
    assert core.increment_for("Bench Press") == 2.5          # compound
    assert core.increment_for("Chin-up") == 0                # bodyweight


def test_increment_for_unknown_exercise_defaults_to_compound():
    assert core.increment_for("Hic Tanimli Olmayan Hareket XYZ") == 2.5
