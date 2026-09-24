"""
Tonaj - cekirdek veri modeli ve is mantigi.

Bu modul Kivy'ye BAGIMLI DEGIL - amac, arayuzden bagimsiz olarak duz Python ile
test edilebilmesi. main.py (Kivy arayuzu) bu modulu kullanir.
"""
import json
import os
import uuid
import time
from datetime import datetime, timedelta

DAY_SECONDS = 24 * 3600

# ---------------------------------------------------------------------------
# Varsayilan hareket kutuphanesi + artis kategorisi + kas grubu
# ---------------------------------------------------------------------------
INCREMENT_CATEGORIES = {"compound": 2.5, "isolation": 1.25, "bodyweight": 0}

EXERCISE_INCREMENT = {
    "Bench Press": "compound", "Incline Bench Press": "compound", "Decline Bench Press": "compound",
    "Incline Dumbbell Press": "compound", "Flat Dumbbell Press": "compound", "Decline Dumbbell Press": "compound",
    "Dumbbell Fly": "isolation", "Cable Fly": "isolation", "Pec Deck (Chest Fly Machine)": "isolation",
    "Chest Press Machine": "compound", "Push-up": "bodyweight",
    "Deadlift": "compound", "Romanian Deadlift (RDL)": "compound", "Sumo Deadlift": "compound", "Rack Pull": "compound",
    "Barbell Row": "compound", "Pendlay Row": "compound", "T-Bar Row": "compound", "Cable Row": "compound",
    "Lat Pulldown": "compound", "Pull-up": "bodyweight", "Chin-up": "bodyweight",
    "Single-Arm Dumbbell Row": "compound", "Seated Cable Row": "compound", "Straight Arm Pulldown": "isolation",
    "Hyperextension": "bodyweight", "Good Morning": "compound",
    "Overhead Press": "compound", "Dumbbell Shoulder Press": "compound", "Shoulder Press (Dumbbell)": "compound",
    "Arnold Press": "compound", "Lateral Raise (Dumbbell/Cable)": "isolation", "Front Raise": "isolation",
    "Reverse Pec Deck": "isolation", "Face Pull": "isolation", "Upright Row": "isolation",
    "Cable Lateral Raise": "isolation", "Machine Shoulder Press": "compound",
    "Barbell Curl": "isolation", "EZ Barbell Curl": "isolation", "Bicep Curl": "isolation", "Dumbbell Curl": "isolation",
    "Incline Dumbbell Curl": "isolation", "Dumbbell Hammer Curl": "isolation", "Preacher Curl": "isolation",
    "Cable Curl": "isolation", "Concentration Curl": "isolation", "Spider Curl": "isolation", "Incline Curl": "isolation",
    "Triceps Pushdown": "isolation", "Ez Bar Skull Crusher": "isolation", "Overhead Triceps Extension": "isolation",
    "Dumbbell Triceps Extension": "isolation", "Close-Grip Bench Press": "compound", "Dip": "bodyweight",
    "Cable Overhead Extension": "isolation", "Triceps Kickback": "isolation",
    "Squat": "compound", "Front Squat": "compound", "Leg Press": "compound", "Hack Squat Machine": "compound",
    "Leg Extension": "isolation", "Bulgarian Split Squat": "compound", "Walking Lunge": "compound",
    "Goblet Squat": "compound", "Sissy Squat": "bodyweight",
    "Leg Curl": "isolation", "Stiff-Leg Deadlift": "compound", "Nordic Curl": "bodyweight", "Glute Ham Raise": "bodyweight",
    "Hip Thrust": "compound", "Glute Bridge": "compound", "Cable Kickback": "isolation", "Glute Machine": "isolation",
    "Calf Raise": "isolation", "Seated Calf Raise": "isolation", "Leg Press Calf Raise": "isolation", "Donkey Calf Raise": "isolation",
    "Hanging Leg Raise": "bodyweight", "Plank": "bodyweight", "Cable Pallof Press": "isolation",
    "Crunch Machine": "isolation", "Cable Crunch": "isolation", "Russian Twist": "bodyweight",
    "Ab Wheel Rollout": "bodyweight", "Sit-up": "bodyweight", "Leg Raise": "bodyweight", "Side Plank": "bodyweight",
    "Wrist Curl": "isolation", "Reverse Wrist Curl": "isolation", "Farmer's Walk": "compound",
}
DEFAULT_EXERCISES = sorted(EXERCISE_INCREMENT.keys())

MUSCLE_GROUPS = ["Göğüs", "Sırt", "Omuz", "Biceps", "Triceps", "Quadriceps", "Hamstring", "Glute", "Baldır", "Core", "Ön Kol"]
MUSCLE_GROUP_DEFAULTS = {
    "Bench Press": ["Göğüs", "Triceps"], "Incline Dumbbell Press": ["Göğüs", "Omuz"],
    "Lateral Raise (Dumbbell/Cable)": ["Omuz"], "Face Pull": ["Omuz", "Sırt"],
    "Ez Bar Skull Crusher": ["Triceps"], "Triceps Pushdown": ["Triceps"],
    "Lat Pulldown": ["Sırt"], "Cable Row": ["Sırt"], "Reverse Pec Deck": ["Omuz", "Sırt"],
    "Bulgarian Split Squat": ["Quadriceps", "Glute"], "Preacher Curl": ["Biceps"], "Dumbbell Hammer Curl": ["Biceps", "Ön Kol"],
    "Hack Squat Machine": ["Quadriceps"], "Romanian Deadlift (RDL)": ["Hamstring", "Glute"], "Hip Thrust": ["Glute", "Hamstring"],
    "Leg Extension": ["Quadriceps"], "Leg Curl": ["Hamstring"], "Calf Raise": ["Baldır"], "Seated Calf Raise": ["Baldır"],
    "Hanging Leg Raise": ["Core"], "Cable Pallof Press": ["Core"], "Squat": ["Quadriceps", "Glute"],
    "Deadlift": ["Sırt", "Hamstring", "Glute"], "Overhead Press": ["Omuz", "Triceps"], "Pull-up": ["Sırt", "Biceps"],
}


def increment_for(name):
    cat = EXERCISE_INCREMENT.get(name, "compound")
    return INCREMENT_CATEGORIES[cat]


def uid():
    return uuid.uuid4().hex[:10]


def now_ms():
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Baslangic (seed) programi
# ---------------------------------------------------------------------------
def build_seed_program():
    def ex(name, sets, rmin, rmax, weight, rir, rest):
        return {"name": name, "targetSets": sets, "targetRepsMin": rmin, "targetRepsMax": rmax,
                "targetWeight": weight, "targetRIR": rir, "restSeconds": rest}

    return {"days": [
        {"id": uid(), "name": "1. Gün: İtiş (Göğüs-Omuz-Triceps)", "exercises": [
            ex("Bench Press", 3, 6, 8, None, 2, 150),
            ex("Incline Dumbbell Press", 3, 8, 10, None, 2, 120),
            ex("Lateral Raise (Dumbbell/Cable)", 4, 12, 15, None, 1, 60),
            ex("Face Pull", 3, 12, 15, None, 1, 60),
            ex("Ez Bar Skull Crusher", 3, 10, 12, None, 1, 90),
            ex("Triceps Pushdown", 3, 10, 12, None, 1, 90),
        ]},
        {"id": uid(), "name": "2. Gün: Çekiş (Sırt-Omuz-Biceps-Ön Kol)", "exercises": [
            ex("Lat Pulldown", 3, 8, 10, None, 2, 120),
            ex("Cable Row", 3, 8, 10, None, 2, 120),
            ex("Reverse Pec Deck", 3, 12, 15, None, 1, 60),
            ex("Bulgarian Split Squat", 3, 8, 10, None, 2, 90),
            ex("Preacher Curl", 3, 10, 12, None, 1, 75),
            ex("Dumbbell Hammer Curl", 3, 10, 12, None, 1, 75),
        ]},
        {"id": uid(), "name": "3. Gün: Bacak & Karın", "exercises": [
            ex("Hack Squat Machine", 3, 8, 10, None, 2, 150),
            ex("Romanian Deadlift (RDL)", 3, 8, 10, None, 2, 150),
            ex("Hip Thrust", 3, 8, 10, None, 2, 120),
            ex("Leg Extension", 3, 12, 15, None, 1, 75),
            ex("Leg Curl", 3, 10, 12, None, 1, 75),
            ex("Calf Raise", 3, 12, 15, None, 1, 60),
            ex("Hanging Leg Raise", 3, 12, 15, None, 1, 60),
            ex("Cable Pallof Press", 2, 10, 12, None, 1, 60),
        ]},
    ]}


def default_state():
    return {
        "activeSession": None,
        "history": [],
        "library": [],
        "program": {"days": []},
        "muscleGroups": {},
        "bodyweightLog": [],
        "settings": {"lastBackupAt": None},
    }


# ---------------------------------------------------------------------------
# Kalici depolama (JSON dosyasi)
# ---------------------------------------------------------------------------
def load_state(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = default_state()
        state.update(data)
        if "muscleGroups" not in state or not state["muscleGroups"]:
            state["muscleGroups"] = data.get("muscleGroups", {})
        return state, False
    state = default_state()
    state["program"] = build_seed_program()
    state["muscleGroups"] = dict(MUSCLE_GROUP_DEFAULTS)
    save_state(path, state)
    return state, True


def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Antrenman oturumu
# ---------------------------------------------------------------------------
def session_tonnage(session):
    total = 0.0
    for ex in session.get("exercises", []):
        for s in ex.get("sets", []):
            if not s.get("isWarmup"):
                total += s["weight"] * s["reps"]
    return total


def max_weight_for(state, name):
    best = 0.0
    for s in state["history"]:
        for ex in s["exercises"]:
            if ex["name"] == name:
                for st in ex["sets"]:
                    if not st.get("isWarmup"):
                        best = max(best, st["weight"])
    return best


def history_for_exercise(state, name):
    pts = []
    for s in reversed(state["history"]):  # oldest -> newest for the raw scan
        for ex in s["exercises"]:
            if ex["name"] == name:
                working = [st for st in ex["sets"] if not st.get("isWarmup")]
                if not working:
                    continue
                pts.append({"date": s["startedAt"], "max": max(st["weight"] for st in working)})
    return pts


def suggested_weight_for(state, name, target_min, target_max):
    """Cift ilerleme: tavana ulastiysa agirlik artir, tabanin altinda kaldiysa
    ayni agirlik, aradaysa ayni agirlik (bu sefer tavana ulasmaya calis)."""
    for s in state["history"]:  # newest first
        if s.get("isDeload"):
            continue
        ex = next((e for e in s["exercises"] if e["name"] == name), None)
        if not ex:
            continue
        working = [st for st in ex["sets"] if not st.get("isWarmup")]
        if not working:
            continue
        last_weight = max(st["weight"] for st in working)
        below_floor = target_min is not None and any(st["reps"] < target_min for st in working)
        at_ceiling = target_max is not None and all(st["reps"] >= target_max for st in working)
        if below_floor:
            return {"weight": last_weight, "reason": "below"}
        if at_ceiling:
            inc = increment_for(name)
            if inc > 0:
                return {"weight": round(last_weight + inc, 2), "reason": "ceiling"}
            return {"weight": last_weight, "reason": "ceiling-bw"}
        return {"weight": last_weight, "reason": "inrange"}
    return None


def start_session(state, day_id=None, is_deload=False):
    exercises = []
    day_name = None
    if day_id:
        day = next((d for d in state["program"]["days"] if d["id"] == day_id), None)
        if day:
            for item in day["exercises"]:
                target_sets = item.get("targetSets")
                if is_deload and target_sets:
                    target_sets = max(1, round(target_sets * 0.6))
                suggestion = None if is_deload else suggested_weight_for(
                    state, item["name"], item.get("targetRepsMin"), item.get("targetRepsMax"))
                exercises.append({
                    "name": item["name"], "sets": [],
                    "targetSets": target_sets,
                    "targetRepsMin": item.get("targetRepsMin"), "targetRepsMax": item.get("targetRepsMax"),
                    "targetWeight": item.get("targetWeight"), "targetRIR": item.get("targetRIR"),
                    "restSeconds": item.get("restSeconds"),
                    "suggestedWeight": suggestion["weight"] if suggestion else None,
                    "suggestReason": suggestion["reason"] if suggestion else None,
                })
            day_name = day["name"]
    state["activeSession"] = {
        "id": uid(), "startedAt": now_ms(), "exercises": exercises,
        "dayName": day_name, "dayId": day_id, "isDeload": bool(is_deload), "note": "",
    }
    return state["activeSession"]


def add_exercise_to_session(state, name):
    sess = state["activeSession"]
    if not sess or any(e["name"] == name for e in sess["exercises"]):
        return
    sess["exercises"].append({"name": name, "sets": []})


def add_set(state, ex_index, weight, reps, is_warmup=False, rir=None):
    sess = state["activeSession"]
    ex = sess["exercises"][ex_index]
    prev_max = max_weight_for(state, ex["name"])
    s = {"weight": float(weight), "reps": int(reps)}
    if is_warmup:
        s["isWarmup"] = True
    if rir is not None:
        s["rir"] = int(rir)
    ex["sets"].append(s)
    is_pr = (not is_warmup) and s["weight"] > prev_max > 0
    return is_pr


def remove_set(state, ex_index, set_index):
    state["activeSession"]["exercises"][ex_index]["sets"].pop(set_index)


def finish_session(state):
    sess = state["activeSession"]
    if not sess:
        return
    if len(sess["exercises"]) == 0:
        state["activeSession"] = None
        return
    state["history"].insert(0, sess)
    state["activeSession"] = None


def discard_session(state):
    state["activeSession"] = None


# ---------------------------------------------------------------------------
# Program (gun) yonetimi
# ---------------------------------------------------------------------------
def add_program_day(state):
    n = len(state["program"]["days"]) + 1
    day = {"id": uid(), "name": f"Gün {n}", "exercises": []}
    state["program"]["days"].append(day)
    return day


def delete_program_day(state, day_id):
    state["program"]["days"] = [d for d in state["program"]["days"] if d["id"] != day_id]


def move_program_day(state, day_id, direction):
    days = state["program"]["days"]
    idx = next((i for i, d in enumerate(days) if d["id"] == day_id), -1)
    target = idx + direction
    if idx < 0 or target < 0 or target >= len(days):
        return
    days[idx], days[target] = days[target], days[idx]


def duplicate_program_day(state, day_id):
    days = state["program"]["days"]
    day = next((d for d in days if d["id"] == day_id), None)
    if not day:
        return None
    copy = {"id": uid(), "name": day["name"] + " (Kopya)",
            "exercises": [dict(e) for e in day["exercises"]]}
    idx = next(i for i, d in enumerate(days) if d["id"] == day_id)
    days.insert(idx + 1, copy)
    return copy


def set_day_exercise_target(state, day_id, name, target_sets=None, target_reps_min=None,
                             target_reps_max=None, target_weight=None, target_rir=None,
                             rest_seconds=None, muscle_groups=None):
    day = next(d for d in state["program"]["days"] if d["id"] == day_id)
    idx = next((i for i, e in enumerate(day["exercises"]) if e["name"] == name), -1)
    obj = {"name": name, "targetSets": target_sets, "targetRepsMin": target_reps_min,
           "targetRepsMax": target_reps_max, "targetWeight": target_weight,
           "targetRIR": target_rir, "restSeconds": rest_seconds}
    if idx >= 0:
        day["exercises"][idx] = obj
    else:
        day["exercises"].append(obj)
    if muscle_groups is not None:
        state["muscleGroups"][name] = muscle_groups
    # Aktif bir seansta ayni gunden ayni hareket varsa canli guncelle
    sess = state["activeSession"]
    if sess and sess.get("dayId") == day_id:
        active_ex = next((e for e in sess["exercises"] if e["name"] == name), None)
        if active_ex:
            active_ex.update({k: v for k, v in obj.items() if k != "name"})


def remove_exercise_from_day(state, day_id, idx):
    day = next(d for d in state["program"]["days"] if d["id"] == day_id)
    day["exercises"].pop(idx)


def next_suggested_day_id(state):
    days = state["program"]["days"]
    if not days:
        return None
    for s in state["history"]:
        if s.get("dayId"):
            idx = next((i for i, d in enumerate(days) if d["id"] == s["dayId"]), -1)
            if idx >= 0:
                return days[(idx + 1) % len(days)]["id"]
    return days[0]["id"]


def all_exercise_names(state):
    names = set(DEFAULT_EXERCISES) | set(state["library"])
    for s in state["history"]:
        for e in s["exercises"]:
            names.add(e["name"])
    if state["activeSession"]:
        for e in state["activeSession"]["exercises"]:
            names.add(e["name"])
    return sorted(names)


# ---------------------------------------------------------------------------
# Gecmis karsilastirmasi
# ---------------------------------------------------------------------------
def history_exercise_compare(ex):
    has_target = bool(ex.get("targetSets") or ex.get("targetRepsMin") or ex.get("targetRepsMax") or ex.get("targetWeight"))
    working = [s for s in ex["sets"] if not s.get("isWarmup")]
    best_weight = max((s["weight"] for s in working), default=0)

    if not working and has_target:
        delta = ("none", "SET GİRİLMEDİ")
    elif ex.get("targetWeight"):
        diff = round(best_weight - ex["targetWeight"], 2)
        if diff > 0:
            delta = ("up", f"▲ +{diff} KG")
        elif diff < 0:
            delta = ("down", f"▼ {diff} KG")
        else:
            delta = ("eq", "HEDEFTE")
    else:
        delta = (None, None)

    sets_badge = None
    if ex.get("targetSets"):
        done = len(working)
        sets_badge = (done, ex["targetSets"], "ok" if done >= ex["targetSets"] else "under")

    return {"hasTarget": has_target, "delta": delta, "setsBadge": sets_badge, "bestWeight": best_weight}


# ---------------------------------------------------------------------------
# Rapor: haftalik/aylik ozet + kas grubu hacmi
# ---------------------------------------------------------------------------
def period_key(ts_ms, period):
    dt = datetime.fromtimestamp(ts_ms / 1000)
    if period == "week":
        start = dt - timedelta(days=dt.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start.timestamp() * 1000)
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000)


def compute_all_prs(state):
    running_max = {}
    prs = []
    for s in sorted(state["history"], key=lambda x: x["startedAt"]):
        for ex in s["exercises"]:
            working = [st for st in ex["sets"] if not st.get("isWarmup")]
            if not working:
                continue
            best = max(st["weight"] for st in working)
            if best > running_max.get(ex["name"], 0):
                prs.append({"name": ex["name"], "date": s["startedAt"], "weight": best})
                running_max[ex["name"]] = best
    return prs


def muscle_group_volume(state, period, cur_key):
    counts = {}
    for s in state["history"]:
        if period_key(s["startedAt"], period) != cur_key:
            continue
        for ex in s["exercises"]:
            working = len([st for st in ex["sets"] if not st.get("isWarmup")])
            if not working:
                continue
            for g in state["muscleGroups"].get(ex["name"], []):
                counts[g] = counts.get(g, 0) + working
    return sorted(counts.items(), key=lambda x: -x[1])
