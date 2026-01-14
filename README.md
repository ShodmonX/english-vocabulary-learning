# English Vocabulary Learning Bot (SRS)

Telegram bot ingliz tili so‘zlarini “Spaced Repetition” asosida yodlash uchun.

## Asosiy funksiyalar
- /start ro‘yxatdan o‘tkazadi va menyu chiqaradi
- So‘z qo‘shish (wizard): word → translation → example (ixtiyoriy) → pos (ixtiyoriy)
- Mashq (SRS): karta navbat bilan chiqadi, “Bilardim / Unutdim / O‘tkazib yuborish”
- Statistika: bugungi reviewlar, jami so‘zlar, due soni
- Sozlamalar: daily_goal va reminder_time
- Har kuni eslatma: belgilangan vaqtda “Mashq vaqti” xabari

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
