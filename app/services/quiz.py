import random

from app.db.models import Word


def build_quiz_questions(
    all_words: list[Word], due_words: list[Word], max_questions: int = 10
) -> list[dict[str, object]]:
    if len(all_words) < 4:
        return []

    pool = due_words if len(due_words) >= 4 else all_words
    question_count = min(len(pool), max_questions)
    question_words = random.sample(pool, question_count)

    questions: list[dict[str, object]] = []
    for word in question_words:
        distractors = [w for w in all_words if w.id != word.id]
        options = random.sample(distractors, 3) + [word]
        random.shuffle(options)
        questions.append(
            {
                "word_id": word.id,
                "translation": word.translation,
                "word": word.word,
                "options": [(opt.id, opt.word) for opt in options],
            }
        )

    return questions
