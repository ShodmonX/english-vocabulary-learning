from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HelpContext:
    word_count: int
    due_count: int
    review_limit: int
    quiz_size: int
    notifications: bool
    notification_time: str | None
    pronunciation_enabled: bool
    pronunciation_available: bool
    translation_enabled: bool
    is_admin: bool
    streak: int


def build_help_content(ctx: HelpContext) -> dict[str, list[str]]:
    quick_start_first = (
        "1) Avval 3 ta so‘z qo‘shing.\n"
        "2) 📚 Mashq qilish → due so‘zlar.\n"
        "3) 😄/🙂/😐/😕 baholash bosing."
        if ctx.word_count == 0
        else "1) 📚 Mashq qilish → due so‘zlar.\n2) Baholash tugmalaridan birini bosing."
    )
    pron_status = "ochiq" if ctx.pronunciation_available else "o‘chiq"
    pron_user_status = "yoqilgan" if ctx.pronunciation_enabled else "o‘chirilgan"
    translation_status = "yoqilgan" if ctx.translation_enabled else "o‘chirilgan"
    streak_line = f"🔥 Sizning streak: {ctx.streak} kun" if ctx.streak >= 1 else "🔥 Streak: hali yo‘q"
    notif_line = (
        f"⏰ Eslatma: {ctx.notification_time or '—'}"
        if ctx.notifications
        else "⏰ Eslatma: o‘chiq"
    )

    return {
        "quick": [
            (
                "📌 Tez start\n\n"
                "Nima? Bot sizga SRS asosida so‘zlarni qayta ko‘rsatadi.\n\n"
                f"Qanday ishlaydi?\n{quick_start_first}\n\n"
                "Tezkor misol:\n"
                "abandon → tarjima → misol → saqlash\n\n"
                "Tugmalar:\n"
                "- 📚 Mashq qilish: due so‘zlar\n"
                "- ➕ So‘z qo‘shish: yangi so‘z\n"
                f"- {streak_line}"
            )
        ],
        "add": [
            (
                "➕ So‘z qo‘shish\n\n"
                "Nima? Yangi so‘z va tarjimani bazaga qo‘shasiz.\n\n"
                "Qanday ishlaydi?\n"
                "1) So‘zni yuborasiz\n"
                "2) Tarjima tavsiya qilinadi\n"
                "3) Misol yozasiz yoki o‘tkazasiz\n\n"
                "Tezkor misol:\n"
                "abandon → tashlab ketmoq → misol → ✅ saqlandi\n\n"
                "Ko‘p xato:\n"
                "- Bo‘sh so‘z yuborish\n"
                "- Juda uzun matn\n\n"
                "Tugmalar:\n"
                "- ✅ Davom etish\n"
                "- 🔄 Boshqa tarjima\n"
                "- ⏭ Misolni o‘tkazish"
            )
        ],
        "srs": [
            (
                "🔁 Bugungi takrorlash (SRS)\n\n"
                "Nima? Faqat due so‘zlar ko‘rsatiladi.\n\n"
                "Qanday ishlaydi?\n"
                f"- Due so‘zlar: {ctx.due_count}\n"
                f"- Sessiya limiti: {ctx.review_limit}\n"
                "- SM-2 baholash: AGAIN/HARD/GOOD/EASY\n\n"
                "Tezkor misol:\n"
                "😕 Bilmayman → tezroq qaytadi\n"
                "😄 Oson → uzoqroq qaytadi\n\n"
                "Ko‘p xato:\n"
                "- Due=0 bo‘lsa so‘z chiqmaydi\n"
                "- “Yangi so‘zlar bilan mashq”ni tasdiqlash kerak\n\n"
                "Tugmalar:\n"
                "- 😕 Bilmayman (AGAIN)\n"
                "- 😐 Qiyin (HARD)\n"
                "- 🙂 Yaxshi (GOOD)\n"
                "- 😄 Oson (EASY)"
            )
        ],
        "quiz": [
            (
                "🧩 Quiz\n\n"
                "Nima? Tarjima beriladi, 4 variantdan so‘zni topasiz.\n\n"
                "Qanday ishlaydi?\n"
                f"- Savollar soni: {ctx.quiz_size}\n"
                "- To‘g‘ri → SRS yangilanadi\n"
                "- Xato → SRS pastga tushadi\n\n"
                "Tezkor misol:\n"
                "Tarjima: tashlab ketmoq → abandon\n\n"
                "Ko‘p xato:\n"
                "- 4 ta so‘zdan kam bo‘lsa quiz ochilmaydi\n\n"
                "Tugmalar:\n"
                "- A/B/C/D variantlar"
            )
        ],
        "pron": [
            (
                "🗣 Talaffuz\n\n"
                "Nima? O‘zingiz qo‘shgan so‘zlarni aytasiz, bot tekshiradi.\n\n"
                f"Holat: {pron_status} (global), sozlamada: {pron_user_status}\n\n"
                "Qanday ishlaydi?\n"
                "- Single: bitta so‘z tekshirish\n"
                "- Quiz: ketma-ket test\n\n"
                "Tezkor misol:\n"
                "🎯 Ayting: abandon → voice yuboring (5–10s)\n\n"
                "Ko‘p xato:\n"
                "- Juda uzun audio\n"
                "- Shovqinli muhit\n\n"
                "Tugmalar:\n"
                "- 🔁 Qayta urinish\n"
                "- 🗂 Boshqa so‘z"
            )
        ],
        "words": [
            (
                "🗂 So‘zlarni boshqarish\n\n"
                "Nima? So‘zlarni qidirish, tahrirlash, o‘chirish.\n\n"
                "Qanday ishlaydi?\n"
                "- 🔎 Qidirish (substring/prefix)\n"
                "- 🕒 Oxirgilar (pagination)\n"
                "- Detail → Edit/Delete\n\n"
                "Ko‘p xato:\n"
                "- Bir xil so‘z qo‘shish (unique)\n"
                "- Tahrirda duplicate so‘z\n\n"
                "Tugmalar:\n"
                "- ✏️ Tahrirlash\n"
                "- 🗑 O‘chirish\n"
                "- ◀️ Orqaga"
            )
        ],
        "settings": [
            (
                "⚙️ Sozlamalar\n\n"
                "Nima? Mashq, quiz, talaffuz va bildirishnomalarni boshqarasiz.\n\n"
                "Sizda hozir:\n"
                f"- Kunlik mashq limiti: {ctx.review_limit}\n"
                f"- Quiz savollari: {ctx.quiz_size}\n"
                f"- Avto tarjima: {translation_status}\n"
                f"- {notif_line}\n\n"
                "Ko‘p xato:\n"
                "- Noto‘g‘ri vaqt formati (HH:MM)\n\n"
                "Tugmalar:\n"
                "- 🧠 O‘rganish\n"
                "- 🧩 Testlar\n"
                "- 🌍 Til & Tarjima"
            )
        ],
        "trouble": [
            (
                "🧩 Muammolar va yechimlar\n\n"
                "1) So‘z qo‘sholmayapman\n"
                "- Sabab: bo‘sh so‘z yoki dublikat\n"
                "- Yechim: boshqa so‘z kiriting\n\n"
                "2) Takrorlashda so‘z chiqmayapti\n"
                "- Sabab: due=0\n"
                "- Yechim: “Yangi so‘zlar bilan mashq”ni tasdiqlang\n\n"
                "3) Talaffuzda xato chiqyapti\n"
                "- Sabab: audio uzun/shovqin\n"
                "- Yechim: 5–10s va sokin joy\n\n"
                "4) Tarjima noto‘g‘ri chiqdi\n"
                "- Yechim: to‘g‘ri tarjimani qo‘lda yozing\n\n"
                "5) Bot javob bermay qoldi\n"
                "- Yechim: /start qayta bosing\n\n"
                "6) Inline tugmalar ishlamayapti\n"
                "- Yechim: chatni yangilang yoki Telegram’ni qayta oching"
            )
        ],
        "privacy": [
            (
                "🔐 Maxfiylik / Ma’lumotlar\n\n"
                "Nima saqlanadi?\n"
                "- Telegram ID, so‘zlar, mashq natijalari\n\n"
                "Nima saqlanmaydi?\n"
                "- Maxfiy parollar yoki shaxsiy fayllar\n\n"
                "Audio:\n"
                "- Talaffuz uchun yuborilgan audio vaqtinchalik qayta ishlanadi\n\n"
                "O‘chirish:\n"
                "- So‘zlarni “So‘zlarim” bo‘limida o‘chirishingiz mumkin"
            )
        ],
        "admin": [
            (
                "🛠 Admin\n\n"
                "Nima? Monitoring va boshqaruv.\n\n"
                "Bo‘limlar:\n"
                "- 📊 Statistika\n"
                "- 👥 Userlar\n"
                "- 🧠 SRS reset\n"
                "- ⚙️ Feature flag’lar\n"
                "- 🧪 Maintenance\n\n"
                "Eslatma:\n"
                "- Admin faqat ADMIN_USER_IDS ro‘yxatida bo‘lganlarga"
            )
        ],
    }
