# Discord Multi-Bot Voice Stand-In

Bot Discord berbasis `discord.py` yang memungkinkan menjalankan beberapa akun bot kloningan secara paralel dalam satu proses ringan. Dirancang khusus untuk menghidupkan suasana Voice Channel komunitas saat member asli sedang tidak berada di dalam voice, serta dioptimalkan untuk kontainer hosting spesifikasi rendah (RAM 512 MB / CPU 35% seperti Wispbyte).

## Fitur Utama
- **Auto Stand-In Voice (`on_voice_state_update`):** Bot otomatis masuk ke Voice Channel ketika member target tidak berada di voice, dan langsung keluar begitu member asli bergabung ke voice.
- **Anti-Spam Cooldown (60 Detik):** Memberikan jeda 60 detik saat member keluar dari voice sebelum bot menggantikan, mencegah bot keluar-masuk akibat koneksi member yang tidak stabil.
- **Sinkronisasi Identitas Real-Time:** Otomatis menyamakan *Server Nickname* dan foto profil (*Avatar*, termasuk GIF) mengikuti profil member asli, dilengkapi penyimpanan cache lokal (`avatar_cache.json`) agar aman dari *rate limit* Discord.
- **Konfigurasi Fleksibel (`.env`):** Bebas menyalakan atau mematikan bot tertentu (`BOT_X_ACTIVE=true/false`) tanpa harus mengurutkan ulang penomoran bot.
- **Staggered Startup:** Jeda login bertahap 3 detik antar-bot untuk mencegah lonjakan penggunaan CPU saat server dinyalakan.

---

## 1. Persiapan di Discord Developer Portal

Sebelum menjalankan bot, buat aplikasi bot di [Discord Developer Portal](https://discord.com/developers/applications) untuk setiap member yang ingin dikloning:

1. Klik **New Application**, beri nama, lalu masuk ke tab **Bot**.
2. Klik **Reset Token** dan salin token tersebut untuk dimasukkan ke file `.env`.
3. Scroll ke bagian **Privileged Gateway Intents** dan aktifkan **Server Members Intent**, lalu klik **Save Changes**.
4. Masuk ke tab **OAuth2** -> **URL Generator**:
   - Centang scope **`bot`**.
   - Pada *Bot Permissions*, centang **`View Channels`**, **`Connect`**, dan **`Change Nickname`**.
   - Buka URL yang dihasilkan untuk mengundang bot ke server Discord kamu.

---

## 2. Cara Deploy di Wispbyte (Otomatis via GitHub)

Kamu tidak perlu mengunggah file kode secara manual. Wispbyte dapat menarik langsung kode dari repository ini:

1. Buat server Python baru di panel **Wispbyte**.
2. Masuk ke menu **Startup** dan atur kolom berikut:
   - **Git Repo Address (`GIT_ADDRESS`):** Masukkan URL HTTPS repository
   - **Install Branch (`BRANCH`):** `main`
   - **Auto Update (`AUTO_UPDATE`):** `1`
   - **App py file (`PY_FILE`):** `main.py`
   - **Requirements file (`REQUIREMENTS_FILE`):** `requirements.txt`
3. Masuk ke menu **File Manager**, klik **New File**, dan buat file bernama **`.env`**.
4. Salin isi dari `.env.example` ke dalam file **`.env`** tersebut, lalu isi dengan Token Bot, User ID target, dan Voice Channel ID milikmu.
5. Masuk ke menu **Console** dan klik **Start** / **Restart**. Wispbyte akan otomatis mengunduh kode, memasang library dari `requirements.txt`, dan menjalankan semua bot aktif.

---
