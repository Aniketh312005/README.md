import streamlit as st
import pandas as pd
import sys, os

sys.path.append(os.path.dirname(__file__))
from modules import diet, tracker, iot_sim, chatbot, ui

st.set_page_config(page_title="Ironlog — AI Gym Assistant", layout="wide")
ui.inject()

PAGES = ["Dashboard", "Diet Planner", "Behavior Tracker", "Workout Counter",
         "Smart Gym (IoT)", "Chat Assistant"]

st.sidebar.markdown("### IRONLOG")
st.sidebar.caption("AI gym & fitness assistant")
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")

# ---------------- Dashboard ----------------
if page == "Dashboard":
    st.title("Dashboard")

    st.markdown(ui.plate_grid([
        {"label": "Workout streak", "value": tracker.current_streak(), "unit": "days", "tone": "primary"},
        {"label": "Calories today", "value": f"{tracker.day_totals('meals', 'calories'):.0f}", "unit": "kcal"},
        {"label": "Water today", "value": f"{tracker.day_totals('water', 'ml'):.0f}", "unit": "ml"},
        {"label": "Last sleep log", "value": f"{tracker.day_totals('sleep', 'hours'):.1f}", "unit": "hrs"},
    ]), unsafe_allow_html=True)

    st.subheader("Last 7 days")
    summary = tracker.weekly_summary()
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Calories in vs. burned")
        st.line_chart(summary.set_index("date")[["calories_in", "calories_out"]])
    with c2:
        st.caption("Water intake (ml)")
        st.bar_chart(summary.set_index("date")[["water_ml"]])

    st.subheader("Recent workouts")
    w = tracker.get_df("workouts")
    if w.empty:
        st.markdown(ui.alert_bar("No workouts logged yet — head to Workout Counter to start a session."),
                    unsafe_allow_html=True)
    else:
        st.dataframe(w.tail(10), use_container_width=True, hide_index=True)

# ---------------- Diet Planner ----------------
elif page == "Diet Planner":
    st.title("Diet Planner")
    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Weight (kg)", 30.0, 200.0, 70.0)
        height = st.number_input("Height (cm)", 120.0, 220.0, 170.0)
        age = st.number_input("Age", 10, 90, 22)
        sex = st.selectbox("Sex", ["Male", "Female"])
    with col2:
        activity = st.selectbox("Activity level", list(diet.ACTIVITY_MULT.keys()), index=1)
        goal = st.selectbox("Goal", list(diet.GOAL_ADJUST.keys()))
        pref = st.selectbox("Diet preference", ["veg", "non-veg"])

    if st.button("Calculate plan", type="primary"):
        bmr = diet.calculate_bmr(weight, height, age, sex)
        tdee = diet.calculate_tdee(bmr, activity)
        target = diet.target_calories(tdee, goal)
        macros = diet.macro_split(target, goal)
        st.session_state.diet_plan = diet.generate_meal_plan(target, pref)
        st.session_state.diet_stats = (bmr, tdee, target, macros)

    if "diet_stats" in st.session_state:
        bmr, tdee, target, macros = st.session_state.diet_stats
        st.markdown(ui.plate_grid([
            {"label": "BMR", "value": f"{bmr:.0f}", "unit": "kcal"},
            {"label": "TDEE", "value": f"{tdee:.0f}", "unit": "kcal"},
            {"label": "Daily target", "value": f"{target:.0f}", "unit": "kcal", "tone": "primary"},
            {"label": "Protein", "value": macros["protein_g"], "unit": "g"},
            {"label": "Carbs", "value": macros["carbs_g"], "unit": "g"},
            {"label": "Fat", "value": macros["fat_g"], "unit": "g"},
        ]), unsafe_allow_html=True)

        plan = st.session_state.diet_plan
        st.subheader("Today's meal plan")
        st.markdown(ui.meal_row([
            {"slot": meal.title(), **plan[meal]} for meal in ["breakfast", "lunch", "dinner", "snack"]
        ]), unsafe_allow_html=True)
        st.caption(f"Plan total {plan['_total_calories']} kcal vs. target {plan['_target_calories']} kcal")

        if st.button("Log this plan to today's tracker"):
            for meal in ["breakfast", "lunch", "dinner", "snack"]:
                item = plan[meal]
                tracker.log_meal(item["item"], item["calories"], item["protein"],
                                  item["carbs"], item["fat"])
            st.success("Logged to tracker.")

# ---------------- Behavior Tracker ----------------
elif page == "Behavior Tracker":
    st.title("Behavior Tracker")
    tabs = st.tabs(["Log entry", "Meals", "Workouts", "Water / sleep / weight"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Meal**")
            name = st.text_input("Meal name")
            cal = st.number_input("Calories", 0, 3000, 400)
            p = st.number_input("Protein (g)", 0, 200, 20)
            cb = st.number_input("Carbs (g)", 0, 300, 40)
            f = st.number_input("Fat (g)", 0, 150, 10)
            if st.button("Add meal"):
                tracker.log_meal(name, cal, p, cb, f)
                st.success("Meal logged.")

            st.markdown("**Water**")
            ml = st.number_input("Water (ml)", 0, 5000, 250, key="water_ml")
            if st.button("Add water"):
                tracker.log_water(ml)
                st.success("Water logged.")

        with c2:
            st.markdown("**Workout**")
            ex = st.text_input("Exercise", "Squat")
            reps = st.number_input("Reps", 0, 500, 10)
            sets = st.number_input("Sets", 0, 20, 3)
            dur = st.number_input("Duration (min)", 0.0, 180.0, 15.0)
            calb = st.number_input("Calories burned", 0.0, 2000.0, 100.0)
            if st.button("Add workout"):
                tracker.log_workout(ex, reps, sets, dur, calb)
                st.success("Workout logged.")

            st.markdown("**Sleep / weight**")
            hrs = st.number_input("Sleep (hrs)", 0.0, 14.0, 7.0)
            if st.button("Add sleep"):
                tracker.log_sleep(hrs)
                st.success("Sleep logged.")
            kg = st.number_input("Weight (kg)", 30.0, 200.0, 70.0, key="w_log")
            if st.button("Add weight"):
                tracker.log_weight(kg)
                st.success("Weight logged.")

    with tabs[1]:
        st.dataframe(tracker.get_df("meals"), use_container_width=True, hide_index=True)
    with tabs[2]:
        st.dataframe(tracker.get_df("workouts"), use_container_width=True, hide_index=True)
    with tabs[3]:
        c1, c2, c3 = st.columns(3)
        c1.dataframe(tracker.get_df("water"), use_container_width=True, hide_index=True)
        c2.dataframe(tracker.get_df("sleep"), use_container_width=True, hide_index=True)
        c3.dataframe(tracker.get_df("weight"), use_container_width=True, hide_index=True)

# ---------------- Workout Counter ----------------
elif page == "Workout Counter":
    st.title("Workout Counter")
    st.caption("Tap to log reps as you go — no camera required.")
    from modules.workout_detect import RepCounter, estimate_calories

    exercise = st.selectbox("Exercise", ["Bicep Curl", "Squat", "Push-up", "Lunge", "Plank (sec)"])
    if "rep_counter" not in st.session_state or st.session_state.get("wd_exercise") != exercise:
        st.session_state.rep_counter = RepCounter(exercise)
        st.session_state.wd_exercise = exercise

    rc = st.session_state.rep_counter
    st.markdown(ui.counter_display(rc.count, f"{exercise} · set {rc.sets} · {rc.elapsed_min()} min elapsed"),
                unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    if b1.button("+ 1 rep", type="primary", use_container_width=True):
        rc.add_rep(1)
        st.rerun()
    if b2.button("+ 5 reps", use_container_width=True):
        rc.add_rep(5)
        st.rerun()
    b3, b4 = st.columns(2)
    if b3.button("Start new set", use_container_width=True):
        rc.new_set()
        st.rerun()
    if b4.button("Reset session", use_container_width=True):
        rc.reset()
        st.rerun()

    if st.button("Save session to tracker"):
        cals = estimate_calories(rc.exercise, rc.count)
        tracker.log_workout(rc.exercise, rc.count, rc.sets, rc.elapsed_min(), cals)
        st.success(f"Logged {rc.count} reps / {rc.sets} sets of {rc.exercise} (~{cals} kcal).")

# ---------------- IoT Smart Gym ----------------
elif page == "Smart Gym (IoT)":
    st.title("Smart Gym console")
    st.caption("Simulated device feed — swap modules/iot_sim.py for real MQTT/BLE readers.")

    intensity = st.slider("Current activity intensity", 0.0, 1.0, 0.5)
    hr = iot_sim.read_heart_rate(activity_intensity=intensity)
    scale = iot_sim.read_smart_scale()
    bottle = iot_sim.read_smart_bottle()
    tread = iot_sim.read_treadmill()

    for alert in iot_sim.safety_alerts(hr):
        st.markdown(ui.alert_bar(alert), unsafe_allow_html=True)

    st.markdown(ui.readout_strip([
        {"label": "Heart rate (bpm)", "value": hr},
        {"label": "Body fat %", "value": scale["body_fat_pct"]},
        {"label": "Water today (ml)", "value": bottle["ml_consumed_today"]},
        {"label": "Treadmill speed (km/h)", "value": tread["speed_kmh"]},
    ]), unsafe_allow_html=True)

    st.subheader("Device detail")
    st.markdown(ui.plate_grid([
        {"label": "Muscle mass", "value": scale["muscle_mass_kg"], "unit": "kg"},
        {"label": "Weight (scale)", "value": scale["weight_kg"], "unit": "kg"},
        {"label": "Treadmill incline", "value": tread["incline_pct"], "unit": "%"},
        {"label": "Treadmill distance", "value": tread["distance_km"], "unit": "km"},
    ]), unsafe_allow_html=True)

# ---------------- Chat Assistant ----------------
elif page == "Chat Assistant":
    st.title("Chat Assistant")
    st.caption("Ask about diet, workouts, motivation, or your logged progress.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for role, text in st.session_state.chat_history:
        st.chat_message(role).write(text)

    user_msg = st.chat_input("Ask something...")
    if user_msg:
        st.session_state.chat_history.append(("user", user_msg))
        summary = tracker.weekly_summary().tail(1).to_dict("records")
        summary_text = f"Today: {summary[0]}" if summary else None
        reply = chatbot.get_reply(user_msg, summary_text)
        st.session_state.chat_history.append(("assistant", reply))
        st.rerun()
