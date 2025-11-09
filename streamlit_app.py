import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment

# הגדרות כלליות של האפליקציה
st.set_page_config(page_title="🗕️ שיבוץ עובדים", layout="wide")
st.markdown(
    "<h1 style='text-align:center; color:#2C3E50;'>🛠️ מערכת שיבוץ חכמה לעובדים</h1>",
    unsafe_allow_html=True,
)

# ----- הגדרות בסיס -----
ordered_days = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
full_shifts = ['משמרת בוקר', 'משמרת אחצ', 'משמרת לילה']
basic_days = ordered_days[:5]  # א'–ה'

# ----- קלט כללי מהמשתמש -----
num_workers = st.number_input("כמה עובדים יש?", min_value=1, step=1)
work_friday = st.checkbox("עובדים ביום שישי?")
work_saturday = st.checkbox("עובדים ביום שבת?")

shifts_per_day_basic = st.selectbox("כמה משמרות ביום רגיל (א׳–ה׳)?", [1, 2, 3])
selected_shifts_basic = full_shifts[:shifts_per_day_basic]

selected_shifts_friday = full_shifts[:st.selectbox("כמה משמרות בשישי?", [0, 1, 2, 3]) if work_friday else 0]
selected_shifts_saturday = full_shifts[:st.selectbox("כמה משמרות בשבת?", [0, 1, 2, 3]) if work_saturday else 0]

active_days = basic_days + (['שישי'] if work_friday else []) + (['שבת'] if work_saturday else [])

# ----- שמות העובדים -----
st.subheader("👥 שמות העובדים")
workers = []
for i in range(num_workers):
    name = st.text_input(f"שם עובד {i+1}", key=f"worker_{i}")
    if name:
        workers.append(name.strip())

if not workers:
    st.info("הכנס לפחות עובד אחד כדי להמשיך.")
    st.stop()

# ----- דרישות לכל משמרת -----
st.subheader("📋 כמה עובדים דרושים בכל משמרת")
required_workers = {}
shift_slots = []  # (day, shift, index)

for d in active_days:
    if d in basic_days:
        shifts_today = selected_shifts_basic
    elif d == 'שישי':
        shifts_today = selected_shifts_friday
    else:  # שבת
        shifts_today = selected_shifts_saturday

    for s in shifts_today:
        req = st.number_input(
            f"{d} - {s}",
            min_value=0,
            max_value=10,
            value=1,
            key=f"{d}_{s}"
        )
        required_workers[(d, s)] = req
        for i in range(req):
            shift_slots.append((d, s, i))

if len(shift_slots) == 0:
    st.info("לא נבחרו משמרות עם דרישה לעובדים.")
    st.stop()

# ----- העדפות עובדים -----
st.subheader("⭐ העדפות עובדים (1=נמוך, 3=גבוה, -1=לא זמין, 0=שיבוץ רק אם אין ברירה)")
preferences = {}

for w in workers:
    st.markdown(f"**העדפות של {w}:**")
    for d in active_days:
        if d in basic_days:
            shifts_today = selected_shifts_basic
        elif d == 'שישי':
            shifts_today = selected_shifts_friday
        else:
            shifts_today = selected_shifts_saturday

        cols = st.columns(len(shifts_today))
        for i, s in enumerate(shifts_today):
            with cols[i]:
                val = st.slider(
                    f"{d} - {s}",
                    min_value=-1,
                    max_value=3,
                    value=2,
                    key=f"{w}_{d}_{s}"
                )
                preferences[(w, d, s)] = val

# ----- לחצן שיבוץ -----
if st.button("🚀 בצע שיבוץ"):
    # מועמדים – רק משבצות שהעובד זמין בהן (העדפה >= 0)
    worker_copies = []
    for w in workers:
        for d in active_days:
            if d in basic_days:
                shifts_today = selected_shifts_basic
            elif d == 'שישי':
                shifts_today = selected_shifts_friday
            else:
                shifts_today = selected_shifts_saturday

            for s in shifts_today:
                if preferences.get((w, d, s), -1) >= 0:
                    worker_copies.append((w, d, s))

    if not worker_copies:
        st.warning("אין אף עובד זמין באף משמרת לפי ההעדפות.")
        st.stop()

    # ----- בניית מטריצת עלויות -----
    cost_matrix = []
    for w, d, s in worker_copies:
        row = []
        for sd, ss, _ in shift_slots:
            if (d, s) == (sd, ss):
                pref = preferences.get((w, d, s), 0)
                if pref == 0:
                    row.append(100)  # זמין רק אם אין ברירה
                else:
                    row.append(4 - pref)  # העדפה 3 => עלות 1, העדפה 1 => עלות 3
            else:
                row.append(1e6)  # אי התאמה ליום/משמרת
        cost_matrix.append(row)

    cost_matrix = np.array(cost_matrix)
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    # ----- מגבלות ולוגיקה משלימה -----
    assignments = []
    used_workers_in_shift = set()  # (worker, day, shift)
    used_slots = set()            # (day, shift, index)
    worker_shift_count = {w: 0 for w in workers}
    worker_daily_shifts = {w: {d: [] for d in active_days} for w in workers}

    max_shifts_per_worker = len(shift_slots) // len(workers) + 1

    # סיבוב ראשון – לפי העלות המינימלית
    for r, c in sorted(zip(row_ind, col_ind), key=lambda x: cost_matrix[x[0], x[1]]):
        worker, day, shift = worker_copies[r]
        slot = shift_slots[c]
        shift_key = (worker, slot[0], slot[1])

        # אי התאמה לוגית
        if cost_matrix[r][c] >= 1e6 or shift_key in used_workers_in_shift or slot in used_slots:
            continue

        # לא לעבור מכסה לעובד
        if worker_shift_count[worker] >= max_shifts_per_worker:
            continue

        # מניעת משמרות צמודות מדי לאותו עובד באותו יום
        current_shift_index = full_shifts.index(shift)
        if any(abs(full_shifts.index(x) - current_shift_index) == 1
               for x in worker_daily_shifts[worker][day]):
            continue

        used_workers_in_shift.add(shift_key)
        used_slots.add(slot)
        assignments.append({'יום': slot[0], 'משמרת': slot[1], 'עובד': worker})
        worker_shift_count[worker] += 1
        worker_daily_shifts[worker][day].append(shift)

    # סיבוב שני – למלא משמרות ריקות, כולל העדפה 0
    remaining_slots = [slot for slot in shift_slots if slot not in used_slots]
    unassigned_pairs = set()

    for slot in remaining_slots:
        d, s, _ = slot
        assigned = False
        for w in workers:
            if worker_shift_count[w] >= max_shifts_per_worker:
                continue

            pref = preferences.get((w, d, s), -1)
            if pref < 0:
                continue

            current_shift_index = full_shifts.index(s)
            if any(abs(full_shifts.index(x) - current_shift_index) == 1
                   for x in worker_daily_shifts[w][d]):
                continue

            shift_key = (w, d, s)
            if shift_key in used_workers_in_shift:
                continue

            used_workers_in_shift.add(shift_key)
            used_slots.add(slot)
            assignments.append({'יום': d, 'משמרת': s, 'עובד': w})
            worker_shift_count[w] += 1
            worker_daily_shifts[w][d].append(s)
            assigned = True
            break

        if not assigned:
            unassigned_pairs.add((d, s))

    # התראות על משמרות ללא שיבוץ
    for d, s in unassigned_pairs:
        st.warning(f"⚠️ לא שובץ אף אחד ל־{d} - {s}")

    # ----- יצירת טבלה והצגה -----
    df = pd.DataFrame(assignments)

    if not df.empty:
        df['יום_מספר'] = df['יום'].apply(lambda x: ordered_days.index(x))
        df = df.sort_values(by=['יום_מספר', 'משמרת', 'עובד'])
        df = df[['יום', 'משמרת', 'עובד']]

        st.success("✅ השיבוץ הושלם!")
        st.dataframe(df, use_container_width=True)

        # סטטיסטיקת העדפות
        high_pref_count = sum(
            preferences.get((a['עובד'], a['יום'], a['משמרת']), 0) == 3
            for a in assignments
        )
        total_assigned = len(assignments)
        percentage = (high_pref_count / total_assigned) * 100 if total_assigned > 0 else 0
        st.markdown(
            f"📊 **{high_pref_count} מתוך {total_assigned}** שיבוצים לפי העדפה גבוהה (3) — "
            f"**{percentage:.1f}%**"
        )

        # הורדת CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="⬇️ הורד את השיבוץ כקובץ CSV",
            data=csv,
            file_name="shibutz.csv",
            mime="text/csv",
        )
    else:
        st.info("לא בוצע אף שיבוץ.")
