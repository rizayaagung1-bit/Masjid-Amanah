import streamlit as st
import pandas as pd

st.set_page_config(page_title="MasjidLedger AI Basic", layout="wide")
st.title("🕌 MasjidLedger AI — Versi Stabil")

st.write("Upload file Excel (.xlsx) atau CSV untuk dihitung otomatis.")

uploaded_file = st.file_uploader("📂 Upload File Transaksi", type=["csv", "xlsx"])

if uploaded_file is None:
    st.info("Silakan upload file untuk melihat hasil.")
    st.stop()

# ==============================
#  BACA FILE (VERSI PALING AMAN)
# ==============================

try:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"❌ Gagal membaca file: {e}")
    st.stop()

st.subheader("📄 Data Transaksi")
st.dataframe(df)

# ==============================
#   VALIDASI & NORMALISASI
# ==============================

# Ubah nama kolom agar aman (hapus spasi)
df.columns = df.columns.str.strip()

required = ["Tanggal", "Jenis", "Kategori", "Jumlah"]

for col in required:
    if col not in df.columns:
        st.error(f"❌ Kolom wajib '{col}' tidak ditemukan di file.")
        st.stop()

# Format kolom jumlah
df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)

# Jenis harus income / expense
df["Jenis"] = df["Jenis"].str.lower().str.strip()

# ==============================
#     HITUNG RINGKASAN
# ==============================

total_income = df[df["Jenis"] == "income"]["Jumlah"].sum()
total_expense = df[df["Jenis"] == "expense"]["Jumlah"].sum()

st.subheader("📊 Ringkasan Keuangan")

col1, col2 = st.columns(2)
col1.metric("Total Pemasukan", f"Rp {int(total_income):,}")
col2.metric("Total Pengeluaran", f"Rp {int(total_expense):,}")

# Input saldo awal
opening_balance = st.number_input("Masukkan Saldo Awal Masjid (Rp)", min_value=0, value=0, step=10000)

closing_balance = opening_balance + total_income - total_expense

st.metric("💰 Saldo Akhir", f"Rp {int(closing_balance):,}")
