from __future__ import annotations

import ast
import io
import json
import re
from dataclasses import dataclass
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import ensure_admin_callback, ensure_admin_message
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.level_test import admin_level_test_menu_kb
from app.db.repo import level_test as level_test_repo
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()

ALLOWED_LEVEL_TAGS = {"A1", "A2", "B1", "B2", "C1", "C2"}
ALLOWED_TYPES = {"MCQ", "TYPING"}
MAX_JSON_FILE_BYTES = 1024 * 1024


@dataclass(slots=True)
class ValidQuestionPayload:
    level_tag: str
    difficulty: int
    question_type: str
    prompt: str
    choices: list[str] | None
    correct_answer: str | None
    accepted_answers: list[str] | None
    explanation: str | None
    is_active: bool


class QuestionValidationError(ValueError):
    def __init__(self, index: int | str, field: str, message: str) -> None:
        self.index = index
        self.field = field
        self.message = message
        super().__init__(f"[{index}] {field}: {message}")


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_prompt_key(value: str) -> str:
    return _normalize_spaces(value).lower()


def _parse_bool_text(value: str) -> bool | None:
    raw = value.strip().lower()
    if raw in {"ha", "h", "yes", "y", "true", "1", "on"}:
        return True
    if raw in {"yo'q", "yoq", "yo‘q", "no", "n", "false", "0", "off"}:
        return False
    return None


def _split_variants(raw: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[|\n;]", raw) if part.strip()]
    return parts


def _parse_payload_root(raw_payload: str) -> list[dict[str, Any]]:
    parsed: Any
    try:
        parsed = json.loads(raw_payload)
    except Exception:
        try:
            parsed = ast.literal_eval(raw_payload)
        except Exception:
            raise QuestionValidationError(
                "json",
                "payload",
                "Format noto‘g‘ri. JSON list yoki {\"questions\": [...]} yuboring.",
            )

    if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
        parsed = parsed["questions"]
    if not isinstance(parsed, list):
        raise QuestionValidationError(
            "json",
            "payload",
            "Root list bo‘lishi kerak: [{...}] yoki {\"questions\": [...]}",
        )
    return [item for item in parsed]


def _dedupe_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _validate_question(item: dict[str, Any], index: int) -> ValidQuestionPayload:
    if not isinstance(item, dict):
        raise QuestionValidationError(index, "item", "Each question must be an object.")

    level_tag = str(item.get("level_tag", "")).strip().upper()
    if level_tag not in ALLOWED_LEVEL_TAGS:
        raise QuestionValidationError(index, "level_tag", "Use one of A1/A2/B1/B2/C1/C2.")

    try:
        difficulty = int(item.get("difficulty"))
    except (TypeError, ValueError):
        raise QuestionValidationError(index, "difficulty", "Difficulty must be integer 1..5.")
    if difficulty < 1 or difficulty > 5:
        raise QuestionValidationError(index, "difficulty", "Difficulty must be integer 1..5.")

    question_type = str(item.get("type", "")).strip().upper()
    if question_type not in ALLOWED_TYPES:
        raise QuestionValidationError(index, "type", "Type must be MCQ or TYPING.")

    prompt = _normalize_spaces(str(item.get("prompt", "")))
    if not prompt:
        raise QuestionValidationError(index, "prompt", "Prompt is required.")

    correct_answer = _normalize_spaces(str(item.get("correct_answer", "")))
    if not correct_answer:
        raise QuestionValidationError(index, "correct_answer", "Correct answer is required.")

    explanation_raw = item.get("explanation")
    explanation = None
    if explanation_raw is not None:
        explanation = _normalize_spaces(str(explanation_raw))
        if not explanation:
            explanation = None

    is_active_raw = item.get("is_active", True)
    if isinstance(is_active_raw, bool):
        is_active = is_active_raw
    elif isinstance(is_active_raw, str):
        parsed_bool = _parse_bool_text(is_active_raw)
        if parsed_bool is None:
            raise QuestionValidationError(index, "is_active", "Use true/false.")
        is_active = parsed_bool
    else:
        raise QuestionValidationError(index, "is_active", "Use true/false.")

    if question_type == "MCQ":
        choices_raw = item.get("choices")
        if not isinstance(choices_raw, list):
            raise QuestionValidationError(index, "choices", "MCQ choices must be an array of 4 strings.")
        choices = [_normalize_spaces(str(choice)) for choice in choices_raw if str(choice).strip()]
        if len(choices) != 4:
            raise QuestionValidationError(index, "choices", "MCQ requires exactly 4 non-empty options.")
        normalized_choices = {choice.lower() for choice in choices}
        if correct_answer.lower() not in normalized_choices:
            raise QuestionValidationError(index, "correct_answer", "Correct answer must match one of choices.")
        return ValidQuestionPayload(
            level_tag=level_tag,
            difficulty=difficulty,
            question_type=question_type,
            prompt=prompt,
            choices=choices,
            correct_answer=correct_answer,
            accepted_answers=None,
            explanation=explanation,
            is_active=is_active,
        )

    accepted_raw = item.get("accepted_answers")
    accepted_answers: list[str] = []
    if accepted_raw is None:
        accepted_answers = []
    elif isinstance(accepted_raw, list):
        accepted_answers = [_normalize_spaces(str(value)) for value in accepted_raw if str(value).strip()]
    elif isinstance(accepted_raw, str):
        accepted_answers = _split_variants(accepted_raw)
    else:
        raise QuestionValidationError(index, "accepted_answers", "Use array/string/null for typing variants.")

    if correct_answer.lower() not in {value.lower() for value in accepted_answers}:
        accepted_answers.append(correct_answer)
    accepted_answers = _dedupe_ordered(accepted_answers)

    return ValidQuestionPayload(
        level_tag=level_tag,
        difficulty=difficulty,
        question_type=question_type,
        prompt=prompt,
        choices=None,
        correct_answer=correct_answer,
        accepted_answers=accepted_answers,
        explanation=explanation,
        is_active=is_active,
    )


async def _save_questions(validated: list[ValidQuestionPayload]) -> tuple[int, int]:
    inserted = 0
    skipped_duplicates = 0
    async with AsyncSessionLocal() as session:
        existing_keys = await level_test_repo.list_question_prompt_keys(session)
        for question in validated:
            key = (question.question_type, _normalize_prompt_key(question.prompt))
            if key in existing_keys:
                skipped_duplicates += 1
                continue
            await level_test_repo.create_question(
                session,
                level_tag=question.level_tag,
                difficulty=question.difficulty,
                question_type=question.question_type,
                prompt=question.prompt,
                choices=question.choices,
                correct_answer=question.correct_answer,
                accepted_answers=question.accepted_answers,
                explanation=question.explanation,
                is_active=question.is_active,
            )
            existing_keys.add(key)
            inserted += 1
        await session.commit()
    return inserted, skipped_duplicates


async def _process_json_payload(
    message: Message,
    state: FSMContext,
    *,
    raw_payload: str,
) -> None:
    try:
        raw_items = _parse_payload_root(raw_payload)
    except QuestionValidationError as exc:
        await message.answer(
            t(
                "admin_level_test.json_parse_error",
                field=exc.field,
                reason=exc.message,
            ),
            reply_markup=admin_level_test_menu_kb(),
        )
        return

    validated: list[ValidQuestionPayload] = []
    for idx, raw_item in enumerate(raw_items, start=1):
        try:
            validated.append(_validate_question(raw_item, idx))
        except QuestionValidationError as exc:
            await message.answer(
                t(
                    "admin_level_test.item_validation_error",
                    index=exc.index,
                    field=exc.field,
                    reason=exc.message,
                ),
                reply_markup=admin_level_test_menu_kb(),
            )
            return

    inserted, skipped_duplicates = await _save_questions(validated)
    await state.clear()
    await message.answer(
        t(
            "admin_level_test.import_done",
            total=len(validated),
            inserted=inserted,
            skipped=skipped_duplicates,
        ),
        reply_markup=admin_level_test_menu_kb(),
    )


@router.callback_query(F.data == "admin:level_test")
async def admin_level_test_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.level_test_menu)
    await callback.message.edit_text(
        t("admin_level_test.menu"),
        reply_markup=admin_level_test_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:level_test:json")
async def admin_level_test_json_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.level_test_json_input)
    await callback.message.edit_text(
        t("admin_level_test.json_prompt"),
        reply_markup=admin_level_test_menu_kb(),
    )
    await callback.answer()


@router.message(AdminStates.level_test_json_input, F.text)
async def admin_level_test_json_text(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    await _process_json_payload(
        message,
        state,
        raw_payload=message.text or "",
    )


@router.message(AdminStates.level_test_json_input, F.document)
async def admin_level_test_json_file(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    if not message.document:
        await message.answer(t("admin_level_test.file_error"), reply_markup=admin_level_test_menu_kb())
        return
    if message.document.file_size and message.document.file_size > MAX_JSON_FILE_BYTES:
        await message.answer(t("admin_level_test.file_too_large"), reply_markup=admin_level_test_menu_kb())
        return

    try:
        file = await message.bot.get_file(message.document.file_id)
        buffer = io.BytesIO()
        await message.bot.download_file(file.file_path, destination=buffer)
        raw_payload = buffer.getvalue().decode("utf-8")
    except Exception:
        await message.answer(t("admin_level_test.file_error"), reply_markup=admin_level_test_menu_kb())
        return

    await _process_json_payload(message, state, raw_payload=raw_payload)


@router.callback_query(F.data == "admin:level_test:manual")
async def admin_level_test_manual_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.update_data(level_test_manual_draft={})
    await state.set_state(AdminStates.level_test_manual_level_tag)
    await callback.message.edit_text(
        t("admin_level_test.manual_level_tag_prompt"),
        reply_markup=admin_level_test_menu_kb(),
    )
    await callback.answer()


@router.message(AdminStates.level_test_manual_level_tag)
async def admin_level_test_manual_level_tag(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    level_tag = (message.text or "").strip().upper()
    if level_tag not in ALLOWED_LEVEL_TAGS:
        await message.answer(t("admin_level_test.manual_level_tag_invalid"))
        return
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    draft["level_tag"] = level_tag
    await state.update_data(level_test_manual_draft=draft)
    await state.set_state(AdminStates.level_test_manual_difficulty)
    await message.answer(t("admin_level_test.manual_difficulty_prompt"))


@router.message(AdminStates.level_test_manual_difficulty)
async def admin_level_test_manual_difficulty(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    try:
        difficulty = int((message.text or "").strip())
    except ValueError:
        await message.answer(t("admin_level_test.manual_difficulty_invalid"))
        return
    if difficulty < 1 or difficulty > 5:
        await message.answer(t("admin_level_test.manual_difficulty_invalid"))
        return
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    draft["difficulty"] = difficulty
    await state.update_data(level_test_manual_draft=draft)
    await state.set_state(AdminStates.level_test_manual_type)
    await message.answer(t("admin_level_test.manual_type_prompt"))


@router.message(AdminStates.level_test_manual_type)
async def admin_level_test_manual_type(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    question_type = (message.text or "").strip().upper()
    if question_type not in ALLOWED_TYPES:
        await message.answer(t("admin_level_test.manual_type_invalid"))
        return
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    draft["type"] = question_type
    await state.update_data(level_test_manual_draft=draft)
    await state.set_state(AdminStates.level_test_manual_prompt)
    await message.answer(t("admin_level_test.manual_prompt_prompt"))


@router.message(AdminStates.level_test_manual_prompt)
async def admin_level_test_manual_prompt(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    prompt = _normalize_spaces(message.text or "")
    if not prompt:
        await message.answer(t("admin_level_test.manual_prompt_invalid"))
        return
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    draft["prompt"] = prompt
    await state.update_data(level_test_manual_draft=draft)
    if draft.get("type") == "MCQ":
        await state.set_state(AdminStates.level_test_manual_choices)
        await message.answer(t("admin_level_test.manual_choices_prompt"))
        return
    await state.set_state(AdminStates.level_test_manual_correct_answer)
    await message.answer(t("admin_level_test.manual_correct_answer_prompt"))


@router.message(AdminStates.level_test_manual_choices)
async def admin_level_test_manual_choices(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    choices = _split_variants(message.text or "")
    if len(choices) != 4:
        await message.answer(t("admin_level_test.manual_choices_invalid"))
        return
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    draft["choices"] = choices
    await state.update_data(level_test_manual_draft=draft)
    await state.set_state(AdminStates.level_test_manual_correct_answer)
    await message.answer(t("admin_level_test.manual_correct_answer_prompt"))


@router.message(AdminStates.level_test_manual_correct_answer)
async def admin_level_test_manual_correct_answer(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    answer = _normalize_spaces(message.text or "")
    if not answer:
        await message.answer(t("admin_level_test.manual_correct_answer_invalid"))
        return
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    if draft.get("type") == "MCQ":
        choices = list(draft.get("choices") or [])
        if answer.lower() not in {choice.lower() for choice in choices}:
            await message.answer(t("admin_level_test.manual_correct_answer_not_in_choices"))
            return
    draft["correct_answer"] = answer
    await state.update_data(level_test_manual_draft=draft)
    if draft.get("type") == "TYPING":
        await state.set_state(AdminStates.level_test_manual_accepted_answers)
        await message.answer(t("admin_level_test.manual_accepted_answers_prompt"))
        return
    await state.set_state(AdminStates.level_test_manual_explanation)
    await message.answer(t("admin_level_test.manual_explanation_prompt"))


@router.message(AdminStates.level_test_manual_accepted_answers)
async def admin_level_test_manual_accepted_answers(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    raw = (message.text or "").strip()
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    accepted_answers: list[str] = []
    if raw != "-":
        accepted_answers = _split_variants(raw)
    correct_answer = str(draft.get("correct_answer") or "")
    if correct_answer and correct_answer.lower() not in {item.lower() for item in accepted_answers}:
        accepted_answers.append(correct_answer)
    draft["accepted_answers"] = _dedupe_ordered(accepted_answers)
    await state.update_data(level_test_manual_draft=draft)
    await state.set_state(AdminStates.level_test_manual_explanation)
    await message.answer(t("admin_level_test.manual_explanation_prompt"))


@router.message(AdminStates.level_test_manual_explanation)
async def admin_level_test_manual_explanation(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    raw = (message.text or "").strip()
    explanation = None if raw == "-" else _normalize_spaces(raw)
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    draft["explanation"] = explanation
    await state.update_data(level_test_manual_draft=draft)
    await state.set_state(AdminStates.level_test_manual_is_active)
    await message.answer(t("admin_level_test.manual_is_active_prompt"))


@router.message(AdminStates.level_test_manual_is_active)
async def admin_level_test_manual_is_active(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    raw = (message.text or "").strip()
    is_active = _parse_bool_text(raw)
    if is_active is None:
        await message.answer(t("admin_level_test.manual_is_active_invalid"))
        return
    data = await state.get_data()
    draft = dict(data.get("level_test_manual_draft") or {})
    draft["is_active"] = is_active

    try:
        payload = _validate_question(draft, 1)
    except QuestionValidationError as exc:
        await message.answer(
            t(
                "admin_level_test.item_validation_error",
                index=exc.index,
                field=exc.field,
                reason=exc.message,
            ),
            reply_markup=admin_level_test_menu_kb(),
        )
        return

    inserted, skipped_duplicates = await _save_questions([payload])
    await state.clear()
    if inserted <= 0 and skipped_duplicates > 0:
        await message.answer(
            t("admin_level_test.manual_duplicate"),
            reply_markup=admin_level_test_menu_kb(),
        )
        return
    await message.answer(
        t("admin_level_test.manual_saved"),
        reply_markup=admin_level_test_menu_kb(),
    )
