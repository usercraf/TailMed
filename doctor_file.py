from aiogram import types, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

from key_file import cur, base
from log_file import logger
from key_file import all_time

doctor_router = Router()

class TimeDoctor(StatesGroup):
    check_time = State()

class AddPets(StatesGroup):
    pets_name = State()
    species = State()
    bread = State()
    owner_name = State()
    owner_phone = State()

def get_doctor_buttons():
    return {
        'set_time': '⏳ Визначити час прийому',
        'add_pets': '🐶 Додати тваринку'
    }

def doc_name(name):
    try:
        return cur.execute("""SELECT full_name FROM users WHERE telegram_id=?""", (name,)).fetchone()[0]

    except Exception as e:
        logger.error(f'❌ Помилка {e} функція doc_name file doctor_file.py не отримано ім\ʼя лікаря ')
        return 'Помилка'

def get_home_builder() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
    builder.adjust(1)
    return builder

def check_msg(func, msg):
    if len(msg) > 0:
        return True
    else:
        logger.error(f'Введені дані порожні у функції {func}')
        return False

def is_valid_phone_number(phone: str) -> bool:
    return bool(re.fullmatch(r"0\d{9}", phone))

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


@doctor_router.callback_query(F.data == 'add_pets')
async def create_a_record(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text('⬇️ Введіть кличку тваринки.', reply_markup=get_home_builder().as_markup())
    await state.set_state(AddPets.pets_name)


@doctor_router.message(AddPets.pets_name)
async def record_pets_name(message: types.Message, state: FSMContext):
    if check_msg(record_pets_name, message.text.strip()):
        await state.update_data(name_pets=message.text.strip())
        await message.answer('Введіть вид тваринки (🐈 🐕 🐍 🐎 🦜)', reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.species)
    else:
        logger.error(f'Лікар {message.from_user.id} не ввів кличку тварини')
        await message.answer('❌ Ви відправили порожнє повідомлення спробуйте ще раз.', reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.pets_name)


@doctor_router.message(AddPets.species)
async def record_species(message: types.Message, state: FSMContext):
    if check_msg(record_species, message.text.strip()):
        await state.update_data(species=message.text.strip())
        await message.answer('⬇️ Введіть породу тваринки', reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.bread)
    else:
        logger.error(f'Лікар {message.from_user.id} не ввів вид тварини')
        await message.answer('❌ Ви відправили порожнє повідомлення спробуйте ще раз.', reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.species)


@doctor_router.message(AddPets.bread)
async def record_bread(message: types.Message, state: FSMContext):
    if check_msg(record_bread, message.text.strip()):
        await state.update_data(breed=message.text.strip())
        await message.answer('⬇️ Введіть ім\ʼя господаря.', reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.owner_name)
    else:
        logger.error(f'Лікар {message.from_user.id} не ввів породу тварини')
        await message.answer('❌ Ви відправили порожнє повідомлення спробуйте ще раз.', reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.bread)

@doctor_router.message(AddPets.owner_name)
async def record_bread(message: types.Message, state: FSMContext):
    if check_msg(record_bread, message.text.strip()):
        await state.update_data(owner_name=message.text.strip())
        await message.answer('⬇️ Введіть номер телефону господаря у форматі 0950000000.', reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.owner_phone)
    else:
        logger.error(f'Лікар {message.from_user.id} не ім\ʼя господаря тварини')
        await message.answer('❌ Ви відправили порожнє повідомлення спробуйте ще раз.', reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.owner_name)

@doctor_router.message(AddPets.owner_phone)
async def record_to_table(message: types.Message, state: FSMContext):
    if is_valid_phone_number(message.text.strip()):
        data_pets = await state.get_data()
        pets_name = data_pets['name_pets']
        pets_species = data_pets['species']
        pets_breed = data_pets['breed']
        owner_name = data_pets['owner_name']
        owner_phone = message.text.strip()
        try:
            result = cur.execute("""SELECT 1 FROM animals WHERE owner_phone=? AND name_pets=?""", (owner_phone, pets_name)).fetchone()
            if result is None:
                cur.execute("""INSERT INTO animals (name_pets, species, breed, owner_name, owner_phone)
                    VALUES (?, ?, ?, ?, ?)""", (pets_name, pets_species, pets_breed, owner_name, owner_phone))

                base.commit()
                logger.info('🐈 Додано тварину до бази даних')
                await message.answer(f'{pets_name} додано до бази даних', reply_markup=get_home_builder().as_markup())
                await state.clear()
            else:
                logger.warning('Така кличка у такого господаря вже існує')
                await message.answer('🐾 Тваринка вже зареєстрована за даним господарем.',
                                     reply_markup=get_home_builder().as_markup())
                await state.clear()
        except Exception as e:
            logger.error(f'Виникла проблема під час перевірки наявності тваринки у базі даних функція record_to_table {e}')
            await message.answer('❌ Виникла помилка при внесенні даних. Спробуйте пізніше або зверніться до адміністратора',
                                 reply_markup=get_home_builder().as_markup())
            await message.answer('❌ Введені дані очищено спробуйте ще раз або зверніться до адміністратора',
                                 reply_markup=get_home_builder().as_markup())
            await state.clear()
    else:
        logger.error(f'Користувач {message.from_user.first_name} ввів номер телефону у не вірному форматі')
        await message.answer('❌ Номер телефону введено не у визначеному форматі. Перевірте та введіть ще раз.',
                             reply_markup=get_home_builder().as_markup())
        await state.set_state(AddPets.owner_phone)

