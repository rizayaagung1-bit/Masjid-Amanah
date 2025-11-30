# app.py
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="MasjidLedger AI - Pembukuan Masjid Otomatis", layout="wide")
st.title("🕌 MasjidLedger AI — Pembukuan Otomatis (Prototype)")

st.markdown(
    "Upload file transaksi (CSV atau Excel). Kolom wajib: `Tanggal`, `Jenis` (income/expense), `Kategori`, `Jumlah`."
)

uploaded_file = st.file_uploader("📂 Upload CSV / Excel (sheet 'transaksi' jika .xlsx)", type=["csv","xlsx"])
if not uploaded_file:
    st.info("Silakan upload file transaksi untuk melihat ringkasan. Gunakan contoh format: Tanggal, Jenis, Kategori, Jumlah, Sumber/Penerima, Keterangan.")
    st.stop()

# --- Baca file ---
try:
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        # try to read sheet 'transaksi' if exists, otherwise first sheet
        try:
            df = pd.read_excel(uploaded_file, sheet_name="transaksi")
        except Exception:
            df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Gagal membaca file: {e}")
    st.stop()

# --- Validasi kolom wajib ---
required_cols = ["Tanggal","Jenis","Kategori","Jumlah"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Kolom wajib tidak ditemukan: {missing}. Pastikan file memiliki kolom: {required_cols}")
    st.stop()

# --- Normalisasi & tipe data ---
df = df.copy()
df.columns = [c.strip() for c in df.columns]
# tanggal
try:
    df["Tanggal"] = pd.to_datetime(df["Tanggal"])
except Exception:
    st.warning("Format kolom 'Tanggal' bermasalah. Pastikan format YYYY-MM-DD atau format yang dikenali pandas.")
# jenis lower
df["Jenis"] = df["Jenis"].astype(str).str.strip().str.lower()
# jumlah numeric
df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0).astype(int)
# kategori trim
df["Kategori"] = df["Kategori"].astype(str).str.strip()

# --- Input saldo awal ---
st.sidebar.header("Pengaturan Periode & Saldo")
period = st.sidebar.text_input("Periode laporan (contoh: 2025-11)", value="")
opening_balance = st.sidebar.number_input("Saldo Awal (Rp)", min_value=0, value=20000000, step=10000)

# --- Hitung ringkasan ---
total_income = int(df.loc[df["Jenis"]=="income","Jumlah"].sum())
total_expense = int(df.loc[df["Jenis"]=="expense","Jumlah"].sum())
closing_balance = opening_balance + total_income - total_expense
surplus = total_income - total_expense

# --- Tampilkan preview & metrik ---
st.subheader("📄 Preview Transaksi (5 baris teratas)")
st.dataframe(df.head())

col1, col2, col3 = st.columns(3)
col1.metric("Total Pemasukan", f"Rp {total_income:,}")
col2.metric("Total Pengeluaran", f"Rp {total_expense:,}")
col3.metric("Saldo Akhir (terkalkulasi)", f"Rp {closing_balance:,}")

# --- Breakdown per kategori ---
st.subheader("📊 Rincian per Kategori (Pemasukan)")
cat_inc = df[df["Jenis"]=="income"].groupby("Kategori")["Jumlah"].sum().reset_index().sort_values("Jumlah", ascending=False)
st.table(cat_inc.style.format({'Jumlah':"Rp {0:,.0f}"}))

st.subheader("📊 Rincian per Kategori (Pengeluaran)")
cat_exp = df[df["Jenis"]=="expense"].groupby("Kategori")["Jumlah"].sum().reset_index().sort_values("Jumlah", ascending=False)
st.table(cat_exp.style.format({'Jumlah':"Rp {0:,.0f}"}))

# --- Simple analysis text ---
st.subheader("📝 Analisis Singkat (otomatis)")
if surplus > 0:
    st.success(f"Masjid mengalami surplus sebesar Rp {surplus:,}. Saldo akhir Rp {closing_balance:,}.")
elif surplus < 0:
    st.warning(f"Masjid mengalami defisit sebesar Rp {abs(surplus):,}. Perlu review pengeluaran atau tambah pemasukan.")
else:
    st.info("Pemasukan sama dengan pengeluaran (netral).")

# --- Export ringkasan CSV ---
st.subheader("⬇️ Ekspor Ringkasan")
summary = {
    "period": period or "not-set",
    "opening_balance": [opening_balance],
    "total_income": [total_income],
    "total_expense": [total_expense],
    "closing_balance": [closing_balance]
}
df_summary = pd.DataFrame(summary)

def to_excel_bytes(df_transactions, df_summary):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_transactions.to_excel(writer, sheet_name="transactions", index=False)
        df_summary.to_excel(writer, sheet_name="summary", index=False)
        writer.save()
    return buffer.getvalue()

excel_bytes = to_excel_bytes(df, df_summary)
st.download_button("Download Laporan (Excel)", data=excel_bytes, file_name="masjid_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.caption("Catatan: Pastikan kolom 'Jenis' berisi 'income' untuk pemasukan dan 'expense' untuk pengeluaran.")
