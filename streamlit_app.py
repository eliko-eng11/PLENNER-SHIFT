import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment

st.set_page_config(page_title="📅 שיבוץ עובדים", layout="wide")
st.markdown("<h1 style='text-align:center; color:#2C3E50;'>🛠️ מערכת שיבוץ חכמה לעובדים</h1>", unsafe_allow_html=True)

ordered_days = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
full_shifts = ['משמרת בוקר', 'משמרת אחה״צ', 'משמרת לילה']
basic_days = ordered_days[:5]

num_workers = st.number_input("כמה עובדים יש?", min_value=1, step=1)
work_friday = st.checkbox("עובדים ביום שישי?")
work_saturday = st.checkbox("עובדים ביום שבת?")
shifts_per_day_basic = st.selectbox("כמה משמרות ביום רגיל (א׳–ה׳)?", [1, 2, 3])
selected_shifts_basic = full_shifts[:shifts_per_day_basic]
selected_shifts_friday = full_shifts[:st.selectbox("כמה משמרות בשישי?", [0, 1, 2, 3]) if work_friday else 0]
selected_shifts_saturday = full_shifts[:st.selectbox("כמה משמרות בשבת?", [0, 1, 2, 3]) if work_saturday else 0]

active_days = basic_days + (['שישי'] if work_friday else []) + (['שבת'] if work_saturday else [])

st.subheader("👥 שמות העובדים")
workers = []
for i in range(num_workers):
    name = st.text_input(f"שם עובד {i+1}", key=f"worker_{i}")
    if name:
        workers.append(name)

st.subheader("📋 כמה עובדים דרושים בכל משמרת")
required_workers = {}
shift_slots = []
for d in active_days:
    shifts_today = selected_shifts_basic if d in basic_days else selected_shifts_friday if d == 'שישי' else selected_shifts_saturday
    for s in shifts_today:
        req = st.number_input(f"{d} - {s}", min_value=0, max_value=10, value=1, key=f"{d}_{s}")
        required_workers[(d, s)] = req
        for i in range(req):
            shift_slots.append((d, s, i))

st.subheader("⭐ העדפות עובדים (1=נמוך, 3=גבוה, שלילי=לא זמין)")
preferences = {}
for w in workers:
    for d in active_days:
        shifts_today = selected_shifts_basic if d in basic_days else selected_shifts_friday if d == 'שישי' else selected_shifts_saturday
        for s in shifts_today:
            preferences[(w, d, s)] = st.slider(f"{w} - {d} - {s}", -1, 3, 2, key=f"{w}_{d}_{s}")

if st.button("🚀 בצע שיבוץ"):
    if not workers or not shift_slots:
        st.warning("חסר קלט — אנא ודא שיש עובדים ומשמרות")
    else:
        worker_copies = [(w, d, s) for w in workers for d in active_days
                         for s in (selected_shifts_basic if d in basic_days else selected_shifts_friday if d == 'שישי' else selected_shifts_saturday)
                         if preferences[(w, d, s)] >= 0]

        cost_matrix = []
        for w, d, s in worker_copies:
            row = []
            for sd, ss, _ in shift_slots:
                row.append(4 - preferences[(w, d, s)] if (d, s) == (sd, ss) else 1e6)
            cost_matrix.append(row)

        cost_matrix = np.array(cost_matrix)
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        assignments = []
        used_workers_in_shift = set()
        used_slots = set()
        worker_shift_count = {w: 0 for w in workers}
        worker_daily_shifts = {w: {d: [] for d in active_days} for w in workers}
        max_shifts_per_worker = len(shift_slots) // len(workers) + 1

        for r, c in sorted(zip(row_ind, col_ind), key=lambda x: cost_matrix[x[0], x[1]]):
            worker, day, shift = worker_copies[r]
            slot = shift_slots[c]
            shift_key = (worker, slot[0], slot[1])
            current_shift_index = full_shifts.index(shift)

            # תנאי בדיקה
            if cost_matrix[r][c] >= 1e6 or shift_key in used_workers_in_shift or slot in used_slots:
                continue
            if worker_shift_count[worker] >= max_shifts_per_worker:
                continue
            if any(abs(full_shifts.index(s) - current_shift_index) == 1 for s in worker_daily_shifts[worker][day]):
                continue

            used_workers_in_shift.add(shift_key)
            used_slots.add(slot)
            assignments.append({'יום': slot[0], 'משמרת': slot[1], 'עובד': worker})
            worker_shift_count[worker] += 1
            worker_daily_shifts[worker][day].append(shift)

        # התראות על משמרות לא משובצות
        remaining_slots = [slot for slot in shift_slots if slot not in used_slots]
        if remaining_slots:
            for d, s, _ in remaining_slots:
                st.warning(f"⚠️ לא שובץ אף אחד ל־{d} - {s}")

        # תצוגה
        df = pd.DataFrame(assignments)
        df['יום_מספר'] = df['יום'].apply(lambda x: ordered_days.index(x))
        df = df.sort_values(by=['יום_מספר', 'משמרת', 'עובד'])
        df = df[['יום', 'משמרת', 'עובד']]
        st.success("✅ השיבוץ הושלם!")
        st.dataframe(df, use_container_width=True)

        high_pref_count = sum(preferences.get((a['עובד'], a['יום'], a['משמרת']), 0) == 3 for a in assignments)
        total_assigned = len(assignments)
        percentage = (high_pref_count / total_assigned) * 100 if total_assigned else 0
        st.markdown(f"📊 **{high_pref_count} מתוך {total_assigned}** שיבוצים לפי העדפה גבוהה (3) — **{percentage:.1f}%**")
