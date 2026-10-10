# Althea 
NASA Space App challenge (app for astronaut health monitoring in space )

#team Error 403

**Disclaimer**
(This is a research and hackathon prototype. It is decision-support software, not a medical device, and it does not provide medical diagnosis or treatment. It uses simulated data. Thresholds, exercise advice, and predictions must be reviewed by qualified clinicians and validated before any real use.)

Long-duration missions expose astronauts to space radiation, isolation and confinement, altered gravity, and a hostile closed environment. These can bring immune changes, bone loss, cardiovascular events, and behavioral health problems. On long missions, far from doctors and with long communication delays, astronauts carry much of the responsibility for spotting these changes in themselves. So the Challenge was to build a health monitoring software that gathers health indicators and enables astronauts to evaluate and act on the status of their health.


Our Solution


A single app that an astronaut will be used by themselves. It collects health indicators, compares each with the astronaut's own pre-flight baseline, turns them into a plain-language health status, warns before problems are likely to happen, and recommends what to do next, including a personalized exercise plan.
The app will work in three phases:
Daily	Short check-in: for vitals, sleep, mood, symptoms, intake, urine volume, exercise, and radiation dose
Weekly	Periodic tests: such as grip strength, vision, weight, a stand (orthostatic) test, and longer questionnaires
Return to Earth:	Pre-landing preparation, landing-day and first-week tests, and a recovery plan


Domains tracked: bone, muscle, kidney and urine, cardiovascular, behavioral, immune, eyes, radiation.
Sex-specific logic: different thresholds, symptom prompts, and advice for men and women, plus cycle tracking for women.
Status and advice: green/yellow/red per body system, with an explanation and a recommended action.
Cross-domain links: for example, bone loss raises kidney-stone risk, and poor sleep affects immune and heart scores.
Exercise planner: a weekly plan based on current weak points, adapting to missed sessions.
Failure prediction: trend forecasts and risk estimates with confidence ranges, including landing-day fainting risk.
Return-to-Earth mode: fluid-loading checklist, stand test, balance and gait checks, graded recovery.


Reference Figures Used

Career radiation limit of 600 mSv, universal for all ages and sexes(Radiation tracker	NASA-STD-3001 technical brief)
Background space radiation of about 0.5 mSv per day	Simulated daily dose	(NASA-STD-3001 materials)
Urine volume under 2 L/day as a stone risk factor	Kidney rules	(NASA renal stone risk slides)
Landing-day near-fainting in about 20% of short-duration and over 60% of long-duration flyers	Landing-risk feature and pitch(	NASA orthostatic intolerance report)
ISS exercise devices (ARED, T2 treadmill, CEVIS) and about 2 hours of exercise per day	Exercise planner(	NASA astronaut exercise page)


Future Work


Validate with real astronaut data and clinician review; integrate wearables and dosimeters; add more behavioral and immune indicators; and implement encrypted storage with secure sync.


Prototype URL: https://altheaa.streamlit.app/



how to run :

1. Install Python from python.org (tick "Add Python to PATH" in the installer).
2. Unzip this folder.
3. Double-click run.bat
   (first time takes 1-2 minutes to install libraries)
4. Browser opens at http://localhost:8501

Manual way (Command Prompt inside this folder):
   pip install -r requirements.txt
   python -m streamlit run health_plain.py

Keep the black window open while using the app. Close it to stop.
