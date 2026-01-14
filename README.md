# English Vocabulary Learning Bot (SRS)

Telegram bot ingliz tili so‘zlarini “Spaced Repetition” asosida yodlash uchun.

## Asosiy funksiyalar
- /start ro‘yxatdan o‘tkazadi va menyu chiqaradi
- So‘z qo‘shish (wizard): word → translation → example (ixtiyoriy) → pos (ixtiyoriy)
- Mashq (SRS): karta navbat bilan chiqadi, “Bilardim / Unutdim / O‘tkazib yuborish”
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

## SRS modeli (yangilangan)
- Har karta uchun `ease_factor` (default 2.5) va `interval_days` saqlanadi
- “Bilardim” → `ease_factor` sekin oshadi, interval yangilanadi
- “Unutdim” → `ease_factor` kamayadi (min 1.3)
- due_at: `interval_days * ease_factor` asosida hisoblanadi

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

## Upgrade checklist
- [ ] `.env` to‘ldirildi (BOT_TOKEN, DATABASE_URL, LOG_LEVEL)
- [ ] `docker compose up --build` muvaffaqiyatli ishladi
- [ ] `alembic upgrade head` migratsiyalarni o‘tkazdi
- [ ] SRS (ease_factor/interval_days) ishlayapti
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
