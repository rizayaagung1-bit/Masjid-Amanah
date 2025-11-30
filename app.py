import streamlit as st
import pandas as pd

st.title("📘 MasjidAmanah AI – Pembukuan Masjid Otomatis")

uploaded_file = st.file_uploader("Upload File Excel / CSV", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📋 Data Transaksi")
    st.dataframe(df)

    # Hitung total pemasukan dan pengeluaran
    if "Jenis" in df.columns and "Jumlah" in df.columns:
        total_income = df[df["Jenis"]=="income"]["Jumlah"].sum()
        total_expense = df[df["Jenis"]=="expense"]["Jumlah"].sum()

        st.metric("Total Pemasukan", f"Rp {total_income:,}")
        st.metric("Total Pengeluaran", f"Rp {total_expense:,}")
