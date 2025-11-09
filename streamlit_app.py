import streamlit as st
import pandas as pd
import numpy as np
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from scipy.optimize import linear_sum_assignment

st.set_page_config(page_title="🗕️ מערכת שיבוץ חכמה לעובדים", layout="wide")
st.markdown("<h1 style='text-align:center; color:#2C3E50;'>🛠️ מערכת שיבוץ חכמה לעובדים</h1>", unsafe_allow_html=True)

# ===== העלאת קובץ אקסל =====
uploaded_file = st.file_uploader("📤 העלה קובץ Excel בפורמט של שיבוץ (workers, requirements, preferences)", type=["xlsx"])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        workers_df = pd.read_excel(xls, "workers")
        requirements_df = pd.read_excel(xls, "requirements")
        preferences_df = pd.read_excel(xls, "preferences")

        st.success("✅ הקובץ נטען בהצלחה!")

        ordered_days = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
        full_shifts = ['בוקר', 'צהריים', 'לילה']

        workers = workers_df['worker'].dropna().tolist()
        required_workers = {(r['day'], r['shift']): r['required'] for _, r in requirements_df.iterrows()}
        preferences = {(p['worker'], p['day'], p['shift']): p['pref'] for _, p in preferences_df.iterrows()}

        shift_slots = []
        for (day, shift), req in required_workers.items():
            for i in range(int(req)):
                shift_slots.append((day, shift, i))

        # ===== חישוב שיבוץ =====
        if st.button("🚀 בצע שיבוץ"):
            worker_copies = [(w, d, s) for w in workers for (d, s) in required_workers.keys()
                             if preferences.get((w, d, s), -1) >= 0]

            cost_matrix = []
            for w, d, s in worker_copies:
                row = []
                for sd, ss, _ in shift_slots:
                    if (d, s) == (sd, ss):
                        pref = preferences.get((w, d, s), 0)
                        row.append(4 - pref if pref > 0 else 100 if pref == 0 else 1e6)
                    else:
                        row.append(1e6)
                cost_matrix.append(row)
            cost_matrix = np.array(cost_matrix)

            row_ind, col_ind = linear_sum_assignment(cost_matrix)

            assignments = []
            used_slots = set()
            worker_shift_count = {w: 0 for w in workers}
            max_shifts_per_worker = len(shift_slots) // len(workers) + 1

            for r, c in zip(row_ind, col_ind):
                worker, day, shift = worker_copies[r]
                slot = shift_slots[c]
                if cost_matrix[r][c] >= 1e6 or slot in used_slots:
                    continue
                if worker_shift_count[worker] >= max_shifts_per_worker:
                    continue
                used_slots.add(slot)
                assignments.append({'יום': slot[0], 'משמרת': slot[1], 'עובד': worker})
                worker_shift_count[worker] += 1

            df = pd.DataFrame(assignments)
            if not df.empty:
                df['יום_מספר'] = df['יום'].apply(lambda x: ordered_days.index(x))
                df = df.sort_values(by=['יום_מספר', 'משמרת', 'עובד'])
                df = df[['יום', 'משמרת', 'עובד']]

                st.success("✅ השיבוץ הושלם בהצלחה!")
                st.dataframe(df, use_container_width=True)

                # ===== שמירה לקובץ חדש =====
                week_number = st.number_input("📅 מספר שבוע לשמירה", min_value=1, step=1)
                if st.button("💾 הורד קובץ אקסל חדש עם השיבוץ"):
                    output = pd.ExcelWriter("schedule_output.xlsx", engine='openpyxl')
                    for sheet in xls.sheet_names:
                        pd.read_excel(xls, sheet).to_excel(output, index=False, sheet_name=sheet)
                    df.to_excel(output, index=False, sheet_name=f"שבוע {week_number}")
                    output.close()

                    with open("schedule_output.xlsx", "rb") as file:
                        st.download_button(
                            label=f"⬇️ הורד את הקובץ עם השבוע {week_number}",
                            data=file,
                            file_name=f"schedule_week_{week_number}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            else:
                st.warning("⚠️ לא נמצא שיבוץ מתאים.")
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ: {e}")
else:
    st.info("📄 אנא העלה קובץ Excel כדי להתחיל.")
