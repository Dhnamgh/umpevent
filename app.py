import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="UMP Dashboard", layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=600)
def load_data():
    url = st.secrets["data"]["csv_url"]
    df = pd.read_csv(url)

    df = df.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location",
        "Số lượng": "people",
        "Hỗ trợ": "support"
    })

    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    df["end"] = df["end"].fillna(df["start"])

    df["month"] = df["start"].dt.month
    df["year"] = df["start"].dt.year

    return df

df = load_data()

# =========================
# MENU SIDEBAR
# =========================
menu = st.sidebar.radio(
    "📋 Chức năng",
    ["Dashboard", "Tổng hợp", "Trợ giúp", "Liên hệ"]
)

# =========================
# FILTER ĐƠN VỊ
# =========================
donvi_list = sorted(df["donvi"].dropna().unique())
options = ["Toàn trường"] + list(donvi_list)

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    options,
    default=["Phòng Hành chính Tổng hợp"]
)

if "Toàn trường" in selected or len(selected) == 0:
    df_f = df.copy()
else:
    df_f = df[df["donvi"].isin(selected)]

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":
    st.title("📊 Dashboard sự kiện")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng sự kiện", len(df_f))
    c2.metric("Số đơn vị", df_f["donvi"].nunique())
    c3.metric("Địa điểm", df_f["location"].nunique())

    st.dataframe(df_f)

    fig = px.timeline(
        df_f,
        x_start="start",
        x_end="end",
        y="event",
        color="donvi"
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# =========================
# TỔNG HỢP
# =========================
elif menu == "Tổng hợp":
    st.title("📊 Báo cáo tổng hợp")

    today = datetime.today()
    current_month = today.month
    current_year = today.year

    df_month = df[
        (df["start"].dt.year == current_year) &
        (df["start"].dt.month == current_month) &
        (df["start"] <= today)
    ]

    df_ytd = df[
        (df["start"].dt.year == current_year) &
        (df["start"] <= today)
    ]

    st.subheader(f"Tháng {current_month}")
    st.metric("Sự kiện", len(df_month))

    st.subheader("YTD")
    st.metric("Sự kiện", len(df_ytd))

# =========================
# TRỢ GIÚP (AI logic)
# =========================
elif menu == "Trợ giúp":
    st.title("🤖 Trợ giúp")

    query = st.text_input("Nhập câu hỏi (ví dụ: sự kiện trong tuần)")

    if query:
        q = query.lower()
        today = datetime.today()

        # mới nhất
        if "mới nhất" in q:
            latest = df.sort_values("start", ascending=False).head(5)
            st.write("Sự kiện mới nhất:")
            st.dataframe(latest)

        # trong tuần
        elif "tuần" in q:
            week = df[
                (df["start"] >= today - pd.Timedelta(days=7)) &
                (df["start"] <= today)
            ]
            st.write("Sự kiện trong tuần:")
            st.dataframe(week)

        # cần hỗ trợ
        elif "hỗ trợ" in q:
            support_df = df[df["donvi"] == "Phòng Hành chính Tổng hợp"]

            if len(support_df) > 0:
                st.write("Sự kiện cần hỗ trợ:")
                st.dataframe(support_df)

                if "support" in support_df.columns:
                    st.write("Loại hỗ trợ:")
                    st.write(support_df["support"].dropna().unique())
            else:
                st.write("Không có sự kiện cần hỗ trợ")

        # đông người
        elif "đông" in q or "100" in q:
            if "people" in df.columns:
                crowded = df[df["people"] > 100]
                st.write("Sự kiện đông người (>100):")
                st.dataframe(crowded)
            else:
                st.warning("Không có dữ liệu số lượng")

        else:
            st.warning("Chưa hiểu câu hỏi")

# =========================
# LIÊN HỆ
# =========================
elif menu == "Liên hệ":
    st.title("📞 Liên hệ")

    st.markdown("""
**Phòng Hành chính Tổng hợp**

Địa chỉ: 217 Hồng Bàng, Phường Chợ Lớn, TP. Hồ Chí Minh  

ĐT: (+84-28) 3855 8411 - (+84-28) 3853 7949 - (+84-28) 3855 5780  

Fax: (+84-28) 3855 2304  

Email: hanhchinh@ump.edu.vn
""")

# =========================
# FOOTER
# =========================
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:gray;'>© TS. Đào Hồng Nam</div>",
    unsafe_allow_html=True
)
