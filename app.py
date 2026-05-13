import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
html, body {
    font-size:16px;
    color:#000 !important;
}
section[data-testid="stSidebar"] {
    width:360px !important;
}
</style>
""", unsafe_allow_html=True)

# ================= TITLE =================
st.title("📊 Quản lý sự kiện UMP")

# ================= LOAD DATA =================
@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(st.secrets["data"]["csv_url"])

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

    return df

df = load_data()
today = datetime.today()

# ================= MENU =================
menu = st.sidebar.radio(
    "MENU",
    ["Dashboard", "Báo cáo", "Cảnh báo", "Trợ giúp", "Phê duyệt", "Liên hệ"]
)

# ================= FILTER =================
donvi_list = sorted(df["donvi"].dropna().unique())

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    ["Toàn trường"] + donvi_list,
    default=["Phòng Hành chính Tổng hợp"]
)

if "Toàn trường" in selected or len(selected)==0:
    df_f = df
else:
    df_f = df[df["donvi"].isin(selected)]

# ================= DASHBOARD =================
if menu == "Dashboard":

    view = st.selectbox("Chọn chế độ hiển thị", ["Tháng", "Tuần", "Năm"], index=0)

    df_year = df[df["start"].dt.year == today.year]

    if view == "Tháng":
        df_view = df_year[df_year["start"].dt.month == today.month]

    elif view == "Tuần":
        df_view = df_year[
            (df_year["start"] >= today - timedelta(days=7)) &
            (df_year["start"] <= today)
        ]

    else:
        df_view = df_year

    # KPI
    c1,c2,c3 = st.columns(3)
    c1.metric("Tuần", len(df_year[df_year["start"]>=today-timedelta(days=7)]))
    c2.metric("Tháng", len(df_year[df_year["start"].dt.month==today.month]))
    c3.metric("Năm", len(df_year))

    # Bảng dữ liệu
    st.dataframe(df_view.sort_values("start"), use_container_width=True)

    # Timeline
    fig = px.timeline(
        df_year,
        x_start="start",
        x_end="end",
        y="event",
        color="donvi"
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# ================= BÁO CÁO =================
elif menu == "Báo cáo":

    st.subheader("📊 Báo cáo theo đơn vị")

    summary = df.groupby("donvi").size().reset_index(name="count")
    st.bar_chart(summary.set_index("donvi"))

# ================= CẢNH BÁO =================
elif menu == "Cảnh báo":

    st.subheader("⚠️ Cảnh báo trùng lịch")

    overlap = []

    for i in range(len(df)):
        for j in range(i+1, len(df)):
            if df.iloc[i]["start"] == df.iloc[j]["start"]:
                overlap.append((df.iloc[i]["event"], df.iloc[j]["event"]))

    if overlap:
        for a, b in overlap:
            st.warning(f"Trùng lịch: {a} ↔ {b}")
    else:
        st.success("Không có trùng lịch")

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":

    st.subheader("🤖 Trợ giúp")

    st.write("👉 Nhập câu hỏi bên dưới và nhấn Enter")

    q = st.text_input(
        "Nhập câu hỏi:",
        placeholder="Ví dụ: sự kiện trong tháng này có bao nhiêu?"
    )

    if q:
        q = q.lower()

        if "tuần" in q:
            res = df[
                (df["start"] >= today - timedelta(days=7)) &
                (df["start"] <= today + timedelta(days=7))
            ]
            st.dataframe(res)

        elif "tháng" in q:
            res = df[df["start"].dt.month == today.month]
            st.dataframe(res)

        elif "đông" in q:
            st.dataframe(df[df["people"] > 100])

        elif "hỗ trợ" in q:
            support_df = df[df["donvi"] == "Phòng Hành chính Tổng hợp"]

            st.dataframe(support_df)

            if "support" in support_df.columns:
                st.subheader("🔧 Tổng hợp hỗ trợ")

                st.table(
                    support_df["support"]
                    .value_counts()
                    .reset_index()
                    .rename(columns={"index":"Loại hỗ trợ", "support":"Số lượng"})
                )
        else:
            st.info("Chưa hiểu câu hỏi")

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":

    st.subheader("📋 Sự kiện cần phê duyệt")

    st.write("👉 Xem danh sách và vào SharePoint để phê duyệt")

    df_year = df[df["start"].dt.year == today.year]
    df_month = df_year[df_year["start"].dt.month == today.month]
    df_pending = df_month[df_month["start"] >= today]

    if len(df_pending) > 0:
        st.dataframe(df_pending.sort_values("start"), use_container_width=True)
    else:
        st.info("Không có sự kiện cần phê duyệt")

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":

    st.markdown("""
### 📞 Phòng Hành chính Tổng hợp

Địa chỉ: 217 Hồng Bàng, Phường Chợ Lớn, TP. Hồ Chí Minh  

Điện thoại:  
(+84-28) 3855 8411  
(+84-28) 3853 7949  
(+84-28) 3855 5780  

Email: hanhchinh@ump.edu.vn
""")

# ================= FOOTER =================
st.markdown("---")
st.markdown("<center>© TS. Đào Hồng Nam</center>", unsafe_allow_html=True)
