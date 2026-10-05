import os
import io
from datetime import datetime, timedelta
import base64
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Astronaut Health", page_icon=None, layout="wide")

HERE = os.path.dirname(os.path.abspath(__file__))
ss = st.session_state
ss.setdefault("stage", "welcome")   # welcome -> onboard -> app
ss.setdefault("profile", None)
ss.setdefault("weekly", [])
ss.setdefault("landing", [])
ss.setdefault("exercise", [])
ss.setdefault("entries", [])        # every check-in of this visitor (first one = onboarding)

# ---------- Colors ----------
COL = {"green": "#00FF88", "yellow": "#FFD600", "red": "#FF3B5C"}
CYAN, PINK, WHITE, GREY = "#00E5FF", "#FF4DFF", "#FFFFFF", "#B0B6BE"
STATUS_ICON = {"green": "", "yellow": "", "red": ""}
RANK = {"red": 0, "yellow": 1, "green": 2}


# ---------- Background: your own space image (space.jpg / .png / .webp) or built-in CSS space ----------
def find_bg():
    for base in ("space", "background", "bg"):
        for ext in ("jpg", "jpeg", "png", "webp"):
            path = os.path.join(HERE, f"{base}.{ext}")
            if os.path.exists(path):
                return path
    return None


@st.cache_data(show_spinner=False)
def load_bg(path, mtime):
    """Shrink the image (max 1920px) so the page stays fast, return base64 JPEG."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    img.thumbnail((1920, 1920))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


bg_b64 = None
_bg_path = find_bg()
if _bg_path:
    try:
        bg_b64 = load_bg(_bg_path, os.path.getmtime(_bg_path))
    except Exception:
        bg_b64 = None

# Layers (top to bottom): drifting stars, then your photo (+ dark tint) or a breathing nebula.
# A star layer is one tile; moving it by exactly one tile makes a seamless loop.
_stars = [("radial-gradient(1px 1px at 20px 30px, #fff, transparent)", 230, 190),
          ("radial-gradient(1px 1px at 120px 90px, #cfe8ff, transparent)", 310, 270),
          ("radial-gradient(2px 2px at 60px 150px, #fff, transparent)", 410, 350),
          ("radial-gradient(1.5px 1.5px at 200px 40px, #ffd9ff, transparent)", 530, 430),
          ("radial-gradient(1px 1px at 300px 220px, #fff, transparent)", 270, 310),
          ("radial-gradient(2px 2px at 90px 260px, #bfefff, transparent)", 610, 500),
          ("radial-gradient(1px 1px at 400px 120px, #fff, transparent)", 470, 390),
          ("radial-gradient(1px 1px at 50px 70px, #fff, transparent)", 190, 150),
          ("radial-gradient(1.5px 1.5px at 140px 100px, #cfe8ff, transparent)", 350, 260)]
_nebula = [("radial-gradient(ellipse at 15% 10%, rgba(120,40,200,0.34), transparent 55%)",
            "0% 0%", "100% 100%", "0% 0%"),
           ("radial-gradient(ellipse at 85% 35%, rgba(0,140,255,0.24), transparent 55%)",
            "100% 0%", "0% 100%", "100% 0%"),
           ("radial-gradient(ellipse at 45% 105%, rgba(255,60,140,0.20), transparent 50%)",
            "50% 100%", "50% 0%", "50% 100%")]

_L = []  # (image, size, repeat, pos0, pos50, pos100)
for g, w, h in _stars:
    _L.append((g, f"{w}px {h}px", "repeat", "0px 0px", f"{w // 2}px {h // 2}px", f"{w}px {h}px"))
if bg_b64:
    _L.append(("linear-gradient(rgba(0,0,0,0.42), rgba(0,0,0,0.42))", "100% 100%", "no-repeat",
               "0 0", "0 0", "0 0"))
    _L.append((f"url(data:image/jpeg;base64,{bg_b64})", "cover", "no-repeat", "center", "center", "center"))
else:
    for g, p0, p50, p100 in _nebula:
        _L.append((g, "140% 140%", "no-repeat", p0, p50, p100))

_join = lambda i: ", ".join(l[i] for l in _L)
BG_CSS = (f"background-color:#000; background-image:{_join(0)}; background-size:{_join(1)}; "
          f"background-repeat:{_join(2)}; background-position:{_join(3)}; background-attachment:fixed;")
ANIM_CSS = f"""
@keyframes drift {{ 0% {{ background-position:{_join(3)}; }} 50% {{ background-position:{_join(4)}; }}
                   100% {{ background-position:{_join(5)}; }} }}
.stApp, [data-testid="stAppViewContainer"] {{ animation: drift 80s linear infinite; }}
.shoot {{ position:fixed; top:0; left:0; width:150px; height:2px; opacity:0; pointer-events:none; z-index:1;
          background:linear-gradient(90deg, rgba(255,255,255,0), #fff); }}
.shoot.s1 {{ animation: shoot1 11s ease-in infinite; }}
.shoot.s2 {{ animation: shoot2 11s ease-in 5.5s infinite; }}
@keyframes shoot1 {{ 0% {{ transform:translate(8vw,4vh) rotate(32deg); opacity:0; }}
                    2% {{ opacity:1; }}
                    9% {{ transform:translate(60vw,52vh) rotate(32deg); opacity:0; }}
                    100% {{ transform:translate(60vw,52vh) rotate(32deg); opacity:0; }} }}
@keyframes shoot2 {{ 0% {{ transform:translate(45vw,2vh) rotate(38deg); opacity:0; }}
                    2% {{ opacity:1; }}
                    9% {{ transform:translate(92vw,58vh) rotate(38deg); opacity:0; }}
                    100% {{ transform:translate(92vw,58vh) rotate(38deg); opacity:0; }} }}
@media (prefers-reduced-motion: reduce) {{
  .stApp, [data-testid="stAppViewContainer"] {{ animation:none; }} .shoot {{ display:none; }} }}
"""

HIDE_SIDEBAR = "" if ss.stage == "app" else (
    '[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], '
    '[data-testid="collapsedControl"] { display:none; }')

st.markdown(f"""
<style>
.stApp, [data-testid="stAppViewContainer"] {{ {BG_CSS} color:{WHITE}; }}
{ANIM_CSS}
[data-testid="stHeader"] {{ background:transparent; }}
[data-testid="stSidebar"] {{ background:rgba(4,4,16,0.88); border-right:1px solid #2a2a55; }}
{HIDE_SIDEBAR}
h1 {{ color:{CYAN} !important; }}
h2, h3 {{ color:{PINK} !important; }}
p, label, li, span, div[data-testid="stMarkdownContainer"] {{ color:{WHITE}; }}
[data-testid="stCaptionContainer"] {{ color:{GREY} !important; }}
input, textarea, [data-baseweb="select"] > div {{ background:#111 !important; color:{WHITE} !important; }}
input::placeholder {{ color:#8a8f98 !important; }}
[data-testid="stForm"] {{ background:rgba(8,8,28,0.80); border:1px solid #2a2a55; border-radius:16px; padding:22px; }}
.stButton > button, [data-testid="stFormSubmitButton"] > button {{
  background:linear-gradient(90deg,{CYAN},{PINK}); color:#000 !important; font-weight:800;
  border:none; border-radius:999px; padding:0.55rem 2.2rem; }}
.stButton > button p, [data-testid="stFormSubmitButton"] > button p {{ color:#000 !important; }}
.hero {{ text-align:center; margin-top:12vh; background:rgba(0,0,0,0.45); border-radius:20px; padding:36px 20px; }}
.hero .big {{ font-size:4.5rem; }}
.hero h1 {{ font-size:2.4rem; margin:0; padding:0; text-align:center; }}
.hero p {{ color:{GREY}; font-size:1.1rem; }}
.hcard {{ background:rgba(8,8,28,0.78); backdrop-filter:blur(3px); border:2px solid; border-radius:14px; padding:14px 16px; margin-bottom:10px; }}
.hcard .t {{ font-size:1.05rem; font-weight:700; }}
.hcard .s {{ font-size:1.6rem; font-weight:800; margin:2px 0 6px 0; }}
.hcard .v {{ font-size:1rem; font-weight:700; color:{WHITE}; }}
.hcard .r {{ font-size:0.85rem; color:{GREY}; }}
.banner {{ border-left:6px solid; background:rgba(8,8,28,0.78); border-radius:8px; padding:12px 16px; margin:8px 0; }}
.rhero {{ display:flex; align-items:center; gap:22px; background:rgba(8,8,28,0.82); border:2px solid;
          border-radius:18px; padding:18px 24px; margin:14px 0; }}
.rhero .ring {{ width:104px; height:104px; border-radius:50%; display:flex; align-items:center;
               justify-content:center; flex:none; }}
.rhero .ring span {{ width:78px; height:78px; border-radius:50%; background:#08081c; display:flex;
                    align-items:center; justify-content:center; font-size:1.9rem; font-weight:800; }}
.rhero .rt {{ font-size:1.05rem; color:{CYAN}; font-weight:700; }}
.rhero .rs {{ font-size:1.7rem; font-weight:800; margin:2px 0; }}
.rhero .rr {{ font-size:0.9rem; color:{GREY}; }}
</style>
<div class='shoot s1'></div><div class='shoot s2'></div>
""", unsafe_allow_html=True)

# =====================================================================
# Health rules (prototype): YOUR numbers are compared with normal ranges
# =====================================================================
SYMPTOMS = ["Fever", "Rash", "Dizziness", "Nausea"]
PROTEIN_PER_KG = 1.2
STRENGTH_TARGET = 360        # strength work on ISS-style routine: about 60 min x 6 days per week
WEIGHT_BEARING_TARGET = 180  # treadmill / impact work: about 30 min x 6 days per week

DEFAULT_ENTRY = {"weight_kg": 70.0, "heart_rate": 70.0, "temperature": 36.6, "sleep_hours": 7.5,
                 "calories": 2200.0, "protein_g": 80.0, "calcium_mg": 900.0,
                 "strength_min_week": 360.0, "weight_bearing_min_week": 180.0, "symptoms": [],
                 "sbp": 120.0, "dbp": 80.0, "mood": "Nothing", "stress": 2, "anxiety": 2,
                 "fluid_l": 2.0, "vitamin_d_iu": 800.0, "urine_ml": 1500.0, "radiation_msv": 0.7}

SYSTEMS = {
    "Bone": {"icon": "", "metric": "weight_bearing_min_week",
             "action": {"green": "Keep up calcium and weight-bearing exercise",
                        "yellow": "Improve either calcium intake or weight-bearing exercise",
                        "red": "Add calcium and weight-bearing exercise, and talk to a doctor about bone health"}},
    "Heart": {"icon": "", "metric": "heart_rate",
              "action": {"green": "Keep your routine",
                         "yellow": "Rest and recheck your heart rate in 2 hours",
                         "red": "Stop exercise and contact a doctor"}},
    "Sleep": {"icon": "", "metric": "sleep_hours",
              "action": {"green": "Keep your routine",
                         "yellow": "Fix your sleep schedule tonight",
                         "red": "Talk to a doctor about your sleep"}},
    "Immune": {"icon": "", "metric": "temperature",
               "action": {"green": "Keep monitoring",
                          "yellow": "Rest, drink water, recheck temperature in 2 hours",
                          "red": "Check symptoms and contact a doctor"}},
    "Weight": {"icon": "", "metric": "weight_kg",
               "action": {"green": "Weight stable - keep it up",
                          "yellow": "Eat more calories and protein and log your meals",
                          "red": "Talk to a dietitian or doctor about your weight change"}},
    "Nutrition": {"icon": "", "metric": "calories",
                  "action": {"green": "Food intake on track",
                             "yellow": "Adjust calories or protein toward your target",
                             "red": "Talk to a dietitian: intake is far from your target"}},
    "Muscle": {"icon": "", "metric": "strength_min_week",
               "action": {"green": "Muscle-protecting routine on track",
                          "yellow": "Add 15 min of squats / deadlifts / rows on more days",
                          "red": "Start regular strength sessions this week"}},
}


def band(v, green, yellow):
    if green[0] <= v <= green[1]:
        return "green"
    if yellow[0] <= v <= yellow[1]:
        return "yellow"
    return "red"


def worst(*colors):
    return min(colors, key=lambda c: RANK[c])


def targets(p, weight):
    """Daily targets from sex, age, height and weight (Mifflin-St Jeor x 1.5)."""
    bmr = 10 * weight + 6.25 * p["height_cm"] - 5 * p["age"] + (5 if p["sex"] == "Male" else -161)
    calcium = 1200 if (p["sex"] == "Female" and p["age"] > 50) or (p["sex"] == "Male" and p["age"] > 70) else 1000
    return {"kcal": bmr * 1.5, "protein": PROTEIN_PER_KG * weight, "calcium": calcium}


def evaluate(p, e):
    """Turn ONE set of your numbers into a color, a reason and an action for every body system."""
    t = targets(p, e["weight_kg"])
    bmi = e["weight_kg"] / ((p["height_cm"] / 100) ** 2)
    out = {}

    def add(system, color, value, normal, reason):
        out[system] = {"color": color, "value": value, "normal": normal, "reason": reason,
                       "icon": SYSTEMS[system]["icon"], "action": SYSTEMS[system]["action"][color]}

    # Heart
    c = band(e["heart_rate"], (50, 100), (40, 110))
    add("Heart", c, f"{e['heart_rate']:.0f} bpm", "50-100 bpm",
        f"Your resting heart rate is {e['heart_rate']:.0f} bpm (normal 50-100)")

    # Sleep
    c = band(e["sleep_hours"], (7, 9), (6, 10))
    add("Sleep", c, f"{e['sleep_hours']:.1f} h/night", "7-9 h/night",
        f"You sleep {e['sleep_hours']:.1f} hours per night (normal 7-9)")

    # Immune: temperature + symptoms
    n_sym = len(e["symptoms"])
    c_temp = band(e["temperature"], (36.0, 37.5), (35.5, 38.0))
    c_sym = "green" if n_sym == 0 else "yellow" if n_sym <= 2 else "red"
    sym_text = ", ".join(e["symptoms"]) if n_sym else "no symptoms"
    add("Immune", worst(c_temp, c_sym), f"{e['temperature']:.1f} C, {n_sym} symptom(s)",
        "36.0-37.5 C, no symptoms",
        f"Temperature {e['temperature']:.1f} C (normal 36.0-37.5) and {sym_text}")

    # Weight: change from your usual weight + BMI
    usual = p["weight_usual_kg"]
    change = e["weight_kg"] - usual
    pct = change / usual * 100
    c_chg = "green" if abs(pct) < 2 else "yellow" if abs(pct) < 5 else "red"
    c_bmi = band(bmi, (18.5, 29.9), (16.0, 40.0))
    direction = "lost" if change < 0 else "gained"
    add("Weight", worst(c_chg, c_bmi), f"{e['weight_kg']:.1f} kg ({abs(change):.1f} kg {direction})",
        "within 2% of usual weight, BMI 18.5-29.9",
        f"Weight {e['weight_kg']:.1f} kg is {abs(pct):.1f}% {'below' if change < 0 else 'above'} "
        f"your usual {usual:.1f} kg (BMI {bmi:.1f})")

    # Nutrition: calories + protein vs your own targets
    r_k = e["calories"] / t["kcal"]
    r_p = e["protein_g"] / t["protein"]
    c_k = band(r_k, (0.9, 1.15), (0.75, 1.3))
    c_p = "green" if r_p >= 0.85 else "yellow" if r_p >= 0.6 else "red"
    add("Nutrition", worst(c_k, c_p), f"{e['calories']:.0f} kcal, {e['protein_g']:.0f} g protein",
        f"about {t['kcal']:.0f} kcal, {t['protein']:.0f} g protein",
        f"You eat {e['calories']:.0f} kcal (target about {t['kcal']:.0f}) and "
        f"{e['protein_g']:.0f} g protein (target about {t['protein']:.0f})")

    # Muscle: strength exercise
    s = e["strength_min_week"]
    c = "green" if s >= 0.8 * STRENGTH_TARGET else "yellow" if s >= 0.4 * STRENGTH_TARGET else "red"
    add("Muscle", c, f"{s:.0f} min/week", f"{STRENGTH_TARGET} min/week of strength work",
        f"You do {s:.0f} min/week of strength exercise (target {STRENGTH_TARGET})")

    # Bone: calcium + weight-bearing exercise
    ca_ok = e["calcium_mg"] >= 0.8 * t["calcium"]
    wb_ok = e["weight_bearing_min_week"] >= 0.8 * WEIGHT_BEARING_TARGET
    c = "green" if ca_ok and wb_ok else "yellow" if ca_ok or wb_ok else "red"
    add("Bone", c, f"{e['calcium_mg']:.0f} mg Ca, {e['weight_bearing_min_week']:.0f} min/week",
        f"{t['calcium']} mg calcium, {WEIGHT_BEARING_TARGET} min/week weight-bearing",
        f"Calcium {e['calcium_mg']:.0f} mg/day (target {t['calcium']}) and weight-bearing exercise "
        f"{e['weight_bearing_min_week']:.0f} min/week (target {WEIGHT_BEARING_TARGET})")

    # keep the display order
    return {k: out[k] for k in SYSTEMS}


def tint(text, color):
    """Wrap text in a status color (green/yellow/red or a hex code)."""
    return f"<span style='color:{COL.get(color, color)}'>{text}</span>"


def card(system, info):
    c = COL[info["color"]]
    st.markdown(
        f"<div class='hcard' style='border-color:{c}'>"
        f"<div class='t' style='color:{CYAN}'>{info['icon']} {system}</div>"
        f"<div class='s' style='color:{c}'>{STATUS_ICON[info['color']]} {info['color'].title()}</div>"
        f"<div class='v'>Your value: {info['value']}</div>"
        f"<div class='r'>Normal: {info['normal']}</div></div>", unsafe_allow_html=True)


def banner(text, color):
    st.markdown(f"<div class='banner' style='border-color:{COL.get(color, color)}'>{text}</div>",
                unsafe_allow_html=True)


def entry_fields(d, with_weight=False):
    """Daily health inputs (heart rate, sleep, temperature, abnormal checklist, calcium ...)."""
    c1, c2 = st.columns(2)
    with c1:
        if with_weight:
            weight = st.number_input("Weight now (kg)", 30.0, 200.0, float(d["weight_kg"]), step=0.5)
        else:
            weight = float(d["weight_kg"])   # weight comes from onboarding / the weekly test
        hr = st.number_input("Heart rate (bpm)", 30.0, 200.0, float(d["heart_rate"]), step=1.0)
        sleep = st.number_input("Sleep per night (hours)", 0.0, 14.0, float(d["sleep_hours"]), step=0.5)
        temp = st.number_input("Body temperature (C)", 34.0, 42.0, float(d["temperature"]), step=0.1)
        st.markdown("**Anything abnormal right now?**")
        syms = [sy for sy in SYMPTOMS if st.checkbox(sy, value=(sy in d["symptoms"]), key=f"sym_{sy}")]
    with c2:
        ca = st.number_input("Calcium intake (mg per day)", 0.0, 3000.0, float(d["calcium_mg"]), step=50.0)
        st.markdown("**Food and exercise** (used by the Nutrition, Muscle and Bone cards)")
        cal = st.number_input("Food intake (kcal per day)", 0.0, 8000.0, float(d["calories"]), step=50.0)
        prot = st.number_input("Protein (g per day)", 0.0, 400.0, float(d["protein_g"]), step=5.0)
        strength = st.number_input("Strength exercise (min per week)", 0.0, 1000.0,
                                   float(d["strength_min_week"]), step=10.0)
        wbear = st.number_input("Treadmill / running / impact exercise (min per week)", 0.0, 1500.0,
                                float(d["weight_bearing_min_week"]), step=10.0)
    return {"weight_kg": weight, "heart_rate": hr, "temperature": temp, "sleep_hours": sleep,
            "symptoms": syms, "calories": cal, "protein_g": prot, "calcium_mg": ca,
            "strength_min_week": strength, "weight_bearing_min_week": wbear}


def extra_fields(d):
    """Daily extras: BP, mood, stress, anxiety, fluids, vitamin D, urine, radiation."""
    moods = ["Happy", "Calm", "Nothing", "Sad", "Angry"]
    c1, c2 = st.columns(2)
    with c1:
        sbp = st.number_input("Blood pressure - systolic", 70.0, 220.0, float(d.get("sbp", 120.0)), step=1.0)
        dbp = st.number_input("Blood pressure - diastolic", 40.0, 140.0, float(d.get("dbp", 80.0)), step=1.0)
        mood = st.radio("Mood", moods, index=moods.index(d.get("mood", "Nothing")) if d.get("mood", "Nothing") in moods else 2, horizontal=True)
        stress = st.slider("Stress (1-5)", 1, 5, int(d.get("stress", 2)))
        anx = st.slider("Anxiety (1-5)", 1, 5, int(d.get("anxiety", 2)))
    with c2:
        fluid = st.number_input("Fluid intake (L per day)", 0.0, 10.0, float(d.get("fluid_l", 2.0)), step=0.1)
        vitd = st.number_input("Vitamin D intake (IU per day)", 0.0, 10000.0, float(d.get("vitamin_d_iu", 800.0)), step=100.0)
        urine = st.number_input("Urine volume (mL per day)", 0.0, 5000.0, float(d.get("urine_ml", 1500.0)), step=50.0)
        rad = st.number_input("Radiation dose (mSv per day)", 0.0, 50.0, float(d.get("radiation_msv", 0.7)), step=0.1)
    return {"sbp": sbp, "dbp": dbp, "mood": mood, "stress": stress, "anxiety": anx,
            "fluid_l": fluid, "vitamin_d_iu": vitd, "urine_ml": urine, "radiation_msv": rad}


# =====================================================================
# WEEKLY REPORT: shown under the weekly test (score, cards, plain words, EDA charts)
# =====================================================================
SCORE_PTS = {"green": 100, "yellow": 60, "red": 20}
MOOD_COL = {"Happy": COL["green"], "Calm": CYAN, "Nothing": GREY, "Sad": COL["yellow"], "Angry": COL["red"]}


def _orth(r):
    """Stand test: heart-rate rise and systolic BP drop after standing."""
    hr0 = r.get("hr_0min", r["hr_3min"])
    s0 = r.get("sys_0min", r["sys_3min"])
    rise = max(r[f"hr_{t}min"] for t in (3, 7, 15)) - hr0
    drop = s0 - min(r[f"sys_{t}min"] for t in (3, 7, 15))
    return rise, drop


def _rcard(title, value, note, color):
    c = COL[color]
    return (f"<div class='hcard' style='border-color:{c}'><div class='t' style='color:{CYAN}'>{title}</div>"
            f"<div class='s' style='color:{c}'>{value}</div><div class='r'>{note}</div></div>")


def _style(ch, title, h=230):
    return (ch.properties(title=title, height=h, background="#05051a")
            .configure_axis(labelColor=WHITE, titleColor=CYAN, gridColor="#222", domainColor="#444")
            .configure_legend(labelColor=WHITE, titleColor=CYAN)
            .configure_title(color=PINK, fontSize=14)
            .configure_view(stroke=None))


def _line(df, x, y, title, ytitle, xtitle, color=CYAN, ref=None, domain=None):
    scale = alt.Scale(domain=domain) if domain else alt.Scale(zero=False)
    ch = alt.Chart(df).mark_line(point=alt.OverlayMarkDef(filled=True, size=80), color=color, strokeWidth=3).encode(
        x=alt.X(f"{x}:O", title=xtitle), y=alt.Y(f"{y}:Q", title=ytitle, scale=scale), tooltip=[x, y])
    if ref is not None:
        ch = ch + alt.Chart(pd.DataFrame({"ref": [ref]})).mark_rule(
            color=COL["yellow"], strokeDash=[6, 4]).encode(y="ref:Q")
    return _style(ch, title)


def _bars(df, x, y, title, ytitle, xtitle):
    """Bar chart where every bar uses the hex color stored in the 'color' column."""
    ch = alt.Chart(df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X(f"{x}:O", title=xtitle), y=alt.Y(f"{y}:Q", title=ytitle),
        color=alt.Color("color:N", scale=None, legend=None), tooltip=[x, y])
    return _style(ch, title)


def _show(ch):
    st.altair_chart(ch, width="stretch")


def show_weekly_report():
    """Weekly report under the weekly test: health score, status cards, plain words and EDA charts."""
    rows = ss.weekly
    if not rows:
        return
    p, ents = ss.profile, ss.entries
    cur, first = rows[-1], rows[0]
    prev = rows[-2] if len(rows) > 1 else None
    wk_no = len(rows)
    tests, daily = [], []   # each item: (title, value, note, color, tip)

    def delta(key, unit):
        return "first weekly test" if prev is None else f"{cur[key] - prev[key]:+.1f} {unit} vs last week"

    # ---- this week's tests
    usual = p["weight_usual_kg"]
    wpc = (cur["weight_kg"] - usual) / usual * 100
    c = "green" if abs(wpc) < 2 else "yellow" if abs(wpc) < 5 else "red"
    tests.append(("Weight", f"{cur['weight_kg']:.1f} kg", f"{wpc:+.1f}% vs before flight | {delta('weight_kg', 'kg')}", c,
                  "Eat enough calories and protein and keep up strength work. Talk to a dietitian if it continues."))

    if len(rows) == 1 or not first["grip_kg"]:
        c, gnote = "green", "baseline set - later weeks are compared with this"
    else:
        gpc = (cur["grip_kg"] - first["grip_kg"]) / first["grip_kg"] * 100
        c = "green" if gpc >= -5 else "yellow" if gpc >= -10 else "red"
        gnote = f"{gpc:+.1f}% vs your first test | {delta('grip_kg', 'kg')}"
    tests.append(("Grip strength", f"{cur['grip_kg']:.0f} kg", gnote, c,
                  "Muscle may be weakening. Add resistance (ARED) sessions and check protein intake."))

    rise, drop = _orth(cur)
    c = "green" if rise <= 20 else "yellow" if rise <= 30 else "red"
    tests.append(("Heart rate on standing", f"{rise:+.0f} bpm", "rise after standing | normal: under 20 bpm", c,
                  "Your heart works hard to hold blood pressure. Drink fluids and stand up slowly."))
    c = "green" if drop < 10 else "yellow" if drop < 20 else "red"
    tests.append(("Blood pressure on standing", f"{-drop:+.0f} mmHg", "systolic change | normal: drop under 10",
                  c, "A big drop means fainting risk. Hydrate, move slowly and tell the doctor."))

    nv = int(bool(cur["blurry_vision"])) + int(bool(cur["headache"]))
    vtxt = " and ".join(x for x, f in (("Blurry vision", cur["blurry_vision"]), ("Headache", cur["headache"])) if f)
    tests.append(("Vision", vtxt or "Clear", "blur or headache check", ["green", "yellow", "red"][nv],
                  "Report this to the flight surgeon. Eye pressure changes in space can cause blur and headache."))

    uv = cur["urine_ml"]
    tests.append(("Urine volume", f"{uv:.0f} mL", "normal: 1000-2500 mL", band(uv, (1000, 2500), (500, 3000)),
                  "Adjust your fluid intake and recheck tomorrow."))

    ph, ca = cur["ph"], cur["calcium_result"]
    acid = cur.get("acidity_result", "Normal")
    c = worst("green" if 5.0 <= ph <= 7.5 else "yellow", "green" if ca in ("Normal", "Not tested") else "yellow")
    tests.append(("Urine dipstick", f"pH {ph:.1f}", f"{acid} | calcium {ca}", c,
                  "Calcium or acidity is off. Drink more water and review calcium and vitamin D intake (kidney stone risk)."))

    sn = cur["sex_notes"]
    flag = any(k in sn for k in ("UTI", "discomfort", "Weak", "Painful"))
    tests.append(("Cycle and breast health" if p["sex"] == "Female" else "Urinary and groin health",
                  "Needs attention" if flag else "No concerns", sn, "yellow" if flag else "green",
                  "Tell the medical team about these symptoms."))

    # ---- last 7 daily check-ins
    last = ents[-7:]
    n0 = len(ents) - len(last) + 1
    dd = pd.DataFrame([{"Check-in": n0 + i, "Heart rate": e.get("heart_rate", 70.0), "Sleep": e.get("sleep_hours", 7.5),
                        "Stress": e.get("stress", 2), "Anxiety": e.get("anxiety", 2),
                        "Radiation": e.get("radiation_msv", 0.7), "Fluid": e.get("fluid_l", 2.0),
                        "Mood": e.get("mood", "Nothing")} for i, e in enumerate(last)])
    lvl = lambda v: "green" if v <= 2.5 else "yellow" if v <= 3.5 else "red"
    v = dd["Heart rate"].mean()
    daily.append(("Heart rate (average)", f"{v:.0f} bpm", "normal: 50-100 bpm", band(v, (50, 100), (40, 110)),
                  "Rest and recheck. Contact a doctor if it stays out of range."))
    v = dd["Sleep"].mean()
    daily.append(("Sleep (average)", f"{v:.1f} h", "normal: 7-9 hours", band(v, (7, 9), (6, 10)),
                  "Fix your sleep schedule and keep the sleep area dark and quiet."))
    v = dd["Stress"].mean()
    daily.append(("Stress (average)", f"{v:.1f} / 5", "lower is better", lvl(v),
                  "Make time for relaxation, hobbies and a call with family or the crew psychologist."))
    v = dd["Anxiety"].mean()
    daily.append(("Anxiety (average)", f"{v:.1f} / 5", "lower is better", lvl(v),
                  "Try breathing exercises and talk to the crew psychologist."))
    top = dd["Mood"].mode()[0]
    low = dd["Mood"].isin(["Sad", "Angry"]).sum()
    share = low / len(dd)
    daily.append(("Mood (most common)", top, f"{low} of {len(dd)} check-ins sad or angry",
                  "red" if share >= 0.5 else "yellow" if share >= 0.25 else "green",
                  "Your mood has been low. Talk to someone you trust or the crew psychologist."))
    v = dd["Fluid"].mean()
    daily.append(("Fluid intake (average)", f"{v:.1f} L", "normal: 2-3.5 L per day", band(v, (2.0, 3.5), (1.5, 4.5)),
                  "Drink more fluids through the day."))
    v = dd["Radiation"].mean()
    daily.append(("Radiation (average)", f"{v:.2f} mSv", f"total {dd['Radiation'].sum():.1f} mSv | normal under 1 mSv/day",
                  band(v, (0, 1.0), (0, 1.5)), "Limit time in high-radiation areas and follow the crew protocol."))

    allitems = tests + daily
    score = round(sum(SCORE_PTS[i[3]] for i in allitems) / len(allitems))
    overall = "green" if score >= 85 else "yellow" if score >= 60 else "red"
    if overall == "green" and any(i[3] == "red" for i in allitems):
        overall = "yellow"
    verdict = {"green": "You are doing well", "yellow": "A few things to watch",
               "red": "Needs attention - talk to the flight surgeon"}[overall]
    oc = COL[overall]
    vs = (f" | vs last week: weight {cur['weight_kg'] - prev['weight_kg']:+.1f} kg, "
          f"grip {cur['grip_kg'] - prev['grip_kg']:+.1f} kg") if prev else ""

    # ---- hero
    st.markdown("---")
    st.subheader(f"Weekly report - week {wk_no}")
    st.markdown(
        f"<div class='rhero' style='border-color:{oc}'>"
        f"<div class='ring' style='background:conic-gradient({oc} {score * 3.6:.0f}deg, #1b1b3a 0)'>"
        f"<span style='color:{oc}'>{score}</span></div>"
        f"<div><div class='rt'>Weekly health score (out of 100)</div>"
        f"<div class='rs' style='color:{oc}'>{verdict}</div>"
        f"<div class='rr'>Mission day {cur['mission_day']} | {cur['ts'].strftime('%d %b %Y')}{vs}</div></div></div>",
        unsafe_allow_html=True)

    # ---- cards
    for heading, group in (("This week's tests", tests), ("Your last 7 daily check-ins", daily)):
        st.markdown(f"**{heading}**")
        for i in range(0, len(group), 4):
            cols = st.columns(4)
            for col, (t, val, note, colr, _tip) in zip(cols, group[i:i + 4]):
                col.markdown(_rcard(t, val, note, colr), unsafe_allow_html=True)

    # ---- plain words
    st.markdown("**In plain words**")
    bad = sorted([i for i in allitems if i[3] != "green"], key=lambda i: RANK[i[3]])
    for t, val, _n, colr, tip in bad:
        st.markdown(f"{tint('<b>' + t + '</b>', colr)} is {tint(val, colr)}. {tip}", unsafe_allow_html=True)
    good = [i[0] for i in allitems if i[3] == "green"]
    if good:
        banner(f"<b>Normal this week:</b> {', '.join(good)}.", "green")
    if not bad:
        st.markdown(f"{tint('Everything looks normal. Keep your routine.', 'green')}", unsafe_allow_html=True)

    # ---- EDA charts
    st.markdown("**Charts**")
    t1, t2, t3 = st.tabs(["Stand test", "Weekly trends", "Daily life"])

    with t1:
        def stand_df(r, label):
            return pd.DataFrame({"Minute": [0, 3, 7, 15], "Week": label,
                                 "Heart rate": [r.get(f"hr_{t}min", r["hr_3min"]) for t in (0, 3, 7, 15)],
                                 "Systolic BP": [r.get(f"sys_{t}min", r["sys_3min"]) for t in (0, 3, 7, 15)],
                                 "Diastolic BP": [r.get(f"dia_{t}min", r["dia_3min"]) for t in (0, 3, 7, 15)]})
        sd = pd.concat([stand_df(cur, "This week")] + ([stand_df(prev, "Last week")] if prev else []))
        cols = st.columns(3)
        for col, (field, yt) in zip(cols, (("Heart rate", "Heart rate (bpm)"), ("Systolic BP", "Systolic BP (mmHg)"),
                                           ("Diastolic BP", "Diastolic BP (mmHg)"))):
            ch = alt.Chart(sd).mark_line(point=alt.OverlayMarkDef(filled=True, size=80), strokeWidth=3).encode(
                x=alt.X("Minute:O", title="Minutes standing"),
                y=alt.Y(f"{field}:Q", title=yt, scale=alt.Scale(zero=False)),
                color=alt.Color("Week:N", scale=alt.Scale(domain=["This week", "Last week"], range=[CYAN, PINK]),
                                legend=alt.Legend(title=None, orient="bottom")),
                tooltip=["Minute", "Week", field])
            with col:
                _show(_style(ch, field))
        st.caption("A healthy body keeps these lines flat. A big rise in heart rate or a drop in blood pressure "
                   "while standing means the body is struggling with gravity.")

    wk = pd.DataFrame([{"Week": i + 1, "Weight": r["weight_kg"], "Grip": r["grip_kg"], "Urine": r["urine_ml"],
                        "pH": r["ph"], "HR rise": _orth(r)[0], "BP drop": _orth(r)[1]} for i, r in enumerate(rows)])
    with t2:
        a, b = st.columns(2)
        with a:
            _show(_line(wk, "Week", "Weight", "Weight (dashed line = before flight)", "kg", "Weekly test #", CYAN, ref=usual))
        with b:
            _show(_line(wk, "Week", "Grip", "Grip strength", "kg", "Weekly test #", PINK))
        a, b = st.columns(2)
        with a:
            uc = wk.assign(color=wk["Urine"].map(lambda x: COL[band(x, (1000, 2500), (500, 3000))]))
            _show(_bars(uc, "Week", "Urine", "Urine volume", "mL", "Weekly test #"))
        with b:
            _show(_line(wk, "Week", "pH", "Urine pH (dashed line = 7.5 upper limit)", "pH", "Weekly test #", CYAN, ref=7.5))
        if len(wk) > 1:
            st.markdown("**Summary of all weekly tests**")
            st.dataframe(wk.drop(columns="Week").describe().loc[["mean", "min", "max"]].round(1),
                         use_container_width=True)
        else:
            st.info("Charts become trend lines after your second weekly test.")

    with t3:
        if len(dd) < 2:
            st.info("You have 1 daily check-in so far. Add more in Daily check-in to see trends.")
        a, b = st.columns(2)
        with a:
            sa = dd.melt(id_vars="Check-in", value_vars=["Stress", "Anxiety"], var_name="Measure", value_name="Score")
            ch = alt.Chart(sa).mark_line(point=alt.OverlayMarkDef(filled=True, size=80), strokeWidth=3).encode(
                x=alt.X("Check-in:O", title="Check-in #"),
                y=alt.Y("Score:Q", title="Score (1-5)", scale=alt.Scale(domain=[1, 5])),
                color=alt.Color("Measure:N", scale=alt.Scale(domain=["Stress", "Anxiety"], range=[PINK, CYAN]),
                                legend=alt.Legend(title=None, orient="bottom")),
                tooltip=["Check-in", "Measure", "Score"])
            _show(_style(ch, "Stress and anxiety"))
        with b:
            sl = dd.assign(color=dd["Sleep"].map(lambda x: COL[band(x, (7, 9), (6, 10))]))
            _show(_bars(sl, "Check-in", "Sleep", "Sleep (green = 7-9 h)", "hours", "Check-in #"))
        a, b = st.columns(2)
        with a:
            _show(_line(dd, "Check-in", "Heart rate", "Heart rate", "bpm", "Check-in #", CYAN))
        with b:
            rd = dd.assign(color=dd["Radiation"].map(lambda x: COL[band(x, (0, 1.0), (0, 1.5))]))
            _show(_bars(rd, "Check-in", "Radiation", "Radiation dose", "mSv", "Check-in #"))
        a, b = st.columns(2)
        with a:
            mc = dd.groupby("Mood").size().reset_index(name="Days")
            mc["color"] = mc["Mood"].map(MOOD_COL)
            ch = alt.Chart(mc).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
                x=alt.X("Days:Q", title="Check-ins", axis=alt.Axis(tickMinStep=1)), y=alt.Y("Mood:N", title=None),
                color=alt.Color("color:N", scale=None, legend=None), tooltip=["Mood", "Days"])
            _show(_style(ch, "Mood"))
        with b:
            fl = dd.assign(color=dd["Fluid"].map(lambda x: COL[band(x, (2.0, 3.5), (1.5, 4.5))]))
            _show(_bars(fl, "Check-in", "Fluid", "Fluid intake (green = 2-3.5 L)", "litres", "Check-in #"))

    with st.expander("All weekly test records (raw data)"):
        st.dataframe(pd.DataFrame(ss.weekly), use_container_width=True)


# =====================================================================
# SCREEN 1: WELCOME  ->  SCREEN 2: ABOUT YOU  ->  the app
# =====================================================================
if ss.stage == "welcome":
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("<div class='hero'><div class='big'></div><h1>Astronaut Health Monitor</h1>"
                    "<p>Enter your own numbers and see how your bone, heart, sleep, immune system, "
                    "weight, food and muscle are doing.</p></div>", unsafe_allow_html=True)
        st.write("")
        _, b, _ = st.columns([1, 1, 1])
        with b:
            if st.button("Start"):
                ss.stage = "onboard"
                st.rerun()
        st.caption("Prototype with simple rules - not a medical device")
    st.stop()

if ss.stage == "onboard":
    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        st.markdown("<div style='height:3vh'></div>", unsafe_allow_html=True)
        st.title("Tell us about you")
        with st.form("about_you"):
            st.subheader("About you")
            a1, a2 = st.columns(2)
            name = a1.text_input("Astronaut ID")
            sex = a2.selectbox("Sex", ["Male", "Female"])
            st.subheader("Today")
            t1, t2, t3 = st.columns(3)
            age = t1.number_input("Age today", 18, 90, 35)
            height = t2.number_input("Height today (cm)", 120.0, 220.0, 170.0)
            wtoday = t3.number_input("Weight today (kg)", 30.0, 200.0, 70.0, step=0.5)
            st.subheader("Before flight")
            f1, f2, f3 = st.columns(3)
            age0 = f1.number_input("Age before flight", 18, 90, 35)
            height0 = f2.number_input("Height before flight (cm)", 120.0, 220.0, 170.0)
            usual = f3.number_input("Weight before flight (kg)", 30.0, 200.0, 70.0, step=0.5)
            m1, m2 = st.columns(2)
            mdays = m1.number_input("Mission length (days)", 1, 2000, 180)
            bmd0 = m2.number_input("Bone density before flight (g/cm2, optional)", 0.0, 2.0, 1.0, step=0.01)
            go = st.form_submit_button("Continue ")
        if go:
            if not name.strip():
                st.error("Please enter your Astronaut ID.")
            else:
                ss.profile = {"name": name.strip(), "sex": sex, "age": int(age),
                              "height_cm": float(height), "weight_usual_kg": float(usual),
                              "weight_today": float(wtoday), "age0": int(age0), "height0": float(height0),
                              "bmd0": float(bmd0), "mission_days": int(mdays)}
                entry = dict(DEFAULT_ENTRY)
                entry["weight_kg"] = float(wtoday)
                ss.entries = [entry]
                ss.stage = "app"
                st.rerun()
    st.stop()

# =====================================================================
# THE APP
# =====================================================================
profile = ss.profile
entries = ss.entries
latest = entries[-1]
status = evaluate(profile, latest)
w = status["Weight"]
bmi = latest["weight_kg"] / ((profile["height_cm"] / 100) ** 2)
kg_change = latest["weight_kg"] - profile["weight_usual_kg"]
wpct = abs(kg_change) / profile["weight_usual_kg"] * 100
wlabel = f"{abs(kg_change):.1f} kg {'lost' if kg_change < 0 else 'gained'}"

st.sidebar.markdown(f"### {tint(profile['name'], CYAN)}", unsafe_allow_html=True)
st.sidebar.caption(f"{profile['sex']} | {profile['age']} yrs | {profile['height_cm']:.0f} cm | "
                   f"usual {profile['weight_usual_kg']:.0f} kg")
st.sidebar.markdown(f"Check-ins logged: {tint(str(len(entries)), CYAN)}", unsafe_allow_html=True)
mission_days = int(profile.get("mission_days", 180))
st.sidebar.markdown("**Demo controls**")
day = st.sidebar.number_input("Mission day (demo)", 0, 2000, 1)
skip_timer = st.sidebar.checkbox("Skip 7-day timer (demo)")
remaining = mission_days - day
landed = remaining <= 0
st.sidebar.caption(f"Mission length {mission_days} days | days left: {remaining}")
page = st.sidebar.radio("Page", ["Dashboard", "Daily check-in", "Weekly tests", "Return to Earth", "Exercise",
                                 "Muscle & Food plan", "Trends", "Alert detail",
                                 "Final dashboard & Summary"])
if st.sidebar.button("Start over"):
    ss.stage = "welcome"
    ss.profile = None
    ss.entries = []
    ss.weekly, ss.landing, ss.exercise = [], [], []
    st.rerun()

st.title("Astronaut Health Monitor")
st.caption("Prototype with simple rules - not a medical device")

# =============== DASHBOARD ===============
if page == "Dashboard":
    st.subheader(f"Body system status - {profile['name']}")
    wc = w["color"]
    banner(f"<b>Weight:</b> {tint(wlabel, wc)} ({tint(f'{wpct:.1f}%', wc)}) compared with your usual "
           f"{profile['weight_usual_kg']:.1f} kg &nbsp;|&nbsp; now {latest['weight_kg']:.1f} kg "
           f"&nbsp;|&nbsp; BMI {bmi:.1f}", wc)

    items = list(status.items())
    for i in range(0, len(items), 4):
        cols = st.columns(4)
        for col, (system, info) in zip(cols, items[i:i + 4]):
            with col:
                card(system, info)

    st.subheader("Top 3 actions today")
    ranked = sorted(status.items(), key=lambda x: RANK[x[1]["color"]])
    for system, info in ranked[:3]:
        st.markdown(f"{info['icon']} {tint('<b>' + system + '</b>', info['color'])}: "
                    f"{tint(info['action'], info['color'])}", unsafe_allow_html=True)
    st.caption("Each color comes from the numbers you entered, compared with a normal range. "
               "Change your numbers in Daily check-in and watch the colors change.")

# =============== CHECK-IN ===============
elif page == "Daily check-in":
    st.subheader("Daily check-in")
    st.caption("Your numbers are pre-filled from your last check-in. Change what is different today.")
    with st.form("checkin"):
        new_entry = entry_fields(latest, with_weight=False)
        new_entry.update(extra_fields(latest))
        submitted = st.form_submit_button("Submit check-in")
    if submitted:
        ss.entries.append(new_entry)
        st.success(f"Saved! You have {len(ss.entries)} check-ins. Open the Dashboard to see the updated status.")

# =============== WEEKLY TESTS ===============
elif page == "Weekly tests":
    st.subheader("Weekly tests")
    if landed:
        banner("Mission is over - weekly tests are skipped. Use the Return to Earth page.", "yellow")
        st.stop()
    if ss.weekly and not skip_timer:
        left = ss.weekly[-1]["ts"] + timedelta(days=7) - datetime.now()
        if left.total_seconds() > 0:
            banner(f"<b>Locked.</b> Next weekly test opens in {left.days}d {left.seconds // 3600}h "
                   f"{(left.seconds % 3600) // 60}m {left.seconds % 60}s", "yellow")
            show_weekly_report()
            st.stop()
    c1, c2, c3 = st.columns(3)
    wk_w = c1.number_input("Weight (kg)", 30.0, 200.0, float(latest["weight_kg"]), step=0.5)
    wk_h = c2.number_input("Height (cm)", 120.0, 220.0, float(profile["height_cm"]))
    grip = c3.number_input("Grip strength (kg)", 0.0, 100.0, 35.0)
    v1, v2 = st.columns(2)
    blur = v1.checkbox("Blurry vision")
    head = v2.checkbox("Headache")
    st.markdown("**Stand test - heart rate and blood pressure while standing**")
    stand = {}
    for t in (0, 3, 7, 15):
        when = "standing (0 min)" if t == 0 else f"{t} min"
        a, b, c = st.columns(3)
        stand[t] = (a.number_input(f"Heart rate at {when}", 30.0, 220.0, 70.0),
                    b.number_input(f"Systolic at {when}", 70.0, 220.0, 115.0),
                    c.number_input(f"Diastolic at {when}", 40.0, 140.0, 78.0))
    st.markdown("**Urine dipstick**")
    st.caption("A dipstick is a small paper strip dipped in urine. Its coloured pads change colour "
               "and show pH (acidity) and other results.")
    u1, u2, u3 = st.columns(3)
    uv = u1.number_input("Urine volume (mL)", 0.0, 5000.0, 1500.0)
    ph = u2.slider("pH (acidity)", 5.0, 9.0, 6.0, 0.5)
    ca = u3.selectbox("Calcium result", ["Normal", "Low", "High", "Not tested"])
    acid = "Acidic" if ph < 6.0 else "Normal" if ph <= 7.5 else "Alkaline"
    banner(f"<b>Acidity result:</b> {tint(acid, 'green' if acid == 'Normal' else 'yellow')} (pH {ph})",
           "green" if acid == "Normal" else "yellow")
    if profile["sex"] == "Female":
        sup = st.radio("On cycle suppression medication?", ["Yes", "No"], horizontal=True)
        note = "on cycle suppression"
        if sup == "No":
            cd = st.number_input("Days of cycle (cycle day)", 1, 45, 1)
            fl = st.selectbox("Flow", ["None", "Light", "Medium", "Heavy"])
            note = f"cycle day {cd}, flow {fl}"
        if st.checkbox("Breast discomfort"):
            note += "; breast discomfort"
        if st.checkbox("UTI symptoms (burning, urgency)"):
            note += "; UTI symptoms"
    else:
        uf = st.selectbox("Urinary flow", ["Normal", "Weak", "Painful"])
        note = "urinary flow: " + uf
        if st.checkbox("Groin discomfort"):
            note += "; groin discomfort"
    if st.button("Submit weekly test"):
        row = {"ts": datetime.now(), "mission_day": day, "weight_kg": wk_w, "height_cm": wk_h,
               "grip_kg": grip, "blurry_vision": blur, "headache": head, "urine_ml": uv,
               "ph": ph, "acidity_result": acid, "calcium_result": ca, "sex_notes": note}
        for t, (a, b, c) in stand.items():
            row.update({f"hr_{t}min": a, f"sys_{t}min": b, f"dia_{t}min": c})
        ss.weekly.append(row)
        ss.entries[-1]["weight_kg"] = float(wk_w)
        ss.profile["height_cm"] = float(wk_h)
        st.success("Saved. The next weekly test opens in 7 days.")
    if ss.weekly:
        show_weekly_report()

# =============== RETURN TO EARTH ===============
elif page == "Return to Earth":
    st.subheader("Return to Earth - landing recovery (first 7 days)")
    if not landed:
        banner(f"This page opens when mission days left = 0 (now {remaining} days left).", "yellow")
        st.stop()
    ds = st.slider("Days since landing", 0, 7, 0)
    c1, c2, c3 = st.columns(3)
    hr3 = c1.number_input("Stand test - heart rate at 3 min", 30.0, 220.0, 80.0)
    sy3 = c2.number_input("Stand test - systolic BP at 3 min", 60.0, 220.0, 110.0)
    bal = c3.number_input("Balance test (seconds, eyes closed)", 0.0, 60.0, 20.0)
    c1, c2, c3 = st.columns(3)
    falls = c1.number_input("Falls today", 0, 20, 0)
    near = c2.number_input("Near falls today", 0, 20, 0)
    diz = c3.slider("Dizziness (0-5)", 0, 5, 0)
    vis = st.checkbox("Blurry vision or headache")
    c1, c2, c3 = st.columns(3)
    hyd = c1.number_input("Fluid intake (L)", 0.0, 10.0, 2.5)
    grip = c2.number_input("Grip strength (kg)", 0.0, 100.0, 30.0)
    wt = c3.number_input("Weight (kg)", 30.0, 200.0, float(latest["weight_kg"]), step=0.5)
    c1, c2 = st.columns(2)
    uv = c1.number_input("Urine volume (mL)", 0.0, 5000.0, 1500.0)
    sl = c2.number_input("Sleep (hours)", 0.0, 14.0, 7.0, step=0.5)
    bmd = None
    bmd_done = any(r.get("bone_density_after") is not None for r in ss.landing)
    if bmd_done:
        st.caption("Bone density after the mission is already recorded (it is measured only once).")
    elif st.checkbox("Bone density scan done today (once, after the mission)"):
        bmd = st.number_input("Bone density after mission (g/cm2)", 0.0, 2.0, 1.0, step=0.01)
        b0 = profile.get("bmd0")
        if b0:
            chg = (bmd - b0) / b0 * 100
            banner(f"Bone density change vs before flight: {tint(f'{chg:.1f}%', 'green' if chg > -2 else 'yellow' if chg > -5 else 'red')}", "green" if chg > -2 else "yellow" if chg > -5 else "red")
    if st.button("Save landing log"):
        ss.landing.append({"days_since_landing": ds, "hr_stand_3min": hr3, "sys_stand_3min": sy3,
                           "balance_s": bal, "falls": falls, "near_falls": near, "dizziness": diz,
                           "vision_issue": vis, "fluid_l": hyd, "grip_kg": grip, "weight_kg": wt,
                           "urine_ml": uv, "sleep_hours": sl, "bone_density_after": bmd})
        st.success("Saved.")
    if ss.landing:
        st.dataframe(pd.DataFrame(ss.landing), use_container_width=True)

# =============== EXERCISE ===============
elif page == "Exercise":
    st.subheader("Exercise")
    if day <= 0 or landed:
        banner("Exercise is active while the mission is in progress (mission day above 0).", "yellow")
        st.stop()
    st.caption("ISS crews typically use a treadmill, a resistance device (ARED) and a cycle ergometer, "
               "about 2 hours a day. Check current NASA guidance for exact prescriptions.")
    c1, c2, c3 = st.columns(3)
    tm = c1.number_input("Treadmill (min)", 0.0, 180.0, 30.0)
    rs = c2.number_input("Resistance - ARED (min)", 0.0, 180.0, 45.0)
    cy = c3.number_input("Cycle ergometer (min)", 0.0, 180.0, 30.0)
    total = tm + rs + cy
    col = "green" if total >= 100 else "yellow" if total >= 60 else "red"
    banner(f"<b>Total today:</b> {tint(f'{total:.0f} min', col)} &nbsp;|&nbsp; target about 120 min", col)
    if st.button("Log exercise"):
        ss.exercise.append({"mission_day": day, "treadmill_min": tm, "ared_min": rs, "cycle_min": cy})
        st.success("Logged.")
    if ss.exercise:
        st.dataframe(pd.DataFrame(ss.exercise), use_container_width=True)

# =============== MUSCLE & FOOD PLAN ===============
elif page == "Muscle & Food plan":
    st.subheader("Muscle working & food plan")
    tg = targets(profile, latest["weight_kg"])

    def ratio_color(actual, target):
        r = actual / target
        return "green" if r >= 0.9 else "yellow" if r >= 0.7 else "red"

    rows = [("Food intake (kcal/day)", tg["kcal"], latest["calories"]),
            ("Protein (g/day)", tg["protein"], latest["protein_g"]),
            ("Calcium (mg/day)", tg["calcium"], latest["calcium_mg"]),
            ("Strength exercise (min/week)", STRENGTH_TARGET, latest["strength_min_week"]),
            ("Treadmill / impact exercise (min/week)", WEIGHT_BEARING_TARGET, latest["weight_bearing_min_week"])]
    for label, target, actual in rows:
        col = ratio_color(actual, target)
        banner(f"<b>{label}</b> &nbsp; target {tint(f'{target:.0f}', CYAN)} &nbsp;|&nbsp; "
               f"you {tint(f'{actual:.0f}', col)} ({tint(f'{actual / target * 100:.0f}% of target', col)})", col)

    st.caption(f"Exercise targets follow an ISS-style routine: about 60 min strength + 30 min treadmill/impact "
               f"a day, 6 days a week ({STRENGTH_TARGET} and {WEIGHT_BEARING_TARGET} min per week). "
               "Real astronauts spend about 2 to 2.5 hours a day including cardio and equipment setup.")

    st.subheader("Exercises to preserve muscle (ISS equipment)")
    plan = pd.DataFrame([
        ["Squats", "Legs, hips, spine", "ARED", "Vacuum cylinders pull against the bar like free weights", "3 x 8-10"],
        ["Deadlift", "Back, glutes, hamstrings", "ARED", "Same resistance bar, you pull against the cylinders", "3 x 6-8"],
        ["Heel raises", "Calves", "ARED", "Bar loaded by the cylinders, no gravity needed", "3 x 15"],
        ["Presses", "Chest, shoulders, arms", "ARED", "Push the bar against cylinder resistance", "3 x 8-10"],
        ["Rows", "Upper back, biceps", "ARED", "Pull against cylinder resistance", "3 x 10"],
        ["Running", "Heart, legs, bone loading", "T2 treadmill (COLBERT)",
         "Harness and bungees pull you down onto the belt", "30 min"],
        ["Cycling", "Heart, endurance", "CEVIS bike",
         "Vibration-isolated bike, straps keep you in place", "30 min"],
    ], columns=["Exercise", "Muscle worked", "ISS equipment", "How it works in space", "Sets x reps / time"])
    st.table(plan)
    st.caption("ARED = Advanced Resistive Exercise Device. On the ISS, astronauts exercise about "
               "2 to 2.5 hours a day, 6 days a week. Sets and reps here are example values, not NASA's protocol.")

    st.subheader("Food tips")
    tips = [f"Protein: about {PROTEIN_PER_KG} g per kg body weight, spread across all meals",
            f"Calories: about {tg['kcal']:.0f} kcal/day for your size and activity",
            f"Calcium: about {tg['calcium']} mg/day plus vitamin D for bone support"]
    if profile["sex"] == "Female":
        tips.append("Keep an eye on iron intake too")
    for t in tips:
        st.markdown(f"{tint(t, CYAN)}", unsafe_allow_html=True)
    st.caption("Rough prototype formulas (Mifflin-St Jeor x 1.5) - not medical advice.")

# =============== TRENDS ===============
elif page == "Trends":
    st.subheader("Trends")
    names = {"Weight (kg)": "weight_kg", "Resting heart rate": "heart_rate", "Temperature": "temperature",
             "Sleep hours": "sleep_hours", "Calories": "calories", "Protein (g)": "protein_g",
             "Calcium (mg)": "calcium_mg", "Strength min/week": "strength_min_week",
             "Treadmill/impact min/week": "weight_bearing_min_week"}
    pick = st.selectbox("Measurement", list(names.keys()))
    hist = pd.DataFrame(entries)
    hist.index = range(1, len(hist) + 1)
    hist.index.name = "check-in #"
    if len(hist) < 2:
        st.info("You have 1 check-in so far. Add more in Daily check-in to see a trend line.")
    else:
        st.line_chart(hist[[names[pick]]], color=[CYAN])
    st.caption("One point per check-in. The first point is what you entered at the start.")

# =============== ALERT DETAIL ===============
elif page == "Alert detail":
    st.subheader("Alert detail")
    system = st.selectbox("Body system", list(status.keys()))
    info = status[system]
    msg = {"red": "get help", "yellow": "watch closely", "green": "normal"}[info["color"]]
    banner(f"{STATUS_ICON[info['color']]} <b>{info['icon']} {system}:</b> {tint(msg, info['color'])}", info["color"])
    c1, c2 = st.columns(2)
    c1.metric("Your value", info["value"])
    c2.metric("Normal", info["normal"])
    st.markdown(f"**Why:** {tint(info['reason'], info['color'])}", unsafe_allow_html=True)
    st.markdown(f"**What to do:** {tint(info['action'], info['color'])}", unsafe_allow_html=True)

# =============== FINAL DASHBOARD & SUMMARY ===============
else:
    st.subheader("Final dashboard - first entry vs now")
    rows = []
    for name, meta in SYSTEMS.items():
        m = meta["metric"]
        first_v, last_v = entries[0][m], latest[m]
        pct = (last_v - first_v) / first_v * 100 if first_v else 0.0
        rows.append({"System": f"{meta['icon']} {name}", "Change %": round(pct, 1),
                     "color": COL[status[name]["color"]], "Your value": status[name]["value"],
                     "Normal": status[name]["normal"], "Status": STATUS_ICON[status[name]["color"]]})
    diff = pd.DataFrame(rows)
    if len(entries) < 2:
        st.info("Only 1 check-in so far, so changes show as 0%. Add another check-in to see the difference.")
    bars = alt.Chart(diff).mark_bar(cornerRadius=4).encode(
        x=alt.X("Change %:Q", title="Change since your first entry (%)"),
        y=alt.Y("System:N", sort=None, title=None),
        color=alt.Color("color:N", scale=None),
        tooltip=["System", "Your value", "Normal", "Change %"])
    labels = alt.Chart(diff).mark_text(align="left", dx=4, color=WHITE).encode(
        x="Change %:Q", y=alt.Y("System:N", sort=None), text="Change %:Q")
    chart = (bars + labels).properties(height=360, background="#000000").configure_axis(
        labelColor=WHITE, titleColor=CYAN, gridColor="#222", domainColor="#444").configure_view(stroke=None)
    st.altair_chart(chart, width="stretch")
    st.dataframe(diff[["Status", "System", "Your value", "Normal", "Change %"]], hide_index=True)

    st.subheader(f"Summary for {profile['name']}")
    reds = [n for n, i in status.items() if i["color"] == "red"]
    yellows = [n for n, i in status.items() if i["color"] == "yellow"]
    overall = "red" if reds else "yellow" if yellows else "green"
    n_green = len(status) - len(reds) - len(yellows)
    banner(f"{STATUS_ICON[overall]} <b>Overall:</b> {tint(str(len(reds)) + ' red', 'red')}, "
           f"{tint(str(len(yellows)) + ' yellow', 'yellow')}, {tint(str(n_green) + ' green', 'green')} "
           f"out of {len(status)} systems", overall)

    wc = w["color"]
    st.markdown(f"**Weight:** {tint(f'{wlabel} ({wpct:.1f}%)', wc)} compared with your usual "
                f"{profile['weight_usual_kg']:.1f} kg (now {latest['weight_kg']:.1f} kg), BMI {bmi:.1f}",
                unsafe_allow_html=True)

    if kg_change < 0 and wc != "green" and (status["Muscle"]["color"] != "green" or status["Nutrition"]["color"] != "green"):
        banner("<b>Muscle loss risk:</b> you are losing weight while strength exercise or food intake is "
               "below target. Increase protein and strength work.", "red")
    elif kg_change < 0 and wc != "green":
        banner("Weight is down but exercise and food look on target - recheck over the next days.", "yellow")

    for system, info in sorted(status.items(), key=lambda x: RANK[x[1]["color"]]):
        st.markdown(f"{info['icon']} {STATUS_ICON[info['color']]} "
                    f"{tint('<b>' + system + '</b>', info['color'])} - {info['reason']}. "
                    f"{tint('Action: ' + info['action'], info['color'])}", unsafe_allow_html=True)
    st.caption("This is a prototype using simple reference ranges - not medical advice.")
