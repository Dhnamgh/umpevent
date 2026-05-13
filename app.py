import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import plotly.express as px
import re

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
html, body {
    font-family: Arial;
    font-size:16px;
}

section[data-testid="stSidebar"] {
    width:340px !important;
}

/* Calendar */
.fc-event-title {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    line-height: 1.4 !important;
}

.fc-daygrid-event {
    white-space: normal !important;
    align-items: start !important;
    padding: 4px !important;
    border-radius: 6px !important;
}

.fc-daygrid-day-frame {
    min-height: 140px !important;
}

.fc-toolbar-title {
    font-size: 28px !important;
    font-weight: bold !important;
}

</style>
""", unsafe_allow_html=True)

st.title("📊 Quản lý sự kiện UMP")

# ================= PARSE GIỜ =================
def parse_time(text):

    if pd.isna(text):
        return None

    text = str(text).lower()

    m = re.search(r"(\d{1,2})\s*[gh:]\s*(\d{0,2})", text)

    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        return hour, minute

    return None

# ================= LOAD DATA =================
@st.cache_data
def load_data():

    df = pd.read_csv(st.secrets["data"]["csv_url"])

    df.columns = df.columns.str.strip()

    df = df.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location",
        "Hỗ trợ": "support",
        "Giờ bắt đầu": "start_time",
        "Giờ kết thúc": "end_time"
    })

    # parse date
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")

    # nếu không có ngày kết thúc
    df["end"] = df["end"].fillna(df["start"])

    # thêm giờ
    for i in range(len(df)):

        t = parse_time(df.loc[i].get("start_time"))

        if t and pd.notna(df.loc[i, "start"]):
            df.loc[i, "start"] = df.loc[i, "start"].replace(
                hour=t[0],
                minute=t[1]
            )

        t2 = parse_time(df.loc[i].get("end_time"))

        if t2 and pd.notna(df.loc[i, "end"]):
            df.loc[i, "end"] = df.loc[i, "end"].replace(
                hour=t2[0],
                minute=t2[1]
            )

    return df

df = load_data()

today = datetime.today()

# ================= MENU =================
menu = st.sidebar.radio(
    "MENU",
    [
        "Dashboard",
        "Báo cáo",
        "Cảnh báo",
        "Trợ giúp",
        "Phê duyệt",
        "Liên hệ"
    ]
)

# ================= FILTER =================
donvi_list = sorted(df["donvi"].dropna().unique())

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    ["Toàn trường"] + list(donvi_list),
    default=["Toàn trường"]
)

st.sidebar.write("✅ Đang chọn:", ", ".join(selected))

# lọc
if "Toàn trường" in selected:
    df_f = df
else:
    df_f = df[df["donvi"].isin(selected)]

# năm/tháng
df_year = df_f[df_f["start"].dt.year == today.year]

df_month = df_year[
    df_year["start"].dt.month == today.month
]

# ================= COLOR MAP =================
colors = [
    "#1E88E5",
    "#43A047",
    "#E53935",
    "#FB8C00",
    "#8E24AA",
    "#00897B",
    "#6D4C41",
    "#3949AB",
    "#D81B60",
    "#546E7A"
]

color_map = {}

for i, dv in enumerate(df_year["donvi"].dropna().unique()):
    color_map[dv] = colors[i % len(colors)]

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.subheader(
        f"📅 Lịch toàn trường - Tháng {today.month}/{today.year}"
    )

    events = []

    for _, r in df_year.iterrows():

        s = r["start"]
        e = r["end"]

        has_time = not (
            s.hour == 0 and s.minute == 0
        )

        start_str = (
            s.strftime("%Y-%m-%d %H:%M")
            if has_time
            else s.strftime("%Y-%m-%d")
        )

        end_str = (
            e.strftime("%Y-%m-%d %H:%M")
            if has_time
            else e.strftime("%Y-%m-%d")
        )

        # title có giờ
        title = (
            f"{s.strftime('%H:%M')} - {r['event']}"
            if has_time
            else r["event"]
        )

        color = color_map.get(r["donvi"], "#1E88E5")

        events.append({
            "title": title,
            "start": start_str,
            "end": end_str,
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "white",

            "extendedProps": {
                "event": r["event"],
                "donvi": r["donvi"],
                "location": r["location"],
                "time": start_str,
                "support": str(r.get("support", ""))
            }
        })

    selected_event = calendar(
        events=events,

        options={
            "initialView": "dayGridMonth",
            "locale": "vi",
            "height": 950,
            "eventDisplay": "block",
            "displayEventTime": False,
            "dayMaxEventRows": False,
            "eventMaxStack": 20
        }
    )

    # ================= CHI TIẾT =================
    if selected_event and "event" in selected_event:

        e = selected_event["event"]["extendedProps"]

        st.subheader("📋 Chi tiết sự kiện")

        st.write("📌", e.get("event", ""))
        st.write("🏢", e.get("donvi", ""))
        st.write("📍", e.get("location", ""))
        st.write("🕒", e.get("time", ""))
        st.write("🛠", e.get("support", ""))

    # ================= KPI =================
    st.subheader("📈 Tổng quan")

    df_week = df_year[
        (df_year["start"] >= today - timedelta(days=7))
    ]

    c1, c2, c3 = st.columns(3)

    c1.metric("Tuần", len(df_week))
    c2.metric("Tháng", len(df_month))
    c3.metric("Năm", len(df_year))

    # ================= HỖ TRỢ =================
    st.subheader("🛠️ Cần hỗ trợ")

    support_df = df_month[
        df_month["donvi"] == "Phòng Hành chính Tổng hợp"
    ]

    if "support" in support_df.columns and len(support_df) > 0:

        valid = support_df["support"].dropna()

        if len(valid) > 0:

            ss = valid.value_counts().reset_index()

            ss.columns = ["Loại", "Số lượng"]

            st.table(ss)

        else:
            st.info("Không có dữ liệu hỗ trợ")

    else:
        st.info("Không có dữ liệu hỗ trợ")

# ================= BÁO CÁO =================
elif menu == "Báo cáo":

    st.subheader("📊 Báo cáo sự kiện theo đơn vị")

    summary = (
        df_month
        .groupby("donvi")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    fig = px.bar(
        summary,
        x="donvi",
        y="count",
        text="count",
        color="donvi",
        height=700
    )

    fig.update_traces(
        textposition='outside',
        textfont_size=15
    )

    fig.update_layout(
        showlegend=False,

        xaxis_title="Đơn vị",
        yaxis_title="Số sự kiện",

        font=dict(
            size=14,
            color="black"
        ),

        xaxis=dict(
            tickangle=-20,
            automargin=True
        ),

        plot_bgcolor="white"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# ================= CẢNH BÁO =================
elif menu == "Cảnh báo":

    st.subheader("⚠️ Trùng lịch")

    df_check = df[
        (df["start"] >= today) &
        (df["start"] <= today + timedelta(days=30))
    ]

    found = False

    for i in range(len(df_check)):

        for j in range(i + 1, len(df_check)):

            s1 = df_check.iloc[i]["start"]
            s2 = df_check.iloc[j]["start"]

            if s1 == s2:

                found = True

                time_str = (
                    s1.strftime("%H:%M - %d/%m/%Y")
                    if not (
                        s1.hour == 0 and s1.minute == 0
                    )
                    else s1.strftime("%d/%m/%Y")
                )

                st.warning(f"""
🕒 Thời gian trùng: {time_str}

• {df_check.iloc[i]['event']}
  - Địa điểm: {df_check.iloc[i]['location']}

• {df_check.iloc[j]['event']}
  - Địa điểm: {df_check.iloc[j]['location']}
""")

    if not found:
        st.success("Không phát hiện lịch bị trùng")

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":

    st.subheader("🤖 Trợ giúp")

    q = st.text_input("Nhập câu hỏi")

    if q:

        q = q.lower()

        # ===== TUẦN =====
        if "tuần" in q:

            start_week = today - timedelta(days=today.weekday())

            end_week = start_week + timedelta(days=6)

            week_df = df[
                (df["start"] >= start_week) &
                (df["start"] <= end_week)
            ]

            st.write(
                f"📅 Sự kiện tuần "
                f"{start_week.strftime('%d/%m/%Y')} "
                f"- {end_week.strftime('%d/%m/%Y')}"
            )

            if len(week_df) > 0:
                st.dataframe(week_df)
            else:
                st.info("Không có sự kiện trong tuần này")

        # ===== THÁNG =====
        elif "tháng" in q:

            st.write(
                f"📅 Sự kiện tháng "
                f"{today.month}/{today.year}"
            )

            if len(df_month) > 0:
                st.dataframe(df_month)
            else:
                st.info("Không có sự kiện trong tháng")

        # ===== NĂM =====
        elif "năm" in q:

            st.write(
                f"📅 Sự kiện năm {today.year}"
            )

            if len(df_year) > 0:
                st.dataframe(df_year)
            else:
                st.info("Không có sự kiện trong năm")

        # ===== HỖ TRỢ =====
        elif "hỗ trợ" in q:

            support_df = df_month[
                df_month["donvi"]
                == "Phòng Hành chính Tổng hợp"
            ]

            if len(support_df) > 0:
                st.dataframe(support_df)
            else:
                st.info("Không có dữ liệu hỗ trợ")

        else:

            st.warning(
                "Không hiểu yêu cầu. "
                "Hãy nhập: tuần, tháng, năm hoặc hỗ trợ"
            )

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":

    st.subheader("📋 Sự kiện cần phê duyệt")

    st.dataframe(
        df_month,
        use_container_width=True
    )

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":

    st.markdown("""
### Phòng Hành chính Tổng hợp

217 Hồng Bàng, Phường Chợ Lớn, TP.HCM

☎ (+84-28) 3855 8411  
☎ (+84-28) 3853 7949  
☎ (+84-28) 3855 5780

📧 hanhchinh@ump.edu.vn
""")

# ================= FOOTER =================
st.markdown("---")
st.markdown("© TS. Đào Hồng Nam")
