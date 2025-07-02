from datetime import datetime

from aiogram import types, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

from key_file import cur, base
from log_file import logger
from key_file import all_time
from doc_form import generate_tailmed_docx

doctor_router = Router()

class TimeDoctor(StatesGroup):
    check_time = State()

class AddPets(StatesGroup):
    pets_name = State()
    species = State()
    bread = State()
    owner_name = State()
    owner_phone = State()

class CheckPets(StatesGroup):
    check_pets = State()

class MedicalRecording(StatesGroup):
    get_owner_number = State()
    use_pets = State()
    get_category = State()
    get_date = State()
    get_title = State()
    get_details = State()

def get_doctor_buttons():
    return {
        'set_time': '⏳ Визначити час прийому',
        'add_pets': '🐶 Додати тваринку',
        'check_pets': '✅ Перевірити тваринку',
        'medical_record': '🧬 Медичний запис'
    }

def category_record():
    return  {"review": "огляд",
             "analysis": "аналіз",
             "procedure": "процедура",
             "recommendation": "рекомендація"}

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

def is_valid_phone_number(phone: str) -> bool:
    return bool(re.fullmatch(r"0\d{9}", phone))

@doctor_router.callback_query(F.data == 'doc_meny')
async def meny_doctor(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for key, value in get_doctor_buttons().items():
        builder.add(InlineKeyboardButton(text=value, callback_data=key))
    builder.adjust(1)
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
    await state.update_data(name_pets=message.text.strip())
    await message.answer('Введіть вид тваринки (🐈 🐕 🐍 🐎 🦜)', reply_markup=get_home_builder().as_markup())
    await state.set_state(AddPets.species)


@doctor_router.message(AddPets.species)
async def record_species(message: types.Message, state: FSMContext):
    await state.update_data(species=message.text.strip())
    await message.answer('⬇️ Введіть породу тваринки', reply_markup=get_home_builder().as_markup())
    await state.set_state(AddPets.bread)


@doctor_router.message(AddPets.bread)
async def record_bread(message: types.Message, state: FSMContext):
    await state.update_data(breed=message.text.strip())
    await message.answer('⬇️ Введіть ім\ʼя господаря.', reply_markup=get_home_builder().as_markup())
    await state.set_state(AddPets.owner_name)


@doctor_router.message(AddPets.owner_name)
async def record_bread(message: types.Message, state: FSMContext):
    await state.update_data(owner_name=message.text.strip())
    await message.answer('⬇️ Введіть номер телефону господаря у форматі 0950000000.', reply_markup=get_home_builder().as_markup())
    await state.set_state(AddPets.owner_phone)


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


@doctor_router.callback_query(F.data == 'check_pets')
async def get_number_owner(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text('⬇️ Введіть номер телефону', reply_markup=get_home_builder().as_markup())
    await state.set_state(CheckPets.check_pets)


@doctor_router.message(CheckPets.check_pets)
async def owner_pets(message: types.Message, state: FSMContext):
    if is_valid_phone_number(message.text.strip()):
        try:
            date_pets = cur.execute("""SELECT * FROM animals WHERE owner_phone=?""", (message.text.strip(),)).fetchall()
            for item in date_pets:
                id_pets, name_pets, species, breed, owner_name, owner_phone = item
                await message.answer(f'📣 Данні по тваринці: '
                                     f'\n1️⃣ID Номер-{id_pets}'
                                     f'\n2️⃣Імʼя тваринки-{name_pets}'
                                     f'\n3️⃣Вид-{species}'
                                     f'\n4️⃣Порода-{breed}'
                                     f'\n5️⃣Імʼя власника-{owner_name}'
                                     f'\n6️⃣Телефон власника-{owner_phone}.')
            logger.info('Данні по тваринці отримані.')
            await message.answer('Виберіть подільші діі', reply_markup=get_home_builder().as_markup())
            await state.clear()
        except Exception as e:
            logger.error(
                f'Виникла проблема під час перевірки наявності тваринки у базі даних функція owner_pets {e}')
            await message.answer(
                '❌ Виникла помилка. Спробуйте пізніше або зверніться до адміністратора',
                reply_markup=get_home_builder().as_markup())
            await message.answer('❌ Введені дані очищено спробуйте ще раз або зверніться до адміністратора',
                                 reply_markup=get_home_builder().as_markup())
            await state.clear()
    else:
        logger.info('Жодного запису не знайдено')
        await message.answer('🙊 Жодного запису не знайдено', reply_markup=get_home_builder().as_markup())
        await state.clear()


@doctor_router.callback_query(F.data == 'medical_record')
async def medical_recording(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text('⬇️ Для внесення медичних рекомендацій введіть номер телефону власника.',
                                     reply_markup=get_home_builder().as_markup())
    await state.set_state(MedicalRecording.get_owner_number)

@doctor_router.message(MedicalRecording.get_owner_number)
async def check_owner_number(message: types.Message, state: FSMContext):
    if is_valid_phone_number(message.text.strip()):
        await state.update_data(owner_phone=message.text.strip())
        try:
            date_pets = cur.execute("""SELECT * FROM animals WHERE owner_phone=?""", (message.text.strip(),)).fetchall()
            for item in date_pets:
                builder = InlineKeyboardBuilder()
                id_pets, name_pets, species, breed, owner_name, owner_phone = item
                builder.add(types.InlineKeyboardButton(text='Вибрати', callback_data=f'mr_{id_pets}'))
                await message.answer(f'📣 Данні по тваринці: '
                                     f'\n1️⃣ID Номер-{id_pets}'
                                     f'\n2️⃣Імʼя тваринки-{name_pets}'
                                     f'\n3️⃣Вид-{species}'
                                     f'\n4️⃣Порода-{breed}'
                                     f'\n5️⃣Імʼя власника-{owner_name}'
                                     f'\n6️⃣Телефон власника-{owner_phone}.', reply_markup=builder.as_markup())

            logger.info('Данні по тваринці отримані.')
            await state.set_state(MedicalRecording.use_pets)
        except Exception as e:
            logger.error(
                f'Виникла проблема під час перевірки наявності тваринки у базі даних функція owner_pets {e}')
            await message.answer(
                '❌ Виникла помилка. Спробуйте пізніше або зверніться до адміністратора',
                reply_markup=get_home_builder().as_markup())
            await message.answer('❌ Введені дані очищено спробуйте ще раз або зверніться до адміністратора',
                                 reply_markup=get_home_builder().as_markup())
            await state.clear()
    else:
        logger.info('Жодного запису не знайдено')
        await message.answer('🙊 Жодного запису не знайдено', reply_markup=get_home_builder().as_markup())
        await state.clear()


@doctor_router.callback_query(MedicalRecording.use_pets, F.data.startswith('mr_'))
async def use_pets(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(animal_id=callback.data.split('_')[1])
    builder = InlineKeyboardBuilder()
    for key, value in category_record().items():
        builder.add(types.InlineKeyboardButton(text=value, callback_data=key))
    builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
    builder.adjust(1)
    await callback.message.answer('⬇️ Виберіть категорію', reply_markup=builder.as_markup())
    await state.set_state(MedicalRecording.get_category)


@doctor_router.callback_query(MedicalRecording.get_category, F.data.in_(category_record().keys()))
async def title_record(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(category=category_record()[callback.data])
    if category_record()[callback.data] in ('аналіз', 'процедура'):
        await callback.message.answer('⬇️ Введіть дату прийому аналізів або проведення процедури.')
        await state.set_state(MedicalRecording.get_date)
    else:
        await callback.message.answer('⬇️ Ведіть Назву/тему запису, наприклад - УЗД черевної порожнини',
                                      reply_markup=get_home_builder().as_markup())
        await state.set_state(MedicalRecording.get_title)


@doctor_router.message(MedicalRecording.get_date)
async def get_date(message: types.Message, state: FSMContext):
    logger.info('Виконано вхід до роутеру з введенням дати аналізів чи процедури.')
    await state.update_data(date=message.text)
    await message.answer('⬇️ Ведіть Назву/тему запису, наприклад - УЗД черевної порожнини',
                                  reply_markup=get_home_builder().as_markup())
    await state.set_state(MedicalRecording.get_title)


@doctor_router.message(MedicalRecording.get_title)
async def title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text='Далі', callback_data='Next'))
    await message.answer('⬇️ Введіть Опис результатів / що було зроблено або натисніть Далі', reply_markup=builder.as_markup())
    await state.set_state(MedicalRecording.get_details)


@doctor_router.message(MedicalRecording.get_details)
async def details_msg(message: types.Message, state: FSMContext):
    logger.info('Лікарем внесенні деталі процедури спрацювала функція details_msg')
    data_mr = await state.get_data()
    if data_mr.get('date'):
        date = data_mr.get('date')
    else:
        date = 'Не вказано лікарем'
    owner_phone = data_mr.get('owner_phone')
    pets_name, species, breed, owner_name = cur.execute("""SELECT name_pets, species, breed, owner_name FROM animals WHERE id_pets = ?""",
                              (data_mr.get('animal_id'),)).fetchone()

    animal_id = data_mr.get('animal_id')
    category = data_mr.get('category')
    tittle = data_mr.get('title')
    details = message.text
    doctor_name = cur.execute("""SELECT full_name FROM users WHERE telegram_id = ?""", (message.from_user.id,)).fetchone()[0]
    now = datetime.now()
    create_at = now.strftime("%Y-%m-%d %H:%M")
    try:
        cur.execute("""INSERT INTO medical_records (animal_id, date, category, title, details, doc_name, created_at) 
                            VALUES (?,?,?,?,?,?,?)""", (animal_id, date, category, tittle, details, doctor_name, create_at))
        base.commit()
        logger.info(f'Данні занесені в базу даних лікарем {doctor_name} o {create_at}')
        await message.answer('Запис Внесено до бази даних.\nНадсилаю файл.', reply_markup=get_home_builder().as_markup())


        generate_tailmed_docx(data_mr, "output/report_tailmed.docx",
                              doctor_name, details, category, pets_name, species, breed, owner_name, owner_phone, create_at)

        file = FSInputFile("output/report_tailmed.docx")
        await message.answer_document(file, caption="📄 Ваш TailMed звіт у форматі DOCX")

        await state.clear()
    except Exception as e:
        logger.warning(f'Відбулась проблема з записом до бази даних {e} функція details_msg')
        await message.answer('❌ Відбулась помилка зверніться до адміністратора', reply_markup=get_home_builder().as_markup())
        await state.clear()


@doctor_router.callback_query(MedicalRecording.get_details, F.data == 'Next')
async def details_callback(callback: types.CallbackQuery, state: FSMContext):
    data_mr = await state.get_data()
    if data_mr.get('date'):
        date = data_mr.get('date')
    else:
        date = 'Не вказано лікарем'
    owner_phone = data_mr.get('owner_phone')
    animal_id = data_mr.get('animal_id')
    category = data_mr.get('category')
    tittle = data_mr.get('title')
    details = 'Лікар не вніс деталі'
    doctor_name = cur.execute("""SELECT full_name FROM users WHERE telegram_id = ?""", (callback.from_user.id,)).fetchone()[0]
    now = datetime.now()
    create_at = now.strftime("%Y-%m-%d %H:%M")
    try:
        cur.execute("""INSERT INTO medical_records (animal_id, date, category, title, details, doc_name, created_at) 
                            VALUES (?,?,?,?,?,?,?)""", (animal_id, date, category, tittle, details, doctor_name, create_at))
        base.commit()
        logger.info(f'Данні занесені в базу даних лікарем {doctor_name} o {create_at}')
        await callback.message.answer('Запис Внесено до бази даних.\nНадсилаю файл.',
                                      reply_markup=get_home_builder().as_markup())
        await state.clear()
    except Exception as e:
        logger.warning(f'Відбулась проблема з записом до бази даних {e} функція details_msg')
        await callback.message.answer('❌ Відбулась помилка зверніться до адміністратора.',
                                      reply_markup=get_home_builder().as_markup())
        await state.clear()





