# Guide Lengkap Fitur Bot Keuangan

## Daftar Fitur

### ✅ Original Commands
- `/summary` - Ringkas hari ini (income, expense, net)
- `/weekly` - Ringkas minggu terakhir
- `/monthly` - Ringkas bulan terakhir
- `/undo` - Hapus transaksi terakhir

---

## 🆕 6 Fitur Baru

### 1️⃣ BUDGET ALERT - Kelola Budget per Kategori

**Membuat/Update Budget:**
```
/setbudget {kategori} {amount}
```
Contoh:
```
/setbudget makan 500000
/setbudget transport 200000
/setbudget belanja 1000000
```

**Cek Budget Kategori:**
```
/budget {kategori}
```
Contoh:
```
/budget makan
→ 💰 Budget makan: Rp 500,000
```

**Lihat Semua Budget:**
```
/budgets
```
Hasil:
```
💰 Daftar Budget Anda:
• makan: Rp 500,000
• transport: Rp 200,000
• belanja: Rp 1,000,000
```

---

### 2️⃣ SPENDING TARGET - Set Target Pengeluaran Harian/Mingguan

**Set Target:**
```
/target {daily|weekly} {amount}
```
Contoh:
```
/target daily 200000    → Target pengeluaran per hari: Rp 200,000
/target weekly 1000000  → Target pengeluaran per minggu: Rp 1,000,000
```

**Cek Target (otomatis saat closing):**
Bot akan otomatis mengingatkan jika Anda melampaui target.

---

### 3️⃣ CATEGORY BREAKDOWN - Lihat Detail Pengeluaran per Kategori

**Format:**
```
/breakdown [hari]
```
Contoh:
```
/breakdown 7     → Breakdown 7 hari terakhir
/breakdown 30    → Breakdown 30 hari terakhir (default)
/breakdown       → Default 30 hari
```

Hasil:
```
📊 Breakdown Pengeluaran (7 hari):
• makan: Rp 1,500,000
• transport: Rp 400,000
• belanja: Rp 800,000

Total: Rp 2,700,000
```

---

### 4️⃣ INCOME vs EXPENSE RATIO - Analisis Keuangan

**Format:**
```
/ratio [hari]
```
Contoh:
```
/ratio 30    → Analisis 30 hari terakhir
/ratio 7     → Analisis 7 hari terakhir
/ratio       → Default 30 hari
```

Hasil:
```
📈 Financial Ratio (30 hari):
Income: Rp 15,000,000
Expense: Rp 8,500,000
Saved: Rp 6,500,000
Saving Rate: 43.3%
```

---

### 5️⃣ TRANSACTION HISTORY SEARCH - Cari Transaksi

**Cari by Kategori:**
```
/history {kategori} [hari]
```
Contoh:
```
/history makan          → Semua transaksi makan (30 hari)
/history makan 7        → Transaksi makan 7 hari terakhir
/history transport      → Semua transaksi transport
```

**Cari by Hari:**
```
/history {hari}
```
Contoh:
```
/history 7              → Semua transaksi 7 hari terakhir
/history 30             → Semua transaksi 30 hari terakhir
```

Hasil:
```
📜 History Transaksi (terakhir 5):
• makan Rp 125,000 (expense)
  Makan siang di restoran
• transport Rp 50,000 (expense)
  Grab ke kantor
• makan Rp 100,000 (expense)
  Sarapan kopi
...
```

---

### 6️⃣ RECURRING TRANSACTIONS - Set Pengeluaran Otomatis

**Tambah Recurring Transaction:**
```
/setrecurring {kategori} {amount} {daily|weekly|monthly} [note]
```
Contoh:
```
/setrecurring listrik 300000 monthly
/setrecurring gym 75000 weekly
/setrecurring transaksi 50000 daily note="Ojek ke rumah"
```

**Lihat Semua Recurring:**
```
/recurring
```
Hasil:
```
🔄 Daftar Recurring Transaction:
1. listrik Rp 300,000 (monthly)
2. gym Rp 75,000 (weekly)
3. transaksi Rp 50,000 (daily)
```

**Cara Kerja:**
- Recurring transactions otomatis dicatat sesuai frequency
- Daily: setiap hari
- Weekly: setiap 7 hari
- Monthly: setiap bulan
- Bot akan auto-insert kapan transaction sudah saatnya

---

## 📋 Format Input Pesan Reguler

Masih sama seperti sebelumnya:
```
{kategori} {amount}
{kategori} {amount} note
```

Contoh:
```
makan 25000
sarapan 15000 beli roti dan kopi
transport 50000
gaji 10000000
```

---

## 🎯 Use Case Praktis

### Kasus 1: Cek Budget Makan
```
User: /budget makan
Bot: 💰 Budget makan: Rp 500,000

User: /history makan 30
Bot: 📜 History Transaksi Makan (30 hari):
- Rp 125,000
- Rp 100,000
- Rp 150,000
- ...
Total: Rp 800,000 (MELEBIHI BUDGET!)
```

### Kasus 2: Track Saving Rate
```
User: /ratio
Bot: 📈 Financial Ratio (30 hari):
Income: Rp 15,000,000
Expense: Rp 8,500,000
Saved: Rp 6,500,000
Saving Rate: 43.3% ✅
```

### Kasus 3: Recurring Bills
```
User: /setrecurring listrik 300000 monthly
Bot: ✅ Recurring monthly untuk listrik Rp 300,000 berhasil ditambah

User: /recurring
Bot: 🔄 Daftar Recurring Transaction:
1. listrik Rp 300,000 (monthly)

(Setiap bulannya Bot otomatis insert Rp 300,000 ke kategori listrik)
```

---

## 📊 Struktur Data

Bot menggunakan 4 sheet di Google Sheets:

1. **Database_Input** - Semua transaksi
   - Timestamp, Phone, Type, Category, Amount, Note, Message_ID

2. **Budget_Settings** - Budget per kategori
   - Timestamp, Phone, Category, Amount

3. **Spending_Target** - Daily/Weekly target
   - Timestamp, Phone, Type (daily/weekly), Amount

4. **Recurring_Transactions** - Transaksi berulang
   - Timestamp, Phone, Category, Amount, Frequency, Last_Run, Note

---

## ⚙️ Environment Variables (Sudah Configured di Railway)

```
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=service_account_json
VERIFY_TOKEN=webhook_verify_token
WHATSAPP_API_TOKEN=api_token
WHATSAPP_PHONE_NUMBER_ID=phone_id
```

---

## 🚀 Tips Penggunaan

1. **Setup Budget Dulu**
   ```
   /setbudget makan 500000
   /setbudget transport 200000
   ```

2. **Set Target Pengeluaran**
   ```
   /target daily 200000
   ```

3. **Recurring Transaksi Tetap**
   ```
   /setrecurring listrik 300000 monthly
   /setrecurring internet 150000 monthly
   ```

4. **Monitoring Rutin**
   - `/summary` setiap pagi
   - `/breakdown 7` setiap Minggu
   - `/ratio` setiap bulan

---

## 📞 Format Error & Solusi

| Error | Solusi |
|-------|--------|
| "Format tidak dikenali" | Gunakan format yang benar |
| "Amount harus angka" | Pastikan amount adalah angka |
| "Belum ada budget" | Gunakan `/setbudget` dulu |
| "Tidak ada transaksi" | Belum ada transaksi di periode tersebut |

---

**Last Updated:** February 9, 2026
**Version:** 2.0 (with 6 new features)
