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
    "Ab Wheel Rollout": "bodyweight",
    "Arnold Press": "compound",
    "Assisted Dip Machine": "bodyweight",
    "Assisted Pull-up Machine": "bodyweight",
    "Barbell Calf Raise": "isolation",
    "Barbell Curl": "isolation",
    "Barbell Hip Thrust": "compound",
    "Barbell Lunge": "compound",
    "Barbell Overhead Press": "compound",
    "Barbell Pullover": "isolation",
    "Barbell Reverse Wrist Curl": "isolation",
    "Barbell Row": "compound",
    "Barbell Shrug": "isolation",
    "Barbell Skull Crusher": "isolation",
    "Barbell Step-Up": "compound",
    "Behind-the-Back Barbell Wrist Curl": "isolation",
    "Behind-the-Neck Press": "compound",
    "Belt Squat Machine": "compound",
    "Bench Dip": "bodyweight",
    "Bench Press": "compound",
    "Bicep Curl": "isolation",
    "Bird Dog": "bodyweight",
    "Bodyweight Step-Up": "bodyweight",
    "Bulgarian Split Squat": "compound",
    "Cable Bayesian Curl": "isolation",
    "Cable Crossover": "isolation",
    "Cable Crunch": "isolation",
    "Cable Curl": "isolation",
    "Cable Fly": "isolation",
    "Cable Front Raise": "isolation",
    "Cable Hip Abduction": "isolation",
    "Cable Kickback": "isolation",
    "Cable Lateral Raise": "isolation",
    "Cable Leg Curl": "isolation",
    "Cable Overhead Extension": "isolation",
    "Cable Overhead Rope Extension": "isolation",
    "Cable Pallof Press": "isolation",
    "Cable Pull-Through": "compound",
    "Cable Pullover": "isolation",
    "Cable Rear Delt Fly": "isolation",
    "Cable Rope Hammer Curl": "isolation",
    "Cable Row": "compound",
    "Cable Shrug": "isolation",
    "Cable Upright Row": "isolation",
    "Cable Woodchopper": "isolation",
    "Cable Wrist Curl": "isolation",
    "Calf Raise": "isolation",
    "Captain's Chair Leg Raise": "bodyweight",
    "Chest Dip": "bodyweight",
    "Chest Press Machine": "compound",
    "Chest-Supported Dumbbell Row": "compound",
    "Chin-up": "bodyweight",
    "Close-Grip Bench Press": "compound",
    "Close-Grip Lat Pulldown": "compound",
    "Concentration Curl": "isolation",
    "Cross-Body Hammer Curl": "isolation",
    "Crunch Machine": "isolation",
    "Dead Bug": "bodyweight",
    "Dead Hang": "bodyweight",
    "Deadlift": "compound",
    "Decline Bench Press": "compound",
    "Decline Cable Fly": "isolation",
    "Decline Dumbbell Fly": "isolation",
    "Decline Dumbbell Press": "compound",
    "Decline Push-up": "bodyweight",
    "Decline Sit-up": "bodyweight",
    "Decline Smith Machine Press": "compound",
    "Diamond Push-up": "bodyweight",
    "Dip": "bodyweight",
    "Donkey Calf Raise": "isolation",
    "Drag Curl": "isolation",
    "Dumbbell Calf Raise": "isolation",
    "Dumbbell Curl": "isolation",
    "Dumbbell Fly": "isolation",
    "Dumbbell Glute Bridge": "compound",
    "Dumbbell Hammer Curl": "isolation",
    "Dumbbell Lunge": "compound",
    "Dumbbell Preacher Curl": "isolation",
    "Dumbbell Pullover": "isolation",
    "Dumbbell Rear Delt Fly": "isolation",
    "Dumbbell Romanian Deadlift": "compound",
    "Dumbbell Shoulder Press": "compound",
    "Dumbbell Shrug": "isolation",
    "Dumbbell Side Bend": "isolation",
    "Dumbbell Skull Crusher": "isolation",
    "Dumbbell Step-Up": "compound",
    "Dumbbell Triceps Extension": "isolation",
    "Dumbbell Upright Row": "isolation",
    "Dumbbell Wrist Curl": "isolation",
    "EZ Barbell Curl": "isolation",
    "EZ-Bar Preacher Curl": "isolation",
    "Ez Bar Skull Crusher": "isolation",
    "Face Pull": "isolation",
    "Farmer's Walk": "compound",
    "Flat Dumbbell Press": "compound",
    "Floor Press (Barbell)": "compound",
    "Floor Press (Dumbbell)": "compound",
    "Front Raise": "isolation",
    "Front Squat": "compound",
    "Glute Bridge": "compound",
    "Glute Ham Raise": "bodyweight",
    "Glute Machine": "isolation",
    "Goblet Squat": "compound",
    "Good Morning": "compound",
    "Hack Squat Machine": "compound",
    "Hanging Knee Raise": "bodyweight",
    "Hanging Leg Raise": "bodyweight",
    "Hip Abduction Machine": "isolation",
    "Hip Adduction Machine": "isolation",
    "Hip Thrust": "compound",
    "Hyperextension": "bodyweight",
    "Incline Bench Press": "compound",
    "Incline Cable Fly": "isolation",
    "Incline Curl": "isolation",
    "Incline Dumbbell Curl": "isolation",
    "Incline Dumbbell Fly": "isolation",
    "Incline Dumbbell Press": "compound",
    "Incline Push-up": "bodyweight",
    "Incline Smith Machine Press": "compound",
    "Inverted Row": "bodyweight",
    "JM Press": "compound",
    "Kettlebell Farmer's Walk": "compound",
    "Landmine Press": "compound",
    "Lat Pulldown": "compound",
    "Lateral Raise (Dumbbell/Cable)": "isolation",
    "Leg Curl": "isolation",
    "Leg Extension": "isolation",
    "Leg Press": "compound",
    "Leg Press Calf Raise": "isolation",
    "Leg Raise": "bodyweight",
    "Lying Leg Curl Machine": "isolation",
    "Machine Ab Coaster": "isolation",
    "Machine Bicep Curl": "isolation",
    "Machine Crunch": "isolation",
    "Machine Decline Chest Press": "compound",
    "Machine Glute Kickback": "isolation",
    "Machine High Row": "compound",
    "Machine Hip Thrust": "compound",
    "Machine Incline Chest Press": "compound",
    "Machine Lateral Raise": "isolation",
    "Machine Leg Extension": "isolation",
    "Machine Low Row": "compound",
    "Machine Preacher Curl": "isolation",
    "Machine Rear Delt Fly": "isolation",
    "Machine Row (Chest-Supported)": "compound",
    "Machine Shoulder Press": "compound",
    "Machine Shrug": "isolation",
    "Machine Triceps Extension": "isolation",
    "Meadows Row": "compound",
    "Nordic Curl": "bodyweight",
    "Overhead Press": "compound",
    "Overhead Triceps Extension": "isolation",
    "Pec Deck (Chest Fly Machine)": "isolation",
    "Pendlay Row": "compound",
    "Pendulum Squat Machine": "compound",
    "Plank": "bodyweight",
    "Plate Front Raise": "isolation",
    "Plate Pinch Hold": "isolation",
    "Preacher Curl": "isolation",
    "Pull-up": "bodyweight",
    "Push Press": "compound",
    "Push-up": "bodyweight",
    "Rack Pull": "compound",
    "Reverse Barbell Curl": "isolation",
    "Reverse Pec Deck": "isolation",
    "Reverse Wrist Curl": "isolation",
    "Reverse-Grip Lat Pulldown": "compound",
    "Romanian Deadlift (RDL)": "compound",
    "Rope Pushdown": "isolation",
    "Russian Twist": "bodyweight",
    "Seated Barbell Shoulder Press": "compound",
    "Seated Cable Row": "compound",
    "Seated Calf Raise": "isolation",
    "Seated Dumbbell Shoulder Press": "compound",
    "Seated Leg Curl Machine": "isolation",
    "Shoulder Press (Dumbbell)": "compound",
    "Side Plank": "bodyweight",
    "Single-Arm Cable Chest Press": "isolation",
    "Single-Arm Cable Pushdown": "isolation",
    "Single-Arm Dumbbell Row": "compound",
    "Single-Arm Lat Pulldown": "compound",
    "Single-Leg Calf Raise": "bodyweight",
    "Single-Leg Leg Press": "compound",
    "Single-Leg Romanian Deadlift": "compound",
    "Sissy Squat": "bodyweight",
    "Sissy Squat Machine": "isolation",
    "Sit-up": "bodyweight",
    "Smith Machine Bench Press": "compound",
    "Smith Machine Calf Raise": "isolation",
    "Smith Machine Hip Thrust": "compound",
    "Smith Machine Romanian Deadlift": "compound",
    "Smith Machine Row": "compound",
    "Smith Machine Shoulder Press": "compound",
    "Smith Machine Shrug": "isolation",
    "Smith Machine Squat": "compound",
    "Spider Curl": "isolation",
    "Squat": "compound",
    "Standing Calf Raise Machine": "isolation",
    "Standing Leg Curl Machine": "isolation",
    "Stiff-Leg Deadlift": "compound",
    "Straight Arm Pulldown": "isolation",
    "Sumo Deadlift": "compound",
    "Svend Press": "isolation",
    "T-Bar Row": "compound",
    "Triceps Dip Machine": "compound",
    "Triceps Kickback": "isolation",
    "Triceps Pushdown": "isolation",
    "Upright Row": "isolation",
    "V-Bar Pushdown": "isolation",
    "V-Squat Machine": "compound",
    "Vertical Leg Press": "compound",
    "Walking Lunge": "compound",
    "Weighted Cable Crunch (Kneeling)": "isolation",
    "Wide-Grip Lat Pulldown": "compound",
    "Wrist Curl": "isolation",
    "Zercher Squat": "compound",
    "Zottman Curl": "isolation",
}
DEFAULT_EXERCISES = sorted(EXERCISE_INCREMENT.keys())

MUSCLE_GROUPS = ["Göğüs", "Sırt", "Omuz", "Biceps", "Triceps", "Quadriceps", "Hamstring", "Glute", "Baldır", "Core", "Ön Kol", "Trapez"]
MUSCLE_GROUP_DEFAULTS = {
    "Ab Wheel Rollout": ["Core"],
    "Arnold Press": ["Omuz", "Triceps"],
    "Assisted Dip Machine": ["Göğüs", "Triceps"],
    "Assisted Pull-up Machine": ["Sırt", "Biceps"],
    "Barbell Calf Raise": ["Baldır"],
    "Barbell Curl": ["Biceps"],
    "Barbell Hip Thrust": ["Glute", "Hamstring"],
    "Barbell Lunge": ["Quadriceps", "Glute"],
    "Barbell Overhead Press": ["Omuz", "Triceps"],
    "Barbell Pullover": ["Sırt", "Göğüs"],
    "Barbell Reverse Wrist Curl": ["Ön Kol"],
    "Barbell Row": ["Sırt", "Biceps"],
    "Barbell Shrug": ["Trapez"],
    "Barbell Skull Crusher": ["Triceps"],
    "Barbell Step-Up": ["Quadriceps", "Glute"],
    "Behind-the-Back Barbell Wrist Curl": ["Ön Kol"],
    "Behind-the-Neck Press": ["Omuz", "Triceps"],
    "Belt Squat Machine": ["Quadriceps", "Glute"],
    "Bench Dip": ["Triceps"],
    "Bench Press": ["Göğüs", "Triceps"],
    "Bicep Curl": ["Biceps"],
    "Bird Dog": ["Core"],
    "Bodyweight Step-Up": ["Glute", "Quadriceps"],
    "Bulgarian Split Squat": ["Quadriceps", "Glute"],
    "Cable Bayesian Curl": ["Biceps"],
    "Cable Crossover": ["Göğüs"],
    "Cable Crunch": ["Core"],
    "Cable Curl": ["Biceps"],
    "Cable Fly": ["Göğüs"],
    "Cable Front Raise": ["Omuz"],
    "Cable Hip Abduction": ["Glute"],
    "Cable Kickback": ["Glute"],
    "Cable Lateral Raise": ["Omuz"],
    "Cable Leg Curl": ["Hamstring"],
    "Cable Overhead Extension": ["Triceps"],
    "Cable Overhead Rope Extension": ["Triceps"],
    "Cable Pallof Press": ["Core"],
    "Cable Pull-Through": ["Glute", "Hamstring"],
    "Cable Pullover": ["Sırt"],
    "Cable Rear Delt Fly": ["Omuz", "Sırt"],
    "Cable Rope Hammer Curl": ["Biceps", "Ön Kol"],
    "Cable Row": ["Sırt"],
    "Cable Shrug": ["Trapez"],
    "Cable Upright Row": ["Omuz", "Trapez"],
    "Cable Woodchopper": ["Core"],
    "Cable Wrist Curl": ["Ön Kol"],
    "Calf Raise": ["Baldır"],
    "Captain's Chair Leg Raise": ["Core"],
    "Chest Dip": ["Göğüs", "Triceps"],
    "Chest Press Machine": ["Göğüs", "Triceps"],
    "Chest-Supported Dumbbell Row": ["Sırt"],
    "Chin-up": ["Sırt", "Biceps"],
    "Close-Grip Bench Press": ["Triceps", "Göğüs"],
    "Close-Grip Lat Pulldown": ["Sırt", "Biceps"],
    "Concentration Curl": ["Biceps"],
    "Cross-Body Hammer Curl": ["Biceps", "Ön Kol"],
    "Crunch Machine": ["Core"],
    "Dead Bug": ["Core"],
    "Dead Hang": ["Ön Kol", "Sırt"],
    "Deadlift": ["Sırt", "Hamstring", "Glute"],
    "Decline Bench Press": ["Göğüs", "Triceps"],
    "Decline Cable Fly": ["Göğüs"],
    "Decline Dumbbell Fly": ["Göğüs"],
    "Decline Dumbbell Press": ["Göğüs", "Triceps"],
    "Decline Push-up": ["Göğüs", "Triceps"],
    "Decline Sit-up": ["Core"],
    "Decline Smith Machine Press": ["Göğüs", "Triceps"],
    "Diamond Push-up": ["Triceps", "Göğüs"],
    "Dip": ["Triceps", "Göğüs"],
    "Donkey Calf Raise": ["Baldır"],
    "Drag Curl": ["Biceps"],
    "Dumbbell Calf Raise": ["Baldır"],
    "Dumbbell Curl": ["Biceps"],
    "Dumbbell Fly": ["Göğüs"],
    "Dumbbell Glute Bridge": ["Glute", "Hamstring"],
    "Dumbbell Hammer Curl": ["Biceps", "Ön Kol"],
    "Dumbbell Lunge": ["Quadriceps", "Glute"],
    "Dumbbell Preacher Curl": ["Biceps"],
    "Dumbbell Pullover": ["Sırt", "Göğüs"],
    "Dumbbell Rear Delt Fly": ["Omuz", "Sırt"],
    "Dumbbell Romanian Deadlift": ["Hamstring", "Glute"],
    "Dumbbell Shoulder Press": ["Omuz", "Triceps"],
    "Dumbbell Shrug": ["Trapez"],
    "Dumbbell Side Bend": ["Core"],
    "Dumbbell Skull Crusher": ["Triceps"],
    "Dumbbell Step-Up": ["Quadriceps", "Glute"],
    "Dumbbell Triceps Extension": ["Triceps"],
    "Dumbbell Upright Row": ["Omuz", "Trapez"],
    "Dumbbell Wrist Curl": ["Ön Kol"],
    "EZ Barbell Curl": ["Biceps"],
    "EZ-Bar Preacher Curl": ["Biceps"],
    "Ez Bar Skull Crusher": ["Triceps"],
    "Face Pull": ["Omuz", "Sırt"],
    "Farmer's Walk": ["Ön Kol", "Trapez"],
    "Flat Dumbbell Press": ["Göğüs", "Triceps"],
    "Floor Press (Barbell)": ["Göğüs", "Triceps"],
    "Floor Press (Dumbbell)": ["Göğüs", "Triceps"],
    "Front Raise": ["Omuz"],
    "Front Squat": ["Quadriceps", "Glute"],
    "Glute Bridge": ["Glute", "Hamstring"],
    "Glute Ham Raise": ["Hamstring", "Glute"],
    "Glute Machine": ["Glute"],
    "Goblet Squat": ["Quadriceps", "Glute"],
    "Good Morning": ["Hamstring", "Glute"],
    "Hack Squat Machine": ["Quadriceps"],
    "Hanging Knee Raise": ["Core"],
    "Hanging Leg Raise": ["Core"],
    "Hip Abduction Machine": ["Glute"],
    "Hip Adduction Machine": ["Glute"],
    "Hip Thrust": ["Glute", "Hamstring"],
    "Hyperextension": ["Hamstring", "Glute"],
    "Incline Bench Press": ["Göğüs", "Omuz"],
    "Incline Cable Fly": ["Göğüs"],
    "Incline Curl": ["Biceps"],
    "Incline Dumbbell Curl": ["Biceps"],
    "Incline Dumbbell Fly": ["Göğüs"],
    "Incline Dumbbell Press": ["Göğüs", "Omuz"],
    "Incline Push-up": ["Göğüs", "Omuz"],
    "Incline Smith Machine Press": ["Göğüs", "Omuz"],
    "Inverted Row": ["Sırt", "Biceps"],
    "JM Press": ["Triceps", "Göğüs"],
    "Kettlebell Farmer's Walk": ["Ön Kol", "Trapez"],
    "Landmine Press": ["Göğüs", "Omuz"],
    "Lat Pulldown": ["Sırt"],
    "Lateral Raise (Dumbbell/Cable)": ["Omuz"],
    "Leg Curl": ["Hamstring"],
    "Leg Extension": ["Quadriceps"],
    "Leg Press": ["Quadriceps", "Glute"],
    "Leg Press Calf Raise": ["Baldır"],
    "Leg Raise": ["Core"],
    "Lying Leg Curl Machine": ["Hamstring"],
    "Machine Ab Coaster": ["Core"],
    "Machine Bicep Curl": ["Biceps"],
    "Machine Crunch": ["Core"],
    "Machine Decline Chest Press": ["Göğüs", "Triceps"],
    "Machine Glute Kickback": ["Glute"],
    "Machine High Row": ["Sırt"],
    "Machine Hip Thrust": ["Glute", "Hamstring"],
    "Machine Incline Chest Press": ["Göğüs", "Omuz"],
    "Machine Lateral Raise": ["Omuz"],
    "Machine Leg Extension": ["Quadriceps"],
    "Machine Low Row": ["Sırt"],
    "Machine Preacher Curl": ["Biceps"],
    "Machine Rear Delt Fly": ["Omuz", "Sırt"],
    "Machine Row (Chest-Supported)": ["Sırt"],
    "Machine Shoulder Press": ["Omuz", "Triceps"],
    "Machine Shrug": ["Trapez"],
    "Machine Triceps Extension": ["Triceps"],
    "Meadows Row": ["Sırt"],
    "Nordic Curl": ["Hamstring"],
    "Overhead Press": ["Omuz", "Triceps"],
    "Overhead Triceps Extension": ["Triceps"],
    "Pec Deck (Chest Fly Machine)": ["Göğüs"],
    "Pendlay Row": ["Sırt", "Biceps"],
    "Pendulum Squat Machine": ["Quadriceps", "Glute"],
    "Plank": ["Core"],
    "Plate Front Raise": ["Omuz"],
    "Plate Pinch Hold": ["Ön Kol"],
    "Preacher Curl": ["Biceps"],
    "Pull-up": ["Sırt", "Biceps"],
    "Push Press": ["Omuz", "Triceps"],
    "Push-up": ["Göğüs", "Triceps"],
    "Rack Pull": ["Sırt", "Hamstring"],
    "Reverse Barbell Curl": ["Ön Kol", "Biceps"],
    "Reverse Pec Deck": ["Omuz", "Sırt"],
    "Reverse Wrist Curl": ["Ön Kol"],
    "Reverse-Grip Lat Pulldown": ["Sırt", "Biceps"],
    "Romanian Deadlift (RDL)": ["Hamstring", "Glute"],
    "Rope Pushdown": ["Triceps"],
    "Russian Twist": ["Core"],
    "Seated Barbell Shoulder Press": ["Omuz", "Triceps"],
    "Seated Cable Row": ["Sırt", "Biceps"],
    "Seated Calf Raise": ["Baldır"],
    "Seated Dumbbell Shoulder Press": ["Omuz", "Triceps"],
    "Seated Leg Curl Machine": ["Hamstring"],
    "Shoulder Press (Dumbbell)": ["Omuz", "Triceps"],
    "Side Plank": ["Core"],
    "Single-Arm Cable Chest Press": ["Göğüs"],
    "Single-Arm Cable Pushdown": ["Triceps"],
    "Single-Arm Dumbbell Row": ["Sırt", "Biceps"],
    "Single-Arm Lat Pulldown": ["Sırt"],
    "Single-Leg Calf Raise": ["Baldır"],
    "Single-Leg Leg Press": ["Quadriceps", "Glute"],
    "Single-Leg Romanian Deadlift": ["Hamstring", "Glute"],
    "Sissy Squat": ["Quadriceps"],
    "Sissy Squat Machine": ["Quadriceps"],
    "Sit-up": ["Core"],
    "Smith Machine Bench Press": ["Göğüs", "Triceps"],
    "Smith Machine Calf Raise": ["Baldır"],
    "Smith Machine Hip Thrust": ["Glute", "Hamstring"],
    "Smith Machine Romanian Deadlift": ["Hamstring", "Glute"],
    "Smith Machine Row": ["Sırt"],
    "Smith Machine Shoulder Press": ["Omuz", "Triceps"],
    "Smith Machine Shrug": ["Trapez"],
    "Smith Machine Squat": ["Quadriceps", "Glute"],
    "Spider Curl": ["Biceps"],
    "Squat": ["Quadriceps", "Glute"],
    "Standing Calf Raise Machine": ["Baldır"],
    "Standing Leg Curl Machine": ["Hamstring"],
    "Stiff-Leg Deadlift": ["Hamstring", "Glute"],
    "Straight Arm Pulldown": ["Sırt"],
    "Sumo Deadlift": ["Sırt", "Hamstring", "Glute"],
    "Svend Press": ["Göğüs"],
    "T-Bar Row": ["Sırt", "Biceps"],
    "Triceps Dip Machine": ["Triceps", "Göğüs"],
    "Triceps Kickback": ["Triceps"],
    "Triceps Pushdown": ["Triceps"],
    "Upright Row": ["Omuz", "Trapez"],
    "V-Bar Pushdown": ["Triceps"],
    "V-Squat Machine": ["Quadriceps", "Glute"],
    "Vertical Leg Press": ["Quadriceps", "Glute"],
    "Walking Lunge": ["Quadriceps", "Glute"],
    "Weighted Cable Crunch (Kneeling)": ["Core"],
    "Wide-Grip Lat Pulldown": ["Sırt"],
    "Wrist Curl": ["Ön Kol"],
    "Zercher Squat": ["Quadriceps", "Glute"],
    "Zottman Curl": ["Biceps", "Ön Kol"],
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
        "settings": {"lastBackupAt": None, "weightUnit": "kg"},
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
    # KULLANICI ISTEGI: yeni kurulumda ornek/varsayilan 3 gunluk program hic
    # OLUSTURULMASIN - program bos baslasin, gunleri kullanici kendi ekleyecek.
    # (Eskiden burada build_seed_program() cagrilip ornek bir program
    # dolduruluyordu - artik program.days bos ([]) kalıyor, default_state()
    # zaten boyle donuyor.)
    state = default_state()
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


def remove_history_session(state, session_id):
    """Gecmisten TEK BIR antrenman kaydini kalici olarak siler (geri alinamaz)."""
    state["history"] = [s for s in state["history"] if s["id"] != session_id]


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
def rir_badge_info(s, ex):
    """Bir setin RIR degerini hedef RIR ile karsilastirip kisa bir etiket
    dondurur: 'easy' (cok kolay, agirlik artir), 'hard' (cok zor, hafiflet),
    'ontarget' (tam hedefte), 'neutral' (hedef yoksa, sadece deger)."""
    if s.get("rir") is None:
        return None
    rir = s["rir"]
    target_rir = ex.get("targetRIR")
    if target_rir is None:
        return {"text": f"RIR {rir}", "kind": "neutral"}
    diff = rir - target_rir
    if diff >= 2:
        return {"text": f"RIR {rir} · artır", "kind": "easy"}
    if diff <= -2:
        return {"text": f"RIR {rir} · hafiflet", "kind": "hard"}
    return {"text": f"RIR {rir} · hedefte", "kind": "ontarget"}


def history_exercise_compare(ex):
    has_target = bool(ex.get("targetSets") or ex.get("targetRepsMin") or ex.get("targetRepsMax") or ex.get("targetWeight"))
    working = [s for s in ex["sets"] if not s.get("isWarmup")]
    best_weight = max((s["weight"] for s in working), default=0)
    weight_diff_kg = None  # sadece agirlik-hedefi dalinda doldurulur (asagida)

    if not working and has_target:
        delta = ("none", "SET GİRİLMEDİ")
    elif ex.get("targetWeight"):
        # NOT: burada kg-sabit bir metin YAZMIYORUZ artik - core.py agirlik
        # birimini (kg/lb) bilmiyor/bilmemeli. Ham kg farkini weight_diff_kg
        # olarak donduruyoruz; main.py bunu kullanicinin sectigi birimde
        # kendi formatliyor (bkz. HistoryScreen.session_card).
        diff = round(best_weight - ex["targetWeight"], 2)
        weight_diff_kg = diff
        if diff > 0:
            delta = ("up", None)
        elif diff < 0:
            delta = ("down", None)
        else:
            delta = ("eq", "HEDEFTE")
    elif working and (ex.get("targetRepsMin") or ex.get("targetRepsMax")):
        # Cogu program agirlik hedefi degil tekrar araligi kullaniyor (ornegin
        # 3x6-8). Bu durumda gercek performansi araliga gore degerlendiriyoruz:
        # tum setler tavana ulastiysa ilerleme zamani, herhangi biri tabanin
        # altinda kaldiysa hedefin altinda, aksi halde araliktayiz demektir.
        rmin = ex.get("targetRepsMin") or 0
        rmax = ex.get("targetRepsMax") or rmin
        reps = [s["reps"] for s in working]
        if rmax and all(r >= rmax for r in reps):
            delta = ("up", "▲ TAVANA ULAŞTI")
        elif rmin and any(r < rmin for r in reps):
            delta = ("down", "▼ HEDEFİN ALTINDA")
        else:
            delta = ("eq", "ARALIKTA")
    else:
        delta = (None, None)

    sets_badge = None
    if ex.get("targetSets"):
        done = len(working)
        sets_badge = (done, ex["targetSets"], "ok" if done >= ex["targetSets"] else "under")

    return {"hasTarget": has_target, "delta": delta, "setsBadge": sets_badge, "bestWeight": best_weight,
            "weightDiffKg": weight_diff_kg}


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
