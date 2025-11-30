# app.py
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px
import re

st.set_page_config(page_title="MasjidLedger AI — All-in-One", layout="wide")
st.title("🕌 MasjidLedger AI — Pembukuan & Laporan Otomatis (All-in-One)")

st.markdown(
    """Upload 1 file (CSV atau XLSX) berisi seluruh transaksi (pemasukan & pengeluaran).
Kolom wajib: `Tanggal`, `Jenis` (income/expense), `Kategori`, `Jumlah`.  
Gunakan tombol `Download Template` jika perlu contoh file."""
)

# ----------------------------
# Utility functions
# ----------------------------
def clean_number(x):
    """Bersihkan nilai jumlah dari tanda non-digit sehingga bisa diparse ke number."""
    if pd.isna(x):
        return 0
    if isinstance(x, (int, float, np.integer, np.floating)):
        return x
    s = str(x)
    # remove currency symbols and spaces
    s = s.strip()
    # if contains comma as decimal or thousand, replace common thousand separators
    # remove anything except digits, minus, dot, comma
    s = re.sub(r"[^\d\-,\.]", "", s)
    # If there are both ',' and '.', assume '.' decimal and ',' thousand -> remove ','
    if ',' in s and '.' in s:
        # decide which is thousand sep by last occurrence
        if s.rfind(',') > s.rfind('.'):
            # comma likely decimal
            s = s.replace('.', '')
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
    else:
        # if only commas and length >4, remove commas (thousand sep)
        if s.count(',') and len(s.replace(',', '')) >= 1:
            s = s.replace(',', '')
    try:
        val = float(s)
    except:
        try:
            val = float(s.replace(',', '').replace('.', ''))
        except:
            val = 0.0
    return val

def read_upload(ufile):
    try:
        if ufile.name.lower().endswith(".csv"):
            df = pd.read_csv(ufile, encoding="utf-8", low_memory=False)
        else:
            # try sheet 'transaksi' first, else first sheet
            try:
                df = pd.read_excel(ufile, sheet_name="transaksi")
            except Exception:
                df = pd.read_excel(ufile)
        return df
    except Exception as e:
        raise

def to_excel_bytes(df_transactions, df_summary):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_transactions.to_excel(writer, sheet_name="transactions", index=False)
        df_summary.to_excel(writer, sheet_name="summary", index=False)
        writer.save()
    return buffer.getvalue()

def detect_duplicates(df):
    # Duplicate if same Tanggal, Jenis, Kategori, Jumlah (within rounding)
    if all(col in df.columns for col in ["Tanggal","Jenis","Kategori","Jumlah"]):
        subset = df[["Tanggal","Jenis","Kategori","Jumlah"]].copy()
        subset["Jumlah_round"] = subset["Jumlah"].round(0)
        dup_mask = subset.duplicated(keep=False)
        return dup_mask
    return pd.Series([False]*len(df))

def detect_outliers(df, z_thresh=3.0):
    # Simple outlier detection by category using z-score on Jumlah (absolute)
    outlier_mask = pd.Series(False, index=df.index)
    if "Kategori" not in df.columns or "Jumlah" not in df.columns:
        return outlier_mask
    for cat, g in df.groupby("Kategori"):
        vals = g["Jumlah"].astype(float)
        if vals.std(ddof=0) == 0:
            continue
        z = (vals - vals.mean()) / vals.std(ddof=0)
        outlier_idx = z.abs() > z_thresh
        outlier_mask.loc[g.index] = outlier_idx
    return outlier_mask

# ----------------------------
# Main app logic
# ----------------------------
col_template, col_upload = st.columns([1,2])
with col_template:
    st.download_button("⬇️ Download Template CSV", data=(
        "Tanggal,Jenis,Kategori,Jumlah,Keterangan,Sumber/Penerima\n"
        "2025-11-01,income,infaq_masjid,5000000,Infaq Jumat,Kotak Infaq\n"
        "2025-11-01,income,infaq_yatim,2000000,Donasi Yatim,Donatur A\n"
        "2025-11-02,income,infaq_perorangan,2500000,Donasi pribadi,Hamba Allah\n"
        "2025-11-03,expense,kegiatan,800000,Isra' Mi'raj,Panitia Masjid\n"
        "2025-11-04,expense,listrik,900000,Tagihan PLN,PLN\n"
        "2025-11-05,expense,air,550000,Tagihan PDAM,PDAM\n"
        "2025-11-06,expense,perbaikan,250000,Perbaikan AC,Teknisi AC\n"
        "2025-11-07,expense,marbot,100000,Honor mingguan,Marbot\n"
    ), file_name="template_transactions.csv", mime="text/csv")

with col_upload:
    uploaded_file = st.file_uploader("📂 Upload CSV / XLSX (satu file berisi semua transaksi)", type=["csv","xlsx"])

if uploaded_file is None:
    st.info("Silakan upload file transaksi (CSV/XLSX). Gunakan template jika perlu.")
    st.stop()

# read
try:
    df = read_upload(uploaded_file)
except Exception as e:
    st.error(f"❌ Gagal membaca file: {e}")
    st.stop()

# show raw preview
with st.expander("📋 Preview Data (raw, 10 baris)"):
    st.dataframe(df.head(10))

# normalize column names (strip)
df.columns = df.columns.str.strip().str.replace("\n"," ").str.replace("\r"," ")

# check required
required = ["Tanggal","Jenis","Kategori","Jumlah"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"Kolom wajib tidak ditemukan: {missing}. Pastikan file mengikuti template.")
    st.stop()

# process tanggal
try:
    df["Tanggal"] = pd.to_datetime(df["Tanggal"])
except Exception:
    # if fails, leave as is and warn
    st.warning("Kolom 'Tanggal' tidak sepenuhnya terkonversi ke datetime. Pastikan format YYYY-MM-DD atau format Excel standar.")

# clean jumlah
df["Jumlah_raw"] = df["Jumlah"]
df["Jumlah"] = df["Jumlah"].apply(clean_number).astype(float)

# normalize jenis
df["Jenis"] = df["Jenis"].astype(str).str.lower().str.strip()
valid_types = {"income","expense"}
if not df["Jenis"].isin(valid_types).all():
    st.warning("Beberapa baris memiliki nilai 'Jenis' bukan 'income' atau 'expense'. Sistem akan menganggap selain 'income' sebagai 'expense'.")
    df.loc[~df["Jenis"].isin(valid_types), "Jenis"] = "expense"

# simple metrics
total_income = df.loc[df["Jenis"]=="income","Jumlah"].sum()
total_expense = df.loc[df["Jenis"]=="expense","Jumlah"].sum()

# duplicates & outliers
dup_mask = detect_duplicates(df)
outlier_mask = detect_outliers(df, z_thresh=3.0)

df["is_duplicate"] = dup_mask
df["is_outlier"] = outlier_mask

# opening balance input
opening_balance = st.number_input("Masukkan Saldo Awal (Rp)", min_value=0, value=0, step=10000)

# computed
closing_balance = opening_balance + total_income - total_expense
surplus = total_income - total_expense

# summary cards
st.markdown("### 📊 Ringkasan Utama")
c1, c2, c3 = st.columns(3)
c1.metric("Total Pemasukan", f"Rp {int(total_income):,}")
c2.metric("Total Pengeluaran", f"Rp {int(total_expense):,}")
c3.metric("Saldo Akhir (terkalkulasi)", f"Rp {int(closing_balance):,}")

if surplus > 0:
    st.success(f"Surplus: Rp {int(surplus):,}")
elif surplus < 0:
    st.error(f"Defisit: Rp {int(abs(surplus)):,}")
else:
    st.info("Seimbang: pemasukan = pengeluaran")

# breakdown per kategori
st.markdown("### 🔍 Rincian per Kategori")
inc_by_cat = df[df["Jenis"]=="income"].groupby("Kategori", as_index=False)["Jumlah"].sum().sort_values("Jumlah", ascending=False)
exp_by_cat = df[df["Jenis"]=="expense"].groupby("Kategori", as_index=False)["Jumlah"].sum().sort_values("Jumlah", ascending=False)

col_inc, col_exp = st.columns(2)
with col_inc:
    st.subheader("Pemasukan per Kategori")
    st.table(inc_by_cat.assign(Jumlah=inc_by_cat["Jumlah"].map(lambda x: f"Rp {int(x):,}")))
    if not inc_by_cat.empty:
        fig_inc = px.bar(inc_by_cat, x="Kategori", y="Jumlah", title="Pemasukan per Kategori")
        st.plotly_chart(fig_inc, use_container_width=True)
with col_exp:
    st.subheader("Pengeluaran per Kategori")
    st.table(exp_by_cat.assign(Jumlah=exp_by_cat["Jumlah"].map(lambda x: f"Rp {int(x):,}")))
    if not exp_by_cat.empty:
        fig_exp = px.bar(exp_by_cat, x="Kategori", y="Jumlah", title="Pengeluaran per Kategori")
        st.plotly_chart(fig_exp, use_container_width=True)

# time trend
st.markdown("### 📈 Tren Harian (Total per Tanggal)")
if "Tanggal" in df.columns:
    time_series = df.groupby("Tanggal").apply(lambda g: pd.Series({
        "income": g.loc[g["Jenis"]=="income","Jumlah"].sum(),
        "expense": g.loc[g["Jenis"]=="expense","Jumlah"].sum()
    })).reset_index()
    if not time_series.empty:
        fig_ts = px.line(time_series, x="Tanggal", y=["income","expense"], labels={"value":"Jumlah (Rp)","variable":"Tipe"}, title="Tren Harian")
        st.plotly_chart(fig_ts, use_container_width=True)

# anomalies & duplicates
st.markdown("### ⚠️ Pemeriksaan Otomatis (Duplikasi & Anomali)")
st.write(f"Duplikat terdeteksi: {int(df['is_duplicate'].sum())} baris. Anomali (outlier) terdeteksi: {int(df['is_outlier'].sum())} baris.")

if df["is_duplicate"].any():
    with st.expander("Tampilkan baris duplikat"):
        st.dataframe(df[df["is_duplicate"]].sort_values(["Tanggal","Kategori","Jumlah"]))

if df["is_outlier"].any():
    with st.expander("Tampilkan baris outlier"):
        st.dataframe(df[df["is_outlier"]].sort_values("Jumlah", ascending=False))

# export result (excel with transactions + summary)
st.markdown("### ⬇️ Download Laporan & Data")
summary = {
    "period": [st.text_input("Periode laporan (contoh: 2025-11)", value="")],
    "opening_balance": [opening_balance],
    "total_income": [total_income],
    "total_expense": [total_expense],
    "closing_balance": [closing_balance]
}
df_summary = pd.DataFrame(summary)

excel_bytes = to_excel_bytes(df, df_summary)
st.download_button("Download Laporan Excel (transactions + summary)", data=excel_bytes, file_name="masjid_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# quick CSV export of cleaned transactions
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Transaksi (CSV dibersihkan)", data=csv_bytes, file_name="transactions_cleaned.csv", mime="text/csv")

# debug area (collapsed)
with st.expander("🛠️ Debug Info (kolom & sample)"):
    st.write("Kolom terbaca:", list(df.columns))
    st.write("Contoh 10 baris (bersih):")
    st.dataframe(df.head(10))

st.caption("Catatan: Aplikasi ini membaca sheet pertama pada file XLSX atau sheet bernama 'transaksi' jika tersedia. Pastikan kolom wajib ada. Jika ada masalah baca file, gunakan template CSV dan coba lagi.")
