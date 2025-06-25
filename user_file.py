from aiogram import types, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from datetime import date, timedelta
import calendar
from key_file import cur, base
from log_file import logger

user_router = Router()

class RecordToDoctor(StatesGroup):
    name_doc = State()
    date_record = State()
    time_record = State()
    note = State()


def day_on_month():
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    last_day = date(today.year, today.month, days_in_month)

    # Генеруємо список рядків
    date_list = []
    current = today
    while current <= last_day:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return date_list

# функція для виборки часу який визначив тренер для приймання
def time_doctor(id_doc):
    time_trainers = cur.execute('''SELECT time_doc FROM users WHERE id=?''', (id_doc,)).fetchall()
    if time_trainers[0][0] is None:
        return ['Час не визначений тренером',]
    else:
        str_time = time_trainers[0][0].split(',')
        return str_time


@user_router.callback_query(F.data == 'record_to_doctor')
async def chose_doc(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    try:
        all_doctors = cur.execute("""SELECT id, full_name FROM users WHERE role=? AND is_verified=?""", ('doctor', 1)).fetchall()
        for item in all_doctors:
            id_doc, name = item
            builder.add(InlineKeyboardButton(text=name, callback_data=f'doctor_{id_doc}'))
        builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
        builder.adjust(1)
        await callback.message.answer(text='Виберіть зі списку лікарів', reply_markup=builder.as_markup())
        await state.set_state(RecordToDoctor.name_doc)
    except Exception as e:
        logger.error(f'Помилка у базі даних функції chose_doc {e}')
        builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
        builder.adjust(1)
        await callback.message.answer(text="⚠️ Помилка бази даних. "
                             "Спробуйте пізніше або зверніться до адміністратора.", reply_markup=builder.as_markup())


# Хендлер для обробки імені тренера до якого хоче записатись людина
@user_router.callback_query(F.data.startswith('doctor_'))
async def chose_date(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(id_doctor=callback.data.split('_')[1])
    builder = InlineKeyboardBuilder()
    for i in day_on_month():
        only_the_date = i.split('-')[2]
        builder.add(types.InlineKeyboardButton(text=only_the_date, callback_data=f'date_{i}'))
    builder.adjust(5)
    builder.row(types.InlineKeyboardButton(text='На головну 🏠', callback_data='Home'))  # Окрема кнопка
    await callback.message.edit_text('Виберіть дату яка Вам треба 🗓️', reply_markup=builder.as_markup())
    await state.set_state(RecordToDoctor.date_record)

# Хендлер для обробки дати на яку хоче записатись людина
@user_router.callback_query(F.data.startswith('date_'))
async def record_to_coach_time(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(date_record=callback.data.split('_')[1])
    state_data = await state.get_data()
    id_doctor = state_data['id_doctor']
    reserved_time = cur.execute("""SELECT visit_time FROM appointments WHERE doctor_id = ? AND visit_date = ?""",
                                (id_doctor, state_data['date_record'])).fetchall()
    reservet_time_list = [i[0] for i in reserved_time]
    time_training = [item for item in time_doctor(id_doctor) if item not in reservet_time_list]
    builder = InlineKeyboardBuilder()
    if not time_training:
        builder.row(types.InlineKeyboardButton(text='На головну 🏠', callback_data='Home'))  # Окрема кнопка
        await callback.message.edit_text(' 😢 На сьогодні у тренера всі години зайняті. Виберіть інший день', reply_markup=builder.as_markup())
        await state.clear()
        await callback.answer()
        return
    else:
        for item in time_training:
            builder.add(types.InlineKeyboardButton(text=item, callback_data=f'time_{item}'))
        builder.adjust(2)
        builder.row(types.InlineKeyboardButton(text='На головну 🏠', callback_data='Home'))  # Окрема кнопка
        await callback.message.edit_text('Вибери час який тобі треба ⏰', reply_markup=builder.as_markup())
        await state.set_state(RecordToDoctor.time_record)

# Хендлер для обробки часу на який хоче записатись людина
@user_router.callback_query(F.data.startswith('time_'))
async def record_note(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(time_record=callback.data.split('_')[1])
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='🏠 На головну', callback_data='Home'))
    await callback.message.edit_text('⬇️ Зазначте причину візиту в повідомленні .', reply_markup=builder.as_markup())
    await state.set_state(RecordToDoctor.note)


@user_router.message(RecordToDoctor.note)
async def save_appointment(message: types.Message, state: FSMContext):
    try:
        state_data = await state.get_data()
        id_doctor = state_data['id_doctor']
        date_record = state_data['date_record']
        time_record = state_data['time_record']
    except KeyError as e:
        logger.error(f"❌ Відсутній ключ у state_data: {e}")
        await message.answer("⚠️ Сталася помилка під час запису. Спробуйте ще раз.")
        await state.clear()
        return

    await state.clear()
    create_at = date.today()
    note = message.text.strip()

    logger.info(f"[APP] Дані запису: {id_doctor}, {date_record}, {time_record}, {create_at}, {note}")

    try:
        doc_data = cur.execute("""SELECT full_name, telegram_id FROM users WHERE id = ?""", (id_doctor,)).fetchone()
        if not doc_data:
            await message.answer("⚠️ Лікаря не знайдено. Запис не збережено.")
            return
        name_doc, id_telegram_doc = doc_data
    except Exception as e:
        logger.exception(f"❌ Помилка SELECT лікаря: {e}")
        await message.answer("⚠️ Помилка при пошуку лікаря. Повідомте адміністратора.")
        return

    try:
        cur.execute("""INSERT INTO appointments (doctor_id, visit_date, visit_time, created_at, note, confirmed) VALUES (?, ?, ?, ?, ?, ?)""",
            (id_doctor, date_record, time_record, create_at, note, 0))
        base.commit()
    except Exception as e:
        logger.exception(f"❌ Помилка при INSERT у appointments: {e}")
        await message.answer("⚠️ Не вдалося зберегти запис. Спробуйте пізніше.")
        return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text='На головну 🏠', callback_data='Home'))

    await message.answer(
        f'🥳 Ви успішно записались до лікаря {name_doc} {date_record} числа на {time_record}',
        reply_markup=builder.as_markup()
    )

    logger.info(
        f"Користувач {message.from_user.first_name} (ID: {message.from_user.id}) "
        f"записався до лікаря {name_doc} {date_record} числа на {time_record}"
    )

    try:
        if id_telegram_doc:
            await message.bot.send_message(chat_id=int(id_telegram_doc), text=f'📅 У Вас новий запис: {date_record} о {time_record}')
    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            logger.warning(f"❌ Лікар {name_doc} (ID: {id_telegram_doc}) — чат не знайдено.")
        else:
            logger.exception(f"⚠️ Telegram помилка для лікаря {id_telegram_doc}: {e}")
    except Exception as e:
        logger.exception(f"❌ Інша помилка при надсиланні повідомлення лікарю: {e}")
