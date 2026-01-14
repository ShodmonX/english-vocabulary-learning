# English Vocabulary Learning Bot (SRS)

Telegram bot ingliz tili so‘zlarini “Spaced Repetition” asosida yodlash uchun.

## Asosiy funksiyalar
- /start ro‘yxatdan o‘tkazadi va menyu chiqaradi
- So‘z qo‘shish (wizard): word → translation → example (ixtiyoriy) → pos (ixtiyoriy)
- Mashq (SRS): karta navbat bilan chiqadi, “Bilardim / Unutdim / O‘tkazib yuborish”
- Statistika: bugungi reviewlar, aniqlik (%), weekly summary
- Sozlamalar: daily_goal, reminder_time, reminder ON/OFF
- Har kuni eslatma: belgilangan vaqtda “Mashq vaqti” xabari (due bo‘lsa)

## Env sozlash
`.env` fayl yarating:
```
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql+asyncpg://vocab:vocab@db:5432/vocab
LOG_LEVEL=INFO
```

## Default sozlamalar
- daily_goal: 10
- reminder_time: 20:00
- timezone: Asia/Tashkent (hozircha qat’iy)

## SRS modeli (yangilangan)
- Har karta uchun `ease_factor` (default 2.5) va `interval_days` saqlanadi
- “Bilardim” → `ease_factor` sekin oshadi, interval yangilanadi
- “Unutdim” → `ease_factor` kamayadi (min 1.3)
- due_at: `interval_days * ease_factor` asosida hisoblanadi

## Reminder ON/OFF
- Sozlamalarda eslatmani yoqish/o‘chirish mumkin
- Agar due bo‘lmasa, eslatma yuborilmaydi

## Upgrade checklist
- [ ] `.env` to‘ldirildi (BOT_TOKEN, DATABASE_URL, LOG_LEVEL)
- [ ] `docker compose up --build` muvaffaqiyatli ishladi
- [ ] `alembic upgrade head` migratsiyalarni o‘tkazdi
- [ ] SRS (ease_factor/interval_days) ishlayapti
- [ ] Reminder ON/OFF va due-check tekshirildi

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
