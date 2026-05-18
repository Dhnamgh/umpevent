import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import plotly.express as px
import re
import hashlib
import json
import requests
from io import BytesIO
from pathlib import Path

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>

/* ===== Sidebar menu buttons - clean equal buttons ===== */
section[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 8px !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    width: 170px !important;
    min-width: 170px !important;
    max-width: 170px !important;
    min-height: 42px !important;
    background: #0f5c99 !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    margin: 5px 0 !important;
    border: 1px solid #0b4a7a !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.18) !important;
    display: flex !important;
    align-items: center !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: #0b4a7a !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
    background: #073b63 !important;
    border-left: 5px solid #facc15 !important;
}

/* Ẩn nút radio tròn */
section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
    display: none !important;
}

/* Chữ menu */
section[data-testid="stSidebar"] div[role="radiogroup"] label p {
    color: #ffffff !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    margin: 0 !important;
    opacity: 1 !important;
    visibility: visible !important;
}


html, body {font-family: Arial, sans-serif; font-size:20px; color:#111827;}
section[data-testid="stSidebar"] {width:255px !important; min-width:255px !important; max-width:255px !important;}

/* Sidebar select options */
section[data-testid="stSidebar"] * {
    font-size: 13px !important;
}

.block-container {padding-top: 1rem;}

/* Warning box font */
div[data-baseweb="notification"] div,
.stAlert p {
    font-size: 13px !important;
    line-height: 1.4 !important;
}


/* Fixed title sizes */
h1, h2, h3, h4, h5, h6,
.stSubheader,
.table-title,
.fc-toolbar-title,
.plotly .gtitle,
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4,
div[data-testid="stMarkdownContainer"] h5,
div[data-testid="stMarkdownContainer"] h6 {
    font-size: 14px !important;
    font-weight: 700 !important;
}

/* Radio labels and small section headings */
div[role="radiogroup"] label,
div[data-baseweb="radio"] label,
.stRadio label,
.stRadio div {
    font-size: 14px !important;
    font-weight: 600 !important;
}


/* Radio labels and small section headings */
div[role="radiogroup"] label,
div[data-baseweb="radio"] label,
.stRadio label,
.stRadio div {
    font-size: 14px !important;
    font-weight: 600 !important;
}


h3, .stSubheader, div[data-testid="stMarkdownContainer"] h3 {
    font-size: 14px !important;
    font-weight: 700 !important;
    margin-top: 0.2rem !important;
    margin-bottom: 0.6rem !important;
}


.table-title {
    font-size: 22px;
    font-weight: 900;
    color: #020617;
    margin-top: 18px;
    margin-bottom: 10px;
    font-family: Arial, sans-serif;
    letter-spacing: -0.2px;
}

.small-note {
    color:#111827;
    font-weight:700;
}

.ump-table-wrap {
    width: 100%;
    overflow-x: auto;
    margin-bottom: 10px;
}

.ump-table-wrap.compact {
    width: fit-content;
    max-width: 100%;
}

.ump-table {
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 15px;
    color: #020617 !important;
    background: white;
}

.ump-table th {
    background: #f1f5f9;
    color: #020617 !important;
    font-weight: 900;
    border: 1px solid #cbd5e1;
    padding: 8px 10px;
    text-align: left;
    white-space: nowrap;
}

.ump-table td {
    color: #020617 !important;
    font-weight: 650;
    border: 1px solid #cbd5e1;
    padding: 7px 10px;
    vertical-align: top;
    line-height: 1.35;
}

.ump-table.compact th,
.ump-table.compact td {
    white-space: nowrap;
}

.ump-table tr:nth-child(even) td {
    background: #f8fafc;
}



}


</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="
    font-size:14px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:0.4px;
    margin-bottom:10px;
    color:#111827;
">
📊 QUẢN LÝ SỰ KIỆN UMP
</div>
""", unsafe_allow_html=True)

# ================= HELPERS =================
def parse_time(text):
    if pd.isna(text):
        return None

    text = str(text).strip().lower()
    if not text or text in ["nan", "none"]:
        return None

    # 7g30, 07g, 7h, 13h00, 14:00
    m = re.search(r"(\d{1,2})\s*[gh:]\s*(\d{0,2})", text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute

    # 7, 07, 13
    m = re.fullmatch(r"\d{1,2}", text)
    if m:
        hour = int(text)
        if 0 <= hour <= 23:
            return hour, 0

    return None


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def is_yes(value):
    txt = clean_text(value).upper()
    return txt in ["CÓ", "CO", "YES", "Y", "TRUE", "1"]


def count_value(value):
    """Convert support quantity to number. Text/CÓ = 1, empty/KHÔNG/0 = 0."""
    txt = clean_text(value)
    if not txt:
        return 0

    up = txt.upper()
    if up in ["KHÔNG", "KHONG", "NO", "N", "FALSE", "0"]:
        return 0

    m = re.search(r"\d+", txt.replace(",", "."))
    if m:
        try:
            return int(m.group(0))
        except Exception:
            return 0

    if up in ["CÓ", "CO", "YES", "Y", "TRUE"]:
        return 1

    return 1


def event_color(index, key):
    """Create stable colors by event, reducing repeated adjacent colors."""
    palette = [
        "#DBEAFE", "#DCFCE7", "#FEE2E2", "#FFEDD5", "#F3E8FF",
        "#CCFBF1", "#FCE7F3", "#E0E7FF", "#CFFAFE", "#FEF3C7",
        "#E5E7EB", "#D1FAE5", "#FAE8FF", "#EDE9FE", "#FDE68A",
        "#BFDBFE", "#BBF7D0", "#FECACA", "#FED7AA", "#DDD6FE"
    ]
    digest = int(hashlib.md5(str(key).encode("utf-8")).hexdigest(), 16)
    return palette[(digest + index) % len(palette)]


def wrap_label(text, width=28):
    words = str(text).split()
    lines = []
    line = ""
    for w in words:
        if len(line + " " + w) <= width:
            line = (line + " " + w).strip()
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return "<br>".join(lines)


def get_period_df(df_input, period):
    now = datetime.today()

    if period == "Tuần":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        label = f"Tuần {start.strftime('%d/%m/%Y')} - {(end - timedelta(days=1)).strftime('%d/%m/%Y')}"

    elif period == "Tháng":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        label = f"Tháng {now.month}/{now.year}"

    else:
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
        label = f"Năm {now.year}"

    out = df_input[(df_input["start"] >= start) & (df_input["start"] < end)].copy()
    return out, label, start, end


def dataframe_to_excel_bytes(dataframe):
    """
    Tạo file Excel dạng .xls bằng HTML để tránh lỗi thiếu module openpyxl/xlsxwriter
    trên Streamlit Cloud. Excel vẫn mở được bình thường.
    """
    html = dataframe.to_html(index=False, escape=False)
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            table {{ border-collapse: collapse; font-family: Arial, sans-serif; }}
            th {{ background: #e5e7eb; font-weight: bold; }}
            th, td {{ border: 1px solid #999; padding: 6px; }}
        </style>
    </head>
    <body>{html}</body>
    </html>
    """
    return html.encode("utf-8-sig")


def excel_file_name(file_name):
    base = str(file_name).rsplit(".", 1)[0]
    return base + ".xls"


def show_table_with_download(title, dataframe, file_name, compact=False):
    st.markdown(f'<div class="table-title">{title}</div>', unsafe_allow_html=True)

    if dataframe is None or len(dataframe) == 0:
        st.info("Không có dữ liệu")
        return

    css_class = "ump-table compact" if compact else "ump-table"
    wrap_class = "ump-table-wrap compact" if compact else "ump-table-wrap"
    html_table = dataframe.to_html(index=False, escape=False, classes=css_class)
    st.markdown(f'<div class="{wrap_class}">{html_table}</div>', unsafe_allow_html=True)

    st.download_button(
        label="⬇️ Tải về Excel",
        data=dataframe_to_excel_bytes(dataframe),
        file_name=excel_file_name(file_name),
        mime="application/vnd.ms-excel",
        use_container_width=False
    )


def collapse_repeated_support_rows(dataframe):
    """Ẩn thông tin lặp lại cho cùng một sự kiện để bảng hỗ trợ dễ đọc hơn."""
    if dataframe is None or len(dataframe) == 0:
        return dataframe

    df_out = dataframe.copy()
    group_cols = ["Sự kiện", "Đơn vị", "Ngày giờ", "Địa điểm"]
    existing = [c for c in group_cols if c in df_out.columns]
    if not existing:
        return df_out

    last_key = None
    for idx in df_out.index:
        key = tuple(df_out.at[idx, c] for c in existing)
        if key == last_key:
            for c in existing:
                df_out.at[idx, c] = ""
        else:
            last_key = key

    return df_out


# ================= GOOGLE SHEET WRITE HELPERS =================
def get_gsheet_webhook_url():
    """URL Apps Script Web App dùng để ghi/cập nhật Google Sheet."""
    try:
        return st.secrets.get("gsheet", {}).get("webhook_url", "")
    except Exception:
        return ""



LOCAL_PENDING_PATH = Path("ump_events_local_pending.json")

def _read_local_pending():
    if not LOCAL_PENDING_PATH.exists():
        return []
    try:
        return json.loads(LOCAL_PENDING_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def _write_local_pending(rows):
    LOCAL_PENDING_PATH.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )

def save_pending_local(payload):
    rows = _read_local_pending()
    action = payload.get("action", "create")
    if action == "create":
        rows.append(payload)
    elif action == "approve":
        found = False
        for row in rows:
            if str(row.get("Id", "")).strip() == str(payload.get("Id", "")).strip():
                row.update(payload)
                found = True
                break
        if not found:
            rows.append(payload)
    _write_local_pending(rows)
    return {"ok": True, "local_pending": True}


def safe_error_message(err):
    """Không hiển thị URL bí mật/webhook trong giao diện app."""
    msg = str(err)
    msg = re.sub(r"https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec", "[WEBHOOK_URL_ẨN]", msg)
    msg = re.sub(r"https://script\.google\.com/macros/s/[^\\s\\)\\]]+", "[WEBHOOK_URL_ẨN]", msg)
    msg = re.sub(r"https://docs\.google\.com/spreadsheets/d/[^\\s\\)\\]]+", "[GOOGLE_SHEET_URL_ẨN]", msg)
    return msg


def read_google_sheet_source():
    """
    Đọc dữ liệu nguồn.
    Ưu tiên đọc trực tiếp qua Apps Script Web App nếu đã cấu hình webhook_url,
    để tránh lỗi CSV Google Sheet chậm cập nhật hoặc đọc nhầm tab.
    Nếu Apps Script chưa có action=read thì fallback về csv_url.
    """
    webhook_url = get_gsheet_webhook_url()

    if webhook_url:
        try:
            response = requests.get(
                webhook_url,
                params={"action": "read"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and isinstance(data.get("rows"), list):
                    return pd.DataFrame(data["rows"])
        except Exception:
            pass

    csv_url = st.secrets["data"]["csv_url"]
    # cache-bust để giảm khả năng Google trả CSV cũ
    sep = "&" if "?" in csv_url else "?"
    return pd.read_csv(f"{csv_url}{sep}_ts={int(datetime.now().timestamp())}")

def post_to_gsheet(payload):
    url = get_gsheet_webhook_url()
    if not url:
        return save_pending_local(payload)

    try:
        response = requests.post(url, data={"payload": json.dumps(payload, ensure_ascii=False)}, headers={"Accept": "application/json"}, timeout=30)
    except Exception as e:
        raise RuntimeError("Không kết nối được Apps Script Web App. Vui lòng kiểm tra webhook_url trong secrets.toml.") from e

    if response.status_code == 403:
        raise RuntimeError(
            "Apps Script Web App đang từ chối truy cập (403). Kiểm tra Deploy Web app: "
            "Execute as = Me, Who has access = Anyone, sau đó Deploy lại và copy URL /exec mới."
        )

    if response.status_code >= 400:
        raise RuntimeError(f"Apps Script Web App trả về lỗi HTTP {response.status_code}.")

    try:
        data = response.json()
    except Exception:
        preview = response.text[:180].replace("\n", " ").replace("\r", " ")
        raise RuntimeError(
            "Apps Script không trả về JSON hợp lệ. Có thể đang dùng URL/deployment cũ hoặc Apps Script trả HTML. "
            "Phản hồi đầu: " + preview
        )

    if not data.get("ok", False):
        raise RuntimeError(data.get("message", "Apps Script trả về lỗi không xác định"))

    # Xóa cache để app đọc lại dữ liệu mới từ Google Sheet CSV
    st.cache_data.clear()
    return data



def show_webhook_config_error():
    st.error("Chưa cấu hình Apps Script Web App URL nên app chưa ghi/cập nhật được Google Sheet.")
    st.code("""
[gsheet]
webhook_url = "DÁN_APPS_SCRIPT_WEB_APP_URL_VÀO_ĐÂY"
""", language="toml")

def build_approval_summary_table(df_input):
    """Bảng phê duyệt rút gọn lấy trực tiếp từ dữ liệu Google Sheet."""
    columns = ["Id", "Sự kiện", "Đơn vị", "Ngày giờ", "Địa điểm", "Hỗ trợ", "Ý kiến"]
    if df_input is None or len(df_input) == 0:
        return pd.DataFrame(columns=columns)

    rows = []
    df_out = df_input.copy().sort_values("start", ascending=True).reset_index(drop=True)

    for _, r in df_out.iterrows():
        s = r.get("start")
        if pd.notna(s):
            ngay_gio = s.strftime("%d/%m/%Y %H:%M")
        else:
            ngay_gio = ""

        rows.append({
            "Id": clean_text(r.get("item_id", "")),
            "Sự kiện": clean_text(r.get("event", "")),
            "Đơn vị": clean_text(r.get("donvi", "")),
            "Ngày giờ": ngay_gio,
            "Địa điểm": clean_text(r.get("location", "")),
            "Hỗ trợ": clean_text(r.get("support", "")) or "Không",
            "Ý kiến": clean_text(r.get("approval_opinion", ""))
        })

    return pd.DataFrame(rows, columns=columns)


def build_registration_payload(
    event_name, donvi, start_dt, end_dt, location,
    nguoi_phu_trach, nguoi_dang_ky, email, support_flag,
    support_values
):
    payload = {
        "action": "create",
        "Thời gian bắt đầu": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Thời gian hoàn thành": "",
        "Tên sự kiện": event_name,
        "Đơn vị phụ trách/ tổ chức": donvi,
        "Ngày tổ chức": start_dt.strftime("%Y-%m-%d"),
        "Ngày kết thúc": end_dt.strftime("%Y-%m-%d"),
        "Giờ bắt đầu": start_dt.strftime("%H:%M"),
        "Giờ kết thúc": end_dt.strftime("%H:%M"),
        "Địa điểm tổ chức": location,
        "Người phụ trách": nguoi_phu_trach,
        "Người đăng ký": nguoi_dang_ky,
        "Email": email,
        "Hỗ trợ": support_flag,
        "Ý kiến của đơn vị quản lý\n (Phòng Hành chính Tổng hợp)": "",
    }

    payload.update(support_values)
    return payload


def build_approval_summary_table(df_input):
    """Tạo bảng Phê duyệt gọn từ dữ liệu gốc giống bản v6, chỉ giữ các cột quan trọng."""
    columns = ["Sự kiện", "Đơn vị", "Ngày giờ", "Địa điểm", "Hỗ trợ"]

    if df_input is None or len(df_input) == 0:
        return pd.DataFrame(columns=columns)

    rows = []
    df_out = df_input.copy()
    df_out["_sort_time"] = pd.to_datetime(df_out["start"], errors="coerce")
    df_out = df_out.sort_values(["_sort_time", "donvi", "event"], ascending=[True, True, True]).reset_index(drop=True)

    for _, r in df_out.iterrows():
        s = r.get("start")
        if pd.notna(s):
            if s.hour == 0 and s.minute == 0:
                ngay_gio = s.strftime("%d/%m/%Y")
            else:
                ngay_gio = s.strftime("%d/%m/%Y %H:%M")
        else:
            ngay_gio = ""

        ho_tro = clean_text(r.get("support", ""))
        if not ho_tro:
            ho_tro = "Không"

        rows.append({
            "Sự kiện": clean_text(r.get("event", "")),
            "Đơn vị": clean_text(r.get("donvi", "")),
            "Ngày giờ": ngay_gio,
            "Địa điểm": clean_text(r.get("location", "")),
            "Hỗ trợ": ho_tro
        })

    return pd.DataFrame(rows, columns=columns)


def build_event_query_table(df_input):
    """Bảng rút gọn cho Truy vấn AI, chỉ giữ các cột quan trọng và sắp xếp theo thời gian."""
    columns = ["Sự kiện", "Đơn vị", "Ngày giờ", "Địa điểm", "Hỗ trợ"]

    if df_input is None or len(df_input) == 0:
        return pd.DataFrame(columns=columns)

    rows = []
    df_out = df_input.copy()
    df_out["_sort_time"] = pd.to_datetime(df_out["start"], errors="coerce")
    df_out = df_out.sort_values(["_sort_time", "donvi", "event"], ascending=[True, True, True]).reset_index(drop=True)

    for _, r in df_out.iterrows():
        s = r.get("start")
        if pd.notna(s):
            if s.hour == 0 and s.minute == 0:
                ngay_gio = s.strftime("%d/%m/%Y")
            else:
                ngay_gio = s.strftime("%d/%m/%Y %H:%M")
        else:
            ngay_gio = ""

        ho_tro = clean_text(r.get("support", ""))
        if not ho_tro:
            ho_tro = "Không"

        rows.append({
            "Sự kiện": clean_text(r.get("event", "")),
            "Đơn vị": clean_text(r.get("donvi", "")),
            "Ngày giờ": ngay_gio,
            "Địa điểm": clean_text(r.get("location", "")),
            "Hỗ trợ": ho_tro
        })

    return pd.DataFrame(rows, columns=columns)



def parse_event_date(value):
    """Parse ngày từ Google Sheet: hỗ trợ dd/mm/yyyy, yyyy-mm-dd và datetime."""
    if pd.isna(value):
        return pd.NaT

    text_value = str(value).strip()
    if not text_value:
        return pd.NaT

    # Thử định dạng ISO trước: 2026-05-29
    dt = pd.to_datetime(text_value, errors="coerce", dayfirst=False)
    if pd.notna(dt):
        return dt

    # Thử định dạng Việt Nam: 29/05/2026
    return pd.to_datetime(text_value, errors="coerce", dayfirst=True)


# ================= LOAD DATA =================
@st.cache_data(ttl=120)
def load_data():
    df = read_google_sheet_source()
    df.columns = df.columns.str.strip()

    df = df.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location",
        "Hỗ trợ": "support",
        "Một số ĐỀ XUẤT HỖ TRỢ từ phòng Hành chính Tổng hợp": "support",
        "Giờ bắt đầu": "start_time",
        "Giờ kết thúc": "end_time",
        "Số lượng bàn đón tiếp": "support_ban_don_tiep",
        "Cần trải khăn bàn hội trường": "support_khan_ban",
        "Số lượng lễ tân": "support_le_tan",
        "Số lượng bảng tên (bảng mica)": "support_bang_ten",
        "Số lượng bìa ký kết": "support_bia_ky_ket",
        "Số lượng nước uống": "support_nuoc_uong",
        "Số phần Teabreak": "support_teabreak",
        "Số lượng hoa để bàn": "support_hoa_ban",
        "Số lượng hoa để bục phát biểu": "support_hoa_buc",
        "Số lượng hoa bó để tặng": "support_hoa_tang",
        "Số lượng quà tặng": "support_qua_tang",
        "Số lượng Brochure": "support_brochure",
        "Số lượng khay bưng": "support_khay_bung",
        "Số lượng bandroll, standee cần in và thi công": "support_bandroll_standee",
        "Số lượng Backdrop cần in và thi công": "support_backdrop",
        "Cần chạy bảng điện tử": "support_bang_dien_tu",
        "Cần gửi thư mời": "support_thu_moi",
        "Các yêu cầu khác (nếu có)": "support_khac",
        "Id": "item_id",
        "ID": "item_id",
        "Thời gian bắt đầu": "submitted_at",
        "Thời gian hoàn thành": "completed_at",
        "Người phụ trách": "nguoi_phu_trach",
        "Người phụ trách sự kiện": "nguoi_phu_trach",
        "Người đăng ký": "nguoi_dang_ky",
        "Người đăng kí": "nguoi_dang_ky",
        "Email": "email",
        "Ý kiến của đơn vị quản lý\n (Phòng Hành chính Tổng hợp)": "approval_opinion",
        "Ý kiến của đơn vị quản lý (Phòng Hành chính Tổng hợp)": "approval_opinion",
        "Ý kiến của Phòng Hành chính Tổng hợp": "approval_opinion"
    })

    df["start"] = df["start"].apply(parse_event_date)
    df["end"] = df["end"].apply(parse_event_date)
    df["end"] = df["end"].fillna(df["start"])

    df = df.dropna(subset=["start"])

    for i in df.index:
        t = parse_time(df.at[i, "start_time"] if "start_time" in df.columns else None)
        if t and pd.notna(df.at[i, "start"]):
            df.at[i, "start"] = df.at[i, "start"].replace(hour=t[0], minute=t[1])

        t2 = parse_time(df.at[i, "end_time"] if "end_time" in df.columns else None)
        if t2 and pd.notna(df.at[i, "end"]):
            df.at[i, "end"] = df.at[i, "end"].replace(hour=t2[0], minute=t2[1])

    for col in [
        "item_id", "event", "donvi", "location", "support",
        "nguoi_phu_trach", "nguoi_dang_ky", "email",
        "approval_opinion", "submitted_at", "completed_at"
    ]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].apply(clean_text)

    # Nếu dữ liệu cũ chưa có Id thì tạo Id tạm để hiển thị, nhưng để phê duyệt/cập nhật ổn định
    # thì Google Sheet nên có cột Id thật.
    if "item_id" in df.columns:
        df["item_id"] = df["item_id"].apply(clean_text)

    return df


def build_support_table(df_input):
    support_cols = {
        "support_ban_don_tiep": "Bàn đón tiếp",
        "support_khan_ban": "Trải khăn bàn hội trường",
        "support_le_tan": "Lễ tân",
        "support_bang_ten": "Bảng tên/bảng mica",
        "support_bia_ky_ket": "Bìa ký kết",
        "support_nuoc_uong": "Nước uống",
        "support_teabreak": "Teabreak",
        "support_hoa_ban": "Hoa để bàn",
        "support_hoa_buc": "Hoa bục phát biểu",
        "support_hoa_tang": "Hoa bó tặng",
        "support_qua_tang": "Quà tặng",
        "support_brochure": "Brochure",
        "support_khay_bung": "Khay bưng",
        "support_bandroll_standee": "Bandroll/standee",
        "support_backdrop": "Backdrop",
        "support_bang_dien_tu": "Bảng điện tử",
        "support_thu_moi": "Gửi thư mời",
        "support_khac": "Yêu cầu khác"
    }

    rows = []

    for _, r in df_input.iterrows():
        has_support_flag = is_yes(r.get("support", ""))
        has_detail = False

        for col, label in support_cols.items():
            if col not in df_input.columns:
                continue

            raw = r.get(col, "")
            qty = count_value(raw)

            if qty > 0:
                has_detail = True
                rows.append({
                    "Sự kiện": r.get("event", ""),
                    "Đơn vị": r.get("donvi", ""),
                    "Ngày giờ": r.get("start").strftime("%d/%m/%Y %H:%M") if pd.notna(r.get("start")) else "",
                    "Địa điểm": r.get("location", ""),
                    "Nội dung hỗ trợ": label,
                    "Số lượng": qty,
                    "Ghi chú/Giá trị gốc": clean_text(raw)
                })

        # Nếu có đánh dấu hỗ trợ nhưng không có cột chi tiết số lượng
        if has_support_flag and not has_detail:
            rows.append({
                "Sự kiện": r.get("event", ""),
                "Đơn vị": r.get("donvi", ""),
                "Ngày giờ": r.get("start").strftime("%d/%m/%Y %H:%M") if pd.notna(r.get("start")) else "",
                "Địa điểm": r.get("location", ""),
                "Nội dung hỗ trợ": "Có yêu cầu hỗ trợ",
                "Số lượng": 1,
                "Ghi chú/Giá trị gốc": clean_text(r.get("support", ""))
            })

    return pd.DataFrame(rows)



def load_data_no_cache():
    """Đọc trực tiếp Google Sheet CSV, không dùng cache, dùng riêng cho menu Phê duyệt."""
    df_raw = read_google_sheet_source()
    df_raw.columns = df_raw.columns.str.strip()

    df_raw = df_raw.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location",
        "Hỗ trợ": "support",
        "Một số ĐỀ XUẤT HỖ TRỢ từ phòng Hành chính Tổng hợp": "support",
        "Giờ bắt đầu": "start_time",
        "Giờ kết thúc": "end_time",
        "Số lượng bàn đón tiếp": "support_ban_don_tiep",
        "Cần trải khăn bàn hội trường": "support_khan_ban",
        "Số lượng lễ tân": "support_le_tan",
        "Số lượng bảng tên (bảng mica)": "support_bang_ten",
        "Số lượng bìa ký kết": "support_bia_ky_ket",
        "Số lượng nước uống": "support_nuoc_uong",
        "Số phần Teabreak": "support_teabreak",
        "Số lượng hoa để bàn": "support_hoa_ban",
        "Số lượng hoa để bục phát biểu": "support_hoa_buc",
        "Số lượng hoa bó để tặng": "support_hoa_tang",
        "Số lượng quà tặng": "support_qua_tang",
        "Số lượng Brochure": "support_brochure",
        "Số lượng khay bưng": "support_khay_bung",
        "Số lượng bandroll, standee cần in và thi công": "support_bandroll_standee",
        "Số lượng Backdrop cần in và thi công": "support_backdrop",
        "Cần chạy bảng điện tử": "support_bang_dien_tu",
        "Cần gửi thư mời": "support_thu_moi",
        "Các yêu cầu khác (nếu có)": "support_khac",
        "Id": "item_id",
        "ID": "item_id",
        "Thời gian bắt đầu": "submitted_at",
        "Thời gian hoàn thành": "completed_at",
        "Người phụ trách": "nguoi_phu_trach",
        "Người phụ trách sự kiện": "nguoi_phu_trach",
        "Người đăng ký": "nguoi_dang_ky",
        "Người đăng kí": "nguoi_dang_ky",
        "Email": "email",
        "Ý kiến của đơn vị quản lý\n (Phòng Hành chính Tổng hợp)": "approval_opinion",
        "Ý kiến của đơn vị quản lý (Phòng Hành chính Tổng hợp)": "approval_opinion",
        "Ý kiến của Phòng Hành chính Tổng hợp": "approval_opinion"
    })

    df_raw["start"] = df_raw["start"].apply(parse_event_date)
    df_raw["end"] = df_raw["end"].apply(parse_event_date)
    df_raw["end"] = df_raw["end"].fillna(df_raw["start"])

    df_raw = df_raw.dropna(subset=["start"])

    for i in df_raw.index:
        t = parse_time(df_raw.at[i, "start_time"] if "start_time" in df_raw.columns else None)
        if t and pd.notna(df_raw.at[i, "start"]):
            df_raw.at[i, "start"] = df_raw.at[i, "start"].replace(hour=t[0], minute=t[1])

        t2 = parse_time(df_raw.at[i, "end_time"] if "end_time" in df_raw.columns else None)
        if t2 and pd.notna(df_raw.at[i, "end"]):
            df_raw.at[i, "end"] = df_raw.at[i, "end"].replace(hour=t2[0], minute=t2[1])

    for col in [
        "item_id", "event", "donvi", "location", "support",
        "approval_opinion", "submitted_at", "completed_at"
    ]:
        if col not in df_raw.columns:
            df_raw[col] = ""
        df_raw[col] = df_raw[col].apply(clean_text)

    return df_raw






def normalize_approval_text(value):
    txt = clean_text(value)
    txt = re.sub(r"\s+", " ", txt).strip()
    if txt.lower() in ["nan", "none", "nat"]:
        return ""
    return txt

def approval_text_from_row(row):
    # Ưu tiên dò mọi cột có cả "Ý kiến" và "Phòng Hành chính Tổng hợp"
    for c in row.index:
        c_norm = re.sub(r"\s+", " ", str(c)).strip()
        if ("Ý kiến" in c_norm and "Phòng Hành chính Tổng hợp" in c_norm) or c == "approval_opinion":
            val = normalize_approval_text(row.get(c, ""))
            if val:
                return val

    candidates = [
        "approval_opinion",
        "Ý kiến của đơn vị quản lý\n (Phòng Hành chính Tổng hợp)",
        "Ý kiến của đơn vị quản lý (Phòng Hành chính Tổng hợp)",
        "Ý kiến của Phòng Hành chính Tổng hợp",
    ]
    for c in candidates:
        if c in row.index:
            return normalize_approval_text(row.get(c, ""))
    return ""

def filter_calendar_approved(df_input):
    if df_input is None or len(df_input) == 0:
        return df_input
    df_out = df_input.copy()
    approval_values = df_out.apply(approval_text_from_row, axis=1)
    return df_out[
        approval_values.eq("Thống nhất") | approval_values.str.startswith("Thống nhất:")
    ].copy()

def filter_pending_approval_events(df_input, current_year):
    if df_input is None or len(df_input) == 0:
        return df_input
    df_out = df_input.copy()
    approvals = df_out.apply(approval_text_from_row, axis=1)
    return df_out[
        (df_out["start"].dt.year == current_year)
        & (approvals == "")
    ].copy()

# ================= DATA =================
df = load_data()
today = datetime.today()



# ================= FORM DEFAULTS =================
if "reg_start_date" not in st.session_state:
    st.session_state.reg_start_date = today.date()
if "reg_end_date" not in st.session_state:
    st.session_state.reg_end_date = today.date()
if "reg_prev_start_date" not in st.session_state:
    st.session_state.reg_prev_start_date = st.session_state.reg_start_date

# ================= MENU =================
menu = st.sidebar.radio(
    "MENU",
    ["Dashboard", "Đăng ký", "Báo cáo", "Cảnh báo", "Hỗ trợ", "Truy vấn AI", "Phê duyệt", "Liên hệ"]
)

# ================= FILTER =================
donvi_list = sorted(df["donvi"].dropna().unique())
selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    ["Toàn trường"] + list(donvi_list),
    default=["Toàn trường"]
)
st.sidebar.write("✅ Đang chọn:", ", ".join(selected))

df_f = df if "Toàn trường" in selected else df[df["donvi"].isin(selected)]
df_all = df_f.copy()
df_year = df_f[df_f["start"].dt.year == today.year]
df_month = df_year[df_year["start"].dt.month == today.month]



# ================= ACCESS AUTH =================
def get_user_password():
    try:
        return st.secrets.get("user", {}).get("password", "")
    except Exception:
        return ""

def get_admin_password():
    try:
        return st.secrets.get("admin", {}).get("password", "")
    except Exception:
        return ""

def require_user_login():
    if st.session_state.get("user_logged_in", False):
        return True

    st.warning("Chức năng này chỉ dành cho người dùng được cấp mật khẩu.")
    password = st.text_input("Nhập mật khẩu người dùng", type="password", key="user_password_input")
    login = st.button("Đăng nhập", key="user_login_button")

    if login:
        user_password = get_user_password()
        if not user_password:
            st.error("Chưa cấu hình mật khẩu người dùng trong secrets.toml.")
            st.code("""
[user]
password = "MAT_KHAU_NGUOI_DUNG"
""", language="toml")
            return False
        if password == user_password:
            st.session_state.user_logged_in = True
            st.success("Đăng nhập thành công.")
            st.rerun()
        else:
            st.error("Sai mật khẩu.")
    return False

def require_admin_login():
    if st.session_state.get("admin_logged_in", False):
        return True

    st.warning("Menu Phê duyệt chỉ dành cho quản trị viên.")
    password = st.text_input("Nhập mật khẩu quản trị", type="password", key="admin_password_input")
    login = st.button("Đăng nhập quản trị", key="admin_login_button")

    if login:
        admin_password = get_admin_password()
        if not admin_password:
            st.error("Chưa cấu hình mật khẩu quản trị trong secrets.toml.")
            st.code("""
[admin]
password = "MAT_KHAU_QUAN_TRI"
""", language="toml")
            return False
        if password == admin_password:
            st.session_state.admin_logged_in = True
            st.success("Đăng nhập quản trị thành công.")
            st.rerun()
        else:
            st.error("Sai mật khẩu quản trị.")
    return False

def enforce_menu_access(menu_name):
    if menu_name in ["Dashboard", "Liên hệ"]:
        return True
    if menu_name == "Phê duyệt":
        return require_admin_login()
    return require_user_login()

# ================= ĐĂNG KÝ =================
if menu == "Đăng ký":
    if not enforce_menu_access(menu):
        st.stop()

    st.markdown('<div style="font-size:14px;font-weight:700;">📝 Đăng ký sự kiện</div>', unsafe_allow_html=True)
    st.info("Dữ liệu đăng ký tạm thời được ghi vào Google Sheet hiện app đang đọc. Sau này lên server trường có thể đổi sang SharePoint List.")

    # Ngày/giờ đặt ngoài form để ngày kết thúc tự đổi theo ngày tổ chức khi người dùng chọn.
    dc1, dc2 = st.columns(2)
    with dc1:
        start_date = st.date_input("Ngày tổ chức", key="reg_start_date")
        start_time = st.time_input(
            "Giờ bắt đầu",
            value=datetime.strptime("07:30", "%H:%M").time()
        )
    with dc2:
        if st.session_state.reg_start_date != st.session_state.reg_prev_start_date:
            st.session_state.reg_end_date = st.session_state.reg_start_date
            st.session_state.reg_prev_start_date = st.session_state.reg_start_date

        end_date = st.date_input("Ngày kết thúc", key="reg_end_date")
        end_time = st.time_input(
            "Giờ kết thúc",
            value=datetime.strptime("13:30", "%H:%M").time()
        )

    support_flag = st.selectbox("Có yêu cầu hỗ trợ?", ["KHÔNG", "CÓ"], key="reg_support_flag")

    with st.form("registration_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            event_name = st.text_input("Tên sự kiện")
            donvi = st.text_input("Đơn vị phụ trách/tổ chức")
            st.caption(f"Ngày giờ tổ chức: {start_date.strftime('%d/%m/%Y')} {start_time.strftime('%H:%M')}")
            st.caption(f"Ngày giờ kết thúc: {end_date.strftime('%d/%m/%Y')} {end_time.strftime('%H:%M')}")
        with c2:
            location = st.text_input("Địa điểm tổ chức")
            nguoi_phu_trach = st.text_input("Người phụ trách")
            nguoi_dang_ky = st.text_input("Người đăng ký")
            email = st.text_input("Email")
            st.caption(f"Có yêu cầu hỗ trợ: {support_flag}")

        support_ban_don_tiep = 0
        support_khan_ban = "KHÔNG"
        support_le_tan = 0
        support_bang_ten = 0
        support_bia_ky_ket = 0
        support_nuoc_uong = 0
        support_teabreak = 0
        support_hoa_ban = 0
        support_hoa_buc = 0
        support_hoa_tang = 0
        support_qua_tang = 0
        support_brochure = 0
        support_khay_bung = 0
        support_bandroll_standee = ""
        support_backdrop = ""
        support_bang_dien_tu = "KHÔNG"
        support_thu_moi = "KHÔNG"
        support_khac = ""

        if support_flag == "CÓ":
            st.markdown('<div class="table-title">Nội dung hỗ trợ</div>', unsafe_allow_html=True)
            s1, s2, s3 = st.columns(3)
            with s1:
                support_ban_don_tiep = st.number_input("Số lượng bàn đón tiếp", min_value=0, step=1)
                support_khan_ban = st.selectbox("Cần trải khăn bàn hội trường", ["KHÔNG", "CÓ"])
                support_le_tan = st.number_input("Số lượng lễ tân", min_value=0, step=1)
                support_bang_ten = st.number_input("Số lượng bảng tên (bảng mica)", min_value=0, step=1)
                support_bia_ky_ket = st.number_input("Số lượng bìa ký kết", min_value=0, step=1)
                support_nuoc_uong = st.number_input("Số lượng nước uống", min_value=0, step=1)
            with s2:
                support_teabreak = st.number_input("Số phần Teabreak", min_value=0, step=1)
                support_hoa_ban = st.number_input("Số lượng hoa để bàn", min_value=0, step=1)
                support_hoa_buc = st.number_input("Số lượng hoa để bục phát biểu", min_value=0, step=1)
                support_hoa_tang = st.number_input("Số lượng hoa bó để tặng", min_value=0, step=1)
                support_qua_tang = st.number_input("Số lượng quà tặng", min_value=0, step=1)
                support_brochure = st.number_input("Số lượng Brochure", min_value=0, step=1)
            with s3:
                support_khay_bung = st.number_input("Số lượng khay bưng", min_value=0, step=1)
                support_bandroll_standee = st.text_input("Số lượng bandroll, standee cần in và thi công")
                support_backdrop = st.text_input("Số lượng Backdrop cần in và thi công")
                support_bang_dien_tu = st.selectbox("Cần chạy bảng điện tử", ["KHÔNG", "CÓ"])
                support_thu_moi = st.selectbox("Cần gửi thư mời", ["KHÔNG", "CÓ"])
                support_khac = st.text_area("Các yêu cầu khác (nếu có)")

        submitted = st.form_submit_button("Gửi đăng ký")

    if submitted:
        if not event_name or not donvi or not location:
            st.error("Vui lòng nhập tối thiểu: Tên sự kiện, Đơn vị và Địa điểm.")
        else:
            start_dt = datetime.combine(start_date, start_time)
            end_dt = datetime.combine(end_date, end_time)

            support_values = {
                "Số lượng bàn đón tiếp": support_ban_don_tiep,
                "Cần trải khăn bàn hội trường": support_khan_ban,
                "Số lượng lễ tân": support_le_tan,
                "Số lượng bảng tên (bảng mica)": support_bang_ten,
                "Số lượng bìa ký kết": support_bia_ky_ket,
                "Số lượng nước uống": support_nuoc_uong,
                "Số phần Teabreak": support_teabreak,
                "Số lượng hoa để bàn": support_hoa_ban,
                "Số lượng hoa để bục phát biểu": support_hoa_buc,
                "Số lượng hoa bó để tặng": support_hoa_tang,
                "Số lượng quà tặng": support_qua_tang,
                "Số lượng Brochure": support_brochure,
                "Số lượng khay bưng": support_khay_bung,
                "Số lượng bandroll, standee cần in và thi công": support_bandroll_standee,
                "Số lượng Backdrop cần in và thi công": support_backdrop,
                "Cần chạy bảng điện tử": support_bang_dien_tu,
                "Cần gửi thư mời": support_thu_moi,
                "Các yêu cầu khác (nếu có)": support_khac,
            }

            payload = build_registration_payload(
                event_name, donvi, start_dt, end_dt, location,
                nguoi_phu_trach, nguoi_dang_ky, email, support_flag,
                support_values
            )

            try:
                result = post_to_gsheet(payload)
                if result.get("local_pending"):
                    st.info("Chưa cấu hình Apps Script Web App URL. Dữ liệu đăng ký đã được lưu tạm vào file ump_events_local_pending.json trên server.")
                else:
                    st.cache_data.clear()
                    st.success("Đã gửi đăng ký và ghi vào Google Sheet. Sự kiện sẽ chỉ hiển thị trên lịch sau khi được phê duyệt là Thống nhất. Sự kiện sẽ chỉ hiển thị trên lịch sau khi được phê duyệt là Thống nhất.")
            except Exception as e:
                if "webhook_url" in str(e):
                    show_webhook_config_error()
                else:
                    st.error(f"Không gửi được đăng ký: {safe_error_message(e)}")

# ================= DASHBOARD =================
elif menu == "Dashboard":
    if st.button("🔄 Làm mới dữ liệu lịch"):
        st.cache_data.clear()
        st.rerun()

    try:
        fresh_dashboard_df = load_data_no_cache()
        fresh_dashboard_df = fresh_dashboard_df if "Toàn trường" in selected else fresh_dashboard_df[fresh_dashboard_df["donvi"].isin(selected)]
        df_f = filter_calendar_approved(fresh_dashboard_df.copy())
    except Exception:
        pass


    # Dashboard/lịch chỉ hiển thị sự kiện đã được phê duyệt là "Thống nhất".
    df_f = filter_calendar_approved(df_f)

    events = []

    for idx, (_, r) in enumerate(df_year.sort_values("start").iterrows()):
        s = r["start"]
        e = r["end"]
        has_time = not (s.hour == 0 and s.minute == 0)

        start_str = s.strftime("%Y-%m-%d %H:%M") if has_time else s.strftime("%Y-%m-%d")
        end_str = e.strftime("%Y-%m-%d %H:%M") if has_time else e.strftime("%Y-%m-%d")

        time_label = s.strftime("%H:%M") if has_time else "Cả ngày"
        location = clean_text(r.get("location", ""))

        title = f"{time_label} - {r['event']}"
        if location:
            title += f"\n📍 {location}"

        color = event_color(idx, f"{r.get('event','')}-{s}-{location}")

        events.append({
            "title": title,
            "start": start_str,
            "end": end_str,
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "#111827",
            "extendedProps": {
                "event": r.get("event", ""),
                "donvi": r.get("donvi", ""),
                "location": location,
                "time": start_str,
                "support": clean_text(r.get("support", ""))
            }
        })

    st.markdown("""
    <style>


    @media (max-width: 768px) {







    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="calendar-mobile-scroll"><div class="calendar-mobile-inner">',
        unsafe_allow_html=True
    )

    selected_event = calendar(
        events=events,
        options={
            "initialView": "dayGridMonth",
            "locale": "vi",
            "firstDay": 1,
            "height": "auto",
            "contentHeight": "auto",
            "expandRows": False,
            "eventDisplay": "block",
            "displayEventTime": False,
            "dayMaxEventRows": False,
            "eventMaxStack": 50,
            "fixedWeekCount": False,
            "handleWindowResize": True
        },
        custom_css="""
        html, body {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }

        .fc { font-family: Arial, sans-serif !important; color:#111827 !important; }

        .fc-toolbar-title {
            font-size: 14px !important;
            font-weight: 800 !important;
            color:#111827 !important;
        }

        .fc-header-toolbar {
            margin-bottom: 6px !important;
        }

        @media (max-width: 768px) {
            html, body {
                width: 100% !important;
                min-width: 100% !important;
                overflow-x: auto !important;
                overflow-y: auto !important;
            }

            #root,
            .fc,
            .fc-view-harness,
            .fc-view-harness-active,
            .fc-view,
            .fc-daygrid,

            .fc-view-harness,

            .fc-daygrid-day {
                min-width: 190px !important;
            }

            .fc-daygrid-day-frame {
                min-height: 135px !important;
            }

            .fc-daygrid-week:has(.fc-daygrid-event) .fc-daygrid-day-frame,
            .fc-scrollgrid-sync-table tr:has(.fc-daygrid-event) .fc-daygrid-day-frame {
                min-height: 190px !important;
            }

            .fc-event-title {
                font-size: 12px !important;
                line-height: 1.28 !important;
            }

            .fc-toolbar {
                flex-wrap: nowrap !important;
                gap: 8px !important;
            }

            .fc-toolbar-title {
            font-size: 14px !important;
                white-space: nowrap !important;
            }
        }
        .fc-toolbar-title {
            font-size: 14px !important; font-weight: 800 !important; color:#111827 !important; }
        .fc-col-header-cell-cushion, .fc-daygrid-day-number { color:#111827 !important; font-weight:800 !important; }

        /* Hàng không có sự kiện co thấp lại. Hàng có sự kiện vẫn đủ cao để đọc nội dung. */
        .fc-daygrid-day-frame { min-height: 58px !important; height: auto !important; padding: 2px !important; }
        .fc-daygrid-week:has(.fc-daygrid-event) .fc-daygrid-day-frame,
        .fc-scrollgrid-sync-table tr:has(.fc-daygrid-event) .fc-daygrid-day-frame {
            min-height: 165px !important;
        }

        .fc-daygrid-day-events { min-height: 1px !important; margin-bottom: 4px !important; }
        .fc-daygrid-event-harness { position: relative !important; margin-top: 4px !important; }
        .fc-daygrid-event { white-space: normal !important; overflow: visible !important; padding: 5px 6px !important; border-radius: 6px !important; border-width: 0 0 0 5px !important; box-shadow: 0 1px 2px rgba(0,0,0,0.08) !important; }
        .fc-event-main { white-space: normal !important; overflow: visible !important; }
        .fc-event-title-container { white-space: normal !important; overflow: visible !important; }
        .fc-event-title { white-space: pre-line !important; overflow: visible !important; text-overflow: unset !important; line-height: 1.35 !important; font-size: 13px !important; font-weight: 700 !important; color:#111827 !important; font-family: Arial, sans-serif !important; }
        .fc-daygrid-block-event .fc-event-title { white-space: pre-line !important; }
        """
    )

    st.markdown("</div></div>", unsafe_allow_html=True)

    if selected_event and "event" in selected_event:
        e = selected_event["event"]["extendedProps"]
        st.subheader("📋 Chi tiết sự kiện")
        st.write("📌", e.get("event", ""))
        st.write("🏢", e.get("donvi", ""))
        st.write("📍", e.get("location", ""))
        st.write("🕒", e.get("time", ""))
        st.write("🛠", e.get("support", ""))

    st.subheader("📈 Tổng quan")
    start_week = today - timedelta(days=today.weekday())
    start_week = start_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_week = start_week + timedelta(days=7)
    df_week = df_year[(df_year["start"] >= start_week) & (df_year["start"] < end_week)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Tuần", len(df_week))
    c2.metric("Tháng", len(df_month))
    c3.metric("Năm", len(df_year))

# ================= BÁO CÁO =================
elif menu == "Báo cáo":
    if not enforce_menu_access(menu):
        st.stop()

    st.markdown('<div style="font-size:14px;font-weight:700;">📊 Báo cáo sự kiện theo đơn vị</div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:14px;font-weight:700;margin-bottom:6px;">Chọn kỳ báo cáo</div>',
        unsafe_allow_html=True
    )
    report_period = st.radio(
        "Chọn kỳ báo cáo",
        ["Tuần", "Tháng", "Năm"],
        index=1,
        horizontal=True,
        label_visibility="collapsed"
    )

    df_report, report_label, _, _ = get_period_df(df_f, report_period)
    st.markdown(
        f'<div style="font-size:14px;font-weight:700;margin-top:8px;">Báo cáo: {report_label}</div>',
        unsafe_allow_html=True
    )

    if len(df_report) == 0:
        st.info(f"Không có sự kiện trong {report_label.lower()}")
    else:
        summary = (
            df_report.groupby("donvi")
            .size()
            .reset_index(name="Số sự kiện")
            .sort_values("Số sự kiện", ascending=True)
        )
        summary["Đơn vị hiển thị"] = summary["donvi"].apply(lambda x: wrap_label(x, 36))

        fig = px.bar(
            summary,
            x="Số sự kiện",
            y="Đơn vị hiển thị",
            text="Số sự kiện",
            color="donvi",
            orientation="h",
            height=max(540, 52 * len(summary) + 180),
            hover_data={"donvi": True, "Đơn vị hiển thị": False}
        )

        fig.update_traces(
            textposition="outside",
            textfont=dict(size=14, color="black", family="Arial Black")
        )

        fig.update_layout(
            title=dict(text="", font=dict(size=1), x=0),
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=30, r=90, t=0, b=40),
            xaxis=dict(title="Số sự kiện", tickfont=dict(size=14, color="black", family="Arial Black"), title_font=dict(size=14, color="black", family="Arial Black")),
            yaxis=dict(title="", tickfont=dict(size=14, color="black", family="Arial Black"), automargin=True)
        )

        st.plotly_chart(fig, use_container_width=True)

        table_report = summary[["donvi", "Số sự kiện"]].sort_values("Số sự kiện", ascending=False)
        table_report = table_report.rename(columns={"donvi": "Đơn vị"}).reset_index(drop=True)
        table_report.insert(0, "STT", range(1, len(table_report) + 1))
        show_table_with_download(
            f"Bảng báo cáo sự kiện theo đơn vị - {report_label}",
            table_report,
            f"bao_cao_su_kien_{report_period.lower()}.xlsx",
            compact=True
        )

# ================= CẢNH BÁO =================
elif menu == "Cảnh báo":
    if not enforce_menu_access(menu):
        st.stop()

    st.markdown('<div style="font-size:14px;font-weight:700;">⚠️ Trùng lịch</div>', unsafe_allow_html=True)

    df_check = df_f[(df_f["start"] >= today) & (df_f["start"] <= today + timedelta(days=30))].copy()
    found = False
    rows = []

    for i in range(len(df_check)):
        for j in range(i + 1, len(df_check)):
            s1 = df_check.iloc[i]["start"]
            s2 = df_check.iloc[j]["start"]
            loc1 = clean_text(df_check.iloc[i].get("location", ""))
            loc2 = clean_text(df_check.iloc[j].get("location", ""))

            same_time = s1 == s2
            overlap = df_check.iloc[i]["start"] < df_check.iloc[j]["end"] and df_check.iloc[j]["start"] < df_check.iloc[i]["end"]

            if same_time or overlap:
                found = True
                time_str_1 = s1.strftime("%H:%M %d/%m/%Y") if not (s1.hour == 0 and s1.minute == 0) else s1.strftime("%d/%m/%Y")
                time_str_2 = s2.strftime("%H:%M %d/%m/%Y") if not (s2.hour == 0 and s2.minute == 0) else s2.strftime("%d/%m/%Y")

                st.warning(f"""
🕒 Thời gian trùng/chồng lấn:

• {time_str_1} - {df_check.iloc[i]['event']}
  - Địa điểm: {loc1}

• {time_str_2} - {df_check.iloc[j]['event']}
  - Địa điểm: {loc2}
""")

                rows.append({
                    "Sự kiện 1": df_check.iloc[i]["event"],
                    "Thời gian 1": time_str_1,
                    "Địa điểm 1": loc1,
                    "Sự kiện 2": df_check.iloc[j]["event"],
                    "Thời gian 2": time_str_2,
                    "Địa điểm 2": loc2
                })

    if not found:
        st.success("Không phát hiện lịch bị trùng trong 30 ngày tới")
    else:
        show_table_with_download(
            "Bảng chi tiết lịch trùng/chồng lấn",
            pd.DataFrame(rows),
            "canh_bao_trung_lich.xlsx"
        )

# ================= HỖ TRỢ =================
elif menu == "Hỗ trợ":
    if not enforce_menu_access(menu):
        st.stop()

    st.markdown("")

    st.markdown('<div class="table-title">Chọn kỳ thống kê hỗ trợ</div>', unsafe_allow_html=True)
    support_period = st.radio(
        "Chọn kỳ thống kê hỗ trợ",
        ["Tuần", "Tháng", "Năm"],
        index=1,
        horizontal=True,
        label_visibility="collapsed"
    )

    df_support_period, support_label, _, _ = get_period_df(df_f, support_period)
    support_table = build_support_table(df_support_period)

    if len(support_table) == 0:
        st.info("Không có thông tin cần hỗ trợ")
    else:
        # Sắp xếp theo thời gian giảm dần: sự kiện gần nhất/mới nhất ở trên cùng.
        support_table["_sort_time"] = pd.to_datetime(
            support_table["Ngày giờ"],
            format="%d/%m/%Y %H:%M",
            errors="coerce"
        )

        support_table = (
            support_table
            .sort_values(
                ["_sort_time", "Đơn vị", "Sự kiện", "Nội dung hỗ trợ"],
                ascending=[False, True, True, True]
            )
            .drop(columns=["_sort_time"])
            .reset_index(drop=True)
        )

        display_support_table = collapse_repeated_support_rows(support_table)
        show_table_with_download(
            f"Bảng sự kiện cần hỗ trợ - {support_label}",
            display_support_table,
            f"su_kien_can_ho_tro_{support_period.lower()}.xlsx"
        )

# ================= TRUY VẤN AI =================
elif menu == "Truy vấn AI":
    if not enforce_menu_access(menu):
        st.stop()

    st.markdown('<div style="font-size:14px;font-weight:700;">🤖 Truy vấn AI</div>', unsafe_allow_html=True)
    q = st.text_input("Nhập câu hỏi, ví dụ: tuần, tháng, năm, hỗ trợ")

    if q:
        q = q.lower()

        if "tuần" in q:
            week_df, label, _, _ = get_period_df(df_f, "Tuần")
            show_table_with_download(f"Sự kiện {label}", build_event_query_table(week_df), "su_kien_tuan.xlsx")

        elif "tháng" in q:
            month_df, label, _, _ = get_period_df(df_f, "Tháng")
            show_table_with_download(f"Sự kiện {label}", build_event_query_table(month_df), "su_kien_thang.xlsx")

        elif "năm" in q:
            year_df, label, _, _ = get_period_df(df_f, "Năm")
            show_table_with_download(f"Sự kiện {label}", build_event_query_table(year_df), "su_kien_nam.xlsx")

        elif "hỗ trợ" in q or "ho tro" in q:
            # Chỉ lấy dữ liệu của năm hiện hành
            support_year_df = df_f[df_f["start"].dt.year == today.year]
            support_df = build_support_table(support_year_df)

            if len(support_df) == 0:
                st.info("Không có thông tin cần hỗ trợ")
            else:
                support_df["_sort_time"] = pd.to_datetime(
                    support_df["Ngày giờ"],
                    format="%d/%m/%Y %H:%M",
                    errors="coerce"
                )

                support_df = (
                    support_df
                    .sort_values(
                        ["_sort_time", "Đơn vị", "Sự kiện", "Nội dung hỗ trợ"],
                        ascending=[True, True, True, True]
                    )
                    .drop(columns=["_sort_time"])
                    .reset_index(drop=True)
                )

                support_display = collapse_repeated_support_rows(support_df)
                show_table_with_download("Danh sách sự kiện cần hỗ trợ", support_display, "danh_sach_can_ho_tro.xlsx")

        else:
            st.warning("Không hiểu yêu cầu. Hãy nhập: tuần, tháng, năm hoặc hỗ trợ")

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":
    st.markdown('<div style="font-size:14px;font-weight:700;">📋 Phê duyệt sự kiện</div>', unsafe_allow_html=True)

    if not enforce_menu_access(menu):
        st.stop()

    if st.session_state.get("approval_success_message"):
        st.success(st.session_state.pop("approval_success_message"))

    if st.button("Đăng xuất quản trị"):
        st.session_state.admin_logged_in = False
        st.rerun()

    if st.button("🔄 Làm mới dữ liệu Google Sheet"):
        st.cache_data.clear()
        st.rerun()

    try:
        approval_source_df = load_data_no_cache()
        approval_source_df = approval_source_df if "Toàn trường" in selected else approval_source_df[approval_source_df["donvi"].isin(selected)]
    except Exception as e:
        st.warning(f"Không đọc trực tiếp được Google Sheet CSV, dùng dữ liệu cache hiện tại. Lỗi: {safe_error_message(e)}")
        approval_source_df = df_f.copy()

    approval_df = approval_source_df.copy()

    pending_df = filter_pending_approval_events(approval_df, today.year)
    pending_df = pending_df.sort_values("start", ascending=True)

    if len(pending_df) == 0:
        st.success("Không có sự kiện đang chờ phê duyệt.")
        st.caption("Nếu vừa đăng ký sự kiện mới mà không thấy ở đây, hãy cập nhật Apps Script theo bản có action=read để app đọc trực tiếp sheet vừa ghi.")
        st.caption(f"Số dòng đọc được từ Google Sheet: {len(approval_df)} | Số dòng trong năm {today.year}: {len(approval_df[approval_df['start'].dt.year == today.year]) if len(approval_df) > 0 else 0}")
    else:
        display_df = build_approval_summary_table(pending_df)
        show_table_with_download(
            "Bảng sự kiện chờ phê duyệt",
            display_df,
            "su_kien_cho_phe_duyet.xlsx"
        )

        st.markdown('<div class="table-title">Xử lý phê duyệt</div>', unsafe_allow_html=True)

        choices = []
        choice_map = {}
        for _, r in pending_df.iterrows():
            time_text = r.get("start").strftime("%d/%m/%Y %H:%M") if pd.notna(r.get("start")) else ""
            item_id = clean_text(r.get("item_id", ""))
            label = f"{time_text} - {r.get('event','')} - {r.get('donvi','')} - ID: {item_id}"
            choices.append(label)
            choice_map[label] = r

        selected_label = st.selectbox("Chọn sự kiện", choices)
        selected_row = choice_map[selected_label]

        st.write("Sự kiện:", selected_row.get("event", ""))
        st.write("Đơn vị:", selected_row.get("donvi", ""))
        st.write("Địa điểm:", selected_row.get("location", ""))

        opinion = st.selectbox(
            "Ý kiến của đơn vị quản lý (Phòng Hành chính Tổng hợp)",
            ["Thống nhất", "Chờ phản hồi", "Không thống nhất"]
        )
        reason = st.text_area("Lý do/Ghi chú")

        if st.button("Cập nhật phê duyệt"):
            item_id = clean_text(selected_row.get("item_id", ""))
            if not item_id:
                st.error("Dòng này chưa có Id. Cần có cột Id trong Google Sheet để cập nhật phê duyệt ổn định.")
            else:
                approval_text = opinion if not reason else f"{opinion}: {reason}"
                payload = {
                    "action": "approve",
                    "Id": item_id,
                    "Thời gian hoàn thành": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "Ý kiến của đơn vị quản lý\n (Phòng Hành chính Tổng hợp)": approval_text,
                }
                try:
                    result = post_to_gsheet(payload)
                    if result.get("local_pending"):
                        st.info("Chưa cấu hình Apps Script Web App URL. Phê duyệt đã được lưu tạm vào file ump_events_local_pending.json trên server.")
                    else:
                        st.success(f"Đã phê duyệt thành công: {opinion}")
                    st.rerun()
                except Exception as e:
                    if "webhook_url" in str(e):
                        show_webhook_config_error()
                    else:
                        st.error(f"Không cập nhật được phê duyệt: {safe_error_message(e)}")


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

st.markdown("---")
st.markdown("Copyright © 2026 Bản quyền thuộc về Phòng Hành chính Tổng hợp, Đại học Y Dược Thành phố Hồ Chí Minh")
