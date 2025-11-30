# MasjidLedger AI - Prototype (All-in-One)

### Cara pakai (singkat)
1. Upload file CSV atau XLSX di halaman aplikasi (kolom wajib: `Tanggal`, `Jenis`, `Kategori`, `Jumlah`).
2. Jika belum ada file, download template CSV di tombol yang tersedia.
3. Setelah upload, aplikasi akan:
   - Menampilkan preview,
   - Menghitung total pemasukan / pengeluaran,
   - Menghitung saldo akhir (dengan input Saldo Awal),
   - Menampilkan per kategori & grafik,
   - Mendeteksi duplikat & anomali sederhana,
   - Menghasilkan laporan Excel dan CSV hasil pembersihan.
4. Untuk deploy di Streamlit Cloud: hubungkan repo ke Streamlit Cloud, point ke `app.py`, branch `main`.

Dependencies: lihat `requirements.txt`.
