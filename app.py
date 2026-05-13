import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

st.set_page_config(layout="wide")

# ================= UI =================
st.markdown("""
<style>
html, body {font-size:16px; color:#000;}
section[data-testid="stSidebar"] {width:360px !important;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Quản lý sự kiện UMP")

# ================= LOAD =================
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

    view = st.selectbox("Chọn chế độ", ["Tháng", "Tuần", "Năm"], index=0)

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

    c1,c2,c3 = st.columns(3)
    c1.metric("Tuần", len(df_year[df_year["start"]>=today-timedelta(days=7)]))
    c2.metric("Tháng", len(df_year[df_year["start"].dt.month==today.month]))
    c3.metric("Năm", len(df_year))

    st.dataframe(df_view.sort_values("start"), use_container_width=True)

    fig = px.timeline(df_year, x_start="start", x_end="end", y="event", color="donvi")
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
            st.warning(f"Trùng: {a} ↔ {b}")
    else:
        st.success("Không có trùng lịch")

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":

    st.subheader("🤖 Trợ giúp AI")
    st.write("👉 Nhập câu hỏi bên dưới rồi nhấn Enter")

    q = st.text_input("Nhập câu hỏi:")

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
                st.subheader("🔧 Tổng hợp")
                st.table(
                    support_df["support"]
                    .value_counts()
                    .reset_index()
                    .rename(columns={"index":"Loại", "support":"Số lượng"})
                )

        else:
            st.info("Chưa hiểu câu hỏi")

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":

    pwd = st.text_input("Nhập mật khẩu", type="password")

    if pwd == st.secrets["auth"]["password"]:

        event = st.selectbox("Chọn sự kiện", df["event"])
        status = st.selectbox("Trạng thái",
            ["Thống nhất", "Chưa thống nhất", "Cần liên hệ"]
        )

        if st.button("Cập nhật"):
            st.success(f"{event} → {status}")

            # gửi email nếu cần
            if status == "Cần liên hệ":
                msg = MIMEText(f"Sự kiện cần hỗ trợ: {event}")
                msg["Subject"] = "Cảnh báo sự kiện"
                msg["From"] = st.secrets["email"]["from"]
                msg["To"] = st.secrets["email"]["to"]

                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(
                        st.secrets["email"]["from"],
                        st.secrets["email"]["password"]
                    )
                    server.send_message(msg)

                st.success("✅ Đã gửi email")

    else:
        st.warning("Nhập mật khẩu")

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":

    st.markdown("""
### 📞 Phòng Hành chính Tổng hợp

217 Hồng Bàng, TP.HCM  

(+84-28) 3855 8411  
(+84-28) 3853 7949  
(+84-28) 3855 5780  

Email: hanhchinh@ump.edu.vn
""")

st.markdown("---")
st.markdown("<center>© TS. Đào Hồng Nam</center>", unsafe_allow_html=True)
``
