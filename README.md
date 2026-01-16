# English Vocabulary Learning Bot (SRS)

Telegram bot ingliz tili so‘zlarini “Spaced Repetition” asosida yodlash uchun.

## Asosiy funksiyalar
- /start ro‘yxatdan o‘tkazadi va menyu chiqaradi
- /help: yordam bo‘limi (bo‘limlar + navigatsiya)
- /leaderboard: reytinglar (opt-in privacy)
- So‘z qo‘shish (wizard): word → translation → example (ixtiyoriy) → pos (ixtiyoriy)
- Mashq (SRS): karta navbat bilan chiqadi, 4 ta baholash (AGAIN/HARD/GOOD/EASY)
- Statistika: bugungi reviewlar, aniqlik (%), weekly summary
- Sozlamalar: modul bo‘limlar (o‘rganish, testlar, til/tarjima, eslatmalar, cheklovlar)
- Har kuni eslatma: belgilangan vaqtda “Mashq vaqti” xabari (due bo‘lsa)
- Quiz: tarjima bo‘yicha 4 variantdan to‘g‘ri so‘zni tanlash
- Talaffuz: STT orqali bitta so‘z va quiz rejimi

## Env sozlash
`.env` fayl yarating:
```
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql+asyncpg://vocab:vocab@db:5432/vocab
LOG_LEVEL=INFO
```

## Default sozlamalar
- Kunlik maqsad: 10
- Quizdagi so‘zlar soni: 10
- Talaffuz: ON (rejim: both)
- Avto tarjima: ON
- Eslatmalar: OFF, vaqt 20:00
- Talaffuz limiti: 10 (limitlar ON)
- Timezone: Asia/Tashkent (hozircha qat’iy)

## SRS modeli (SM-2)
- Har so‘z uchun `srs_repetitions`, `srs_interval_days`, `srs_ease_factor`, `srs_due_at` saqlanadi
- 4 ta rating SM-2 algoritmiga mos:
  - 😕 Bilmayman (AGAIN = 0)
  - 😐 Qiyin (HARD = 3)
  - 🙂 Yaxshi (GOOD = 4)
  - 😄 Oson (EASY = 5)
- EF formulasi: `EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))`, min 1.3
- Repetitions va interval SM-2 bo‘yicha yangilanadi, due_at = now + interval_days

## Reminder ON/OFF
- Sozlamalarda eslatmani yoqish/o‘chirish mumkin
- Agar due bo‘lmasa, eslatma yuborilmaydi

## Settings (yangi)
⚙️ Sozlamalar 6 ta bo‘limga ajratilgan:
- 🧠 O‘rganish: kunlik maqsad
- 🧩 Testlar: quiz soni, talaffuz ON/OFF, rejim
- 🌍 Til & Tarjima: auto-tarjima ON/OFF, engine holati
- 🔔 Bildirishnomalar: ON/OFF, vaqt
- ⚡ Cheklovlar: talaffuz limiti, limitlar holati
- 🛠 Texnik: reset, session tozalash

## Quiz mode
- Kamida 4 ta so‘z bo‘lsa ishga tushadi
- 10 ta savolgacha, har savolda 4 variant
- To‘g‘ri/xato javoblar SRS’ga ta’sir qiladi

## Practice (SRS-first)
- Mashq faqat `due` so‘zlar bilan ishlaydi
- Due=0 bo‘lsa, bot yangi so‘zlar bilan mashq qilishni so‘raydi
- Edit-message ishlaydi, chat spam bo‘lmaydi
- Baholash: AGAIN / HARD / GOOD / EASY

## Streak
- Kuniga kamida 1 ta SRS review bo‘lsa streak saqlanadi
- 2+ kun bo‘lsa summary’da “🔥 Ketma-ket X kun” ko‘rsatiladi
- Asosiy menyuda indikator: “🔥 X kun”

## Leaderboards (Privacy-safe)
- 3 tur: 🔥 Streak, 🏆 Longest Streak, 📚 So‘zlar soni
- Default: opt-in OFF (user rozi bo‘lmasa ko‘rinmaydi)
- Public name va username ko‘rsatish (ixtiyoriy)
- Chat spam yo‘q: edit-message + pagination

### Leaderboards manual test
1) /leaderboard → menu chiqishi
2) Opt-in OFF holatda ham ro‘yxatni ko‘rish
3) ⚙️ Reyting sozlamalari → opt-in ON
4) Public name o‘rnatish
5) Streak/Words TOP bo‘limlarini ko‘rish

## Pronunciation (MVP)
- 🎯 Bitta so‘z tekshirish: oxirgilar yoki qidirish orqali so‘z tanlang, voice yuboring
- 🧩 Talaffuz quiz: 10 savolgacha, ball bilan baholanadi
- Local STT (faster-whisper) `.env` orqali boshqariladi

### Whisper config
```
PRONUNCIATION_ENABLED=true
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

### Manual test
1) "🗣 Talaffuz" → "🎯 Bitta so‘z tekshirish"
2) So‘z tanlang → 5–10s voice yuboring
3) Natija va transcript qaytadi
4) Ketma-ket 2–3 voice yuborib, parallel bloklanishini tekshiring

## Translation (Google Cloud)
- EN→UZ tavsiya: Google Cloud Translate API
- Tavsiyalar DB cache’da saqlanadi

### Translate config
```
TRANSLATION_ENABLED=true
GOOGLE_TRANSLATE_API_KEY=your_api_key
GOOGLE_TRANSLATE_URL=https://translation.googleapis.com/language/translate/v2
GOOGLE_TRANSLATE_TIMEOUT_SECONDS=15
```

### Manual test
1) "➕ So‘z qo‘shish" → word yuboring
2) Tavsiya chiqishini ko‘ring (yoki fallback)
3) ✅ Davom etish yoki o‘z tarjimangizni yozing
4) 🔄 Boshqa tarjima tugmasini bosing

## Settings manual test
1) ⚙️ Sozlamalar → 🧠 O‘rganish → kunlik maqsadni o‘zgartiring
2) ⚙️ Sozlamalar → 🧩 Testlar → quiz soni va talaffuz rejimini o‘zgartiring
3) ⚙️ Sozlamalar → 🌍 Til & Tarjima → auto-tarjima ON/OFF
4) ⚙️ Sozlamalar → 🔔 Bildirishnomalar → ON/OFF va vaqt kiriting
5) ⚙️ Sozlamalar → ⚡ Cheklovlar → talaffuz limiti (0 bo‘lsa cheksiz)
6) ⚙️ Sozlamalar → 🛠 Texnik → reset

## Admin Panel
- /admin faqat `ADMIN_USER_IDS` ro‘yxatidagi userlar uchun
- Bo‘limlar: Statistika, Users, SRS, Kontent, Feature flag’lar, Maintenance
- Database Management: backup/create/list/restore/delete

### Backup storage
- Backup katalogi: `/app/backups`
- Format: `app_YYYY-MM-DD_HH-MM.dump`
- pg_dump -Fc orqali yaratiladi
- Feature flag’lar global override qiladi (quiz/pronunciation/practice/translation)

### Admin manual test
1) `.env` ga `ADMIN_USER_IDS` qo‘shing
2) /admin → 📊 Umumiy statistika
3) 👥 User qidirish → bloklash/ochish
4) 🧠 SRS reset (confirm bilan)
5) ⚙️ Feature flag’lar → quiz/pronunciation/practice/translation toggle
6) 🧪 Debug → FSM reset / loglar
7) 🗄 Database Management → Backup now / List / Restore / Delete

## Help manual test
1) /help → bo‘limlar chiqishi
2) Tez start → orqaga → boshqa bo‘lim
3) Pronunciation o‘chiq bo‘lsa status ko‘rsin
4) Admin userda “🛠 Admin” bo‘limi ko‘rinsin

## Practice manual test
1) Due=0 bo‘lsa: “Yangi so‘zlar bilan mashq qilamizmi?” prompt chiqadi
2) Due bor bo‘lsa: ⚡ Tezkor mashq (show → rate → next)
3) 🧠 O‘ylab javob berish → text javob → baholash
4) 🛑 To‘xtatish → summary chiqishi
5) 🔁 Yana mashq / 🧠 Rejimni almashtirish

## SM-2 test
```
python scripts/sm2_test.py
```

## Upgrade checklist
- [ ] `.env` to‘ldirildi (BOT_TOKEN, DATABASE_URL, LOG_LEVEL)
- [ ] ADMIN_USER_IDS qo‘shildi (agar admin kerak bo‘lsa)
- [ ] `docker compose up --build` muvaffaqiyatli ishladi
- [ ] `alembic upgrade head` migratsiyalarni o‘tkazdi
- [ ] SRS (SM-2: repetitions/interval/EF/due) ishlayapti
- [ ] Reminder ON/OFF va due-check tekshirildi
- [ ] Settings bo‘limlari (Learning/Tests/Language/Notifications/Limits/Advanced) tekshirildi

## Lokal ishga tushirish (Docker)
```
docker compose up --build
```

## Migratsiyalar
- Container ishga tushganda `alembic upgrade head` avtomatik bajariladi.
- Qo‘lda ishga tushirish:
```
alembic upgrade head
```

## Struktura
```
app/
  main.py
  config.py
  bot/handlers/*.py
  bot/keyboards/*.py
  db/models.py
  db/session.py
  db/repo/*.py
  services/srs.py
  services/reminders.py
alembic/
```
