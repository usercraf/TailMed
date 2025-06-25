from aiogram import types, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from key_file import cur, base
from log_file import logger
from key_file import all_time

doctor_router = Router()

class TimeDoctor(StatesGroup):
    check_time = State()


def get_doctor_buttons():
    return {
        'set_time': '⏳ Визначити час прийому',
    }

def doc_name(name):
    try:
        return cur.execute("""SELECT full_name FROM users WHERE telegram_id=?""", (name,)).fetchone()[0]

    except Exception as e:
        logger.error(f'❌ Помилка {e} функція doc_name file doctor_file.py не отримано ім\ʼя лікаря ')
        return 'Помилка'


@doctor_router.callback_query(F.data == 'doc_meny')
async def meny_doctor(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for key, value in get_doctor_buttons().items():
        builder.add(InlineKeyboardButton(text=value, callback_data=key))
    await callback.message.answer(f'😀 Вітаємо {doc_name(callback.from_user.id)} виберіть пункт меню.', reply_markup=builder.as_markup())


@doctor_router.callback_query(F.data == 'set_time')
async def choose_hours(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(id_trainer=callback.from_user.id, selected_hours=[])

    builder = InlineKeyboardBuilder()
    for t in all_time:
        builder.add(types.InlineKeyboardButton(text=f'❌ {t}', callback_data=f'hours_{t.replace(":", "")}'))
    builder.add(types.InlineKeyboardButton(text='🏠 На головну ', callback_data='Home'))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text='✅ Зберегти', callback_data='save_hours'))

    await callback.message.answer('⏰ Вибери години прийому:', reply_markup=builder.as_markup())
    await state.set_state(TimeDoctor.check_time)


@doctor_router.callback_query(TimeDoctor.check_time, F.data.startswith('hours_'))
async def toggle_hour(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_hours", [])
    time_val = callback.data.removeprefix('hours_')
    time_val = f"{time_val[:2]}:{time_val[2:]}"

    if time_val in selected:
        selected.remove(time_val)
    else:
        selected.append(time_val)
    await state.update_data(selected_hours=selected)

    # Оновити клавіатуру
    builder = InlineKeyboardBuilder()
    for t in all_time:
        status = '✅' if t in selected else '❌'
        builder.add(types.InlineKeyboardButton(text=f'{status} {t}', callback_data=f'hours_{t.replace(":", "")}'))
    builder.add(types.InlineKeyboardButton(text='🏠 На головну', callback_data='Home'))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text='✅ Зберегти', callback_data='save_hours'))

    try:
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    except TelegramBadRequest:
        pass
    await callback.answer()


@doctor_router.callback_query(TimeDoctor.check_time, F.data == 'save_hours')
async def save_selected_hours(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trainer_id = data['id_trainer']
    selected = data.get("selected_hours", [])
    times_string = ','.join(selected)
    builder = InlineKeyboardBuilder()
    try:
        cur.execute("UPDATE users SET time_doc = ? WHERE telegram_id = ?", (times_string, trainer_id))
        base.commit()
        builder.add(types.InlineKeyboardButton(text='🏠 На головну', callback_data='Home'))
        await callback.message.edit_text(f"✅ Години збережено: {', '.join(selected)}", reply_markup=builder.as_markup())
        await state.clear()
        await callback.answer()
    except Exception as e:
        logger.error(f'Помилка при оновленні часу прийому лікаря в функції save_selected_hours {e}')
        builder.add(types.InlineKeyboardButton(text='🏠 На головну', callback_data='Home'))
        await callback.message.edit_text("⚠️ Помилка бази даних. "
                             "Спробуйте пізніше або зверніться до адміністратора.", reply_markup=builder.as_markup())
        await state.clear()
        await callback.answer()
