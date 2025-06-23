import random

from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup



from key_file import cur, base
from log_file import logger

admin_router = Router()

class Verification_doc(StatesGroup):
    verific_doc = State()

class AddDoctor(StatesGroup):
    name_doc = State()
    role_doc = State()

class DellDoctor(StatesGroup):
    code_admin = State()
    coode_doc = State()

def generate_unique_code():
    while True:
        code = "{:06d}".format(random.randint(100000, 999999))
        exists = cur.execute(
            "SELECT 1 FROM users WHERE code = ?",
            (code,)
        ).fetchone()
        if not exists:
            return int(code)


@admin_router.message(Command('verification'))
async def verification_doctor(message: types.Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.first_name} (ID: {message.from_user.id}) хоче пройти верифікацію лікаря")
    await message.answer('⬇️ Надійшліть свій код для верифікації')
    await state.set_state(Verification_doc.verific_doc)


@admin_router.message(Verification_doc.verific_doc)
async def verification_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
    try:
        secret_code = cur.execute("""SELECT 1 FROM users WHERE code=?""", (code,)).fetchone()
        if secret_code is None:
            logger.warning(
                f"Користувач {message.from_user.first_name} (ID: {message.from_user.id}) ввів непривильний пароль до верифікації лікаря")
            await message.answer('❌ Ви ввели певірний код. Спробуйте ще раз')
            await state.set_state(Verification_doc.verific_doc)
        else:
            logger.info(
                f"Користувач {message.from_user.first_name} (ID: {message.from_user.id}) пройшов верифікацію лікаря")

            cur.execute("""UPDATE users SET is_verified=?, telegram_id=? WHERE code=?""", (1, int(message.from_user.id), code))
            base.commit()
            await state.clear()
            await message.answer('🥳 Вітаю верифікація пройдена')
    except Exception as e:
        logger.error(f"[DB] Помилка під час SELECT: {e} функція - verification_code")
        await message.answer("⚠️ Помилка бази даних. "
                             "Спробуйте пізніше або зверніться до адміністратора.", reply_markup=builder.as_markup())
        await state.clear()


@admin_router.callback_query(F.data == 'add_doctor')
async def start_add_doc(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
    await callback.message.answer('⬇️ Введіть Ім\ʼя та прізвище лікаря', reply_markup=builder.as_markup())
    await state.set_state(AddDoctor.name_doc)


@admin_router.message(AddDoctor.name_doc)
async def get_name_doc(message: types.Message, state: FSMContext):
    await state.update_data(name_doc=message.text.strip())
    keyboard_doc = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨🏻‍💼 Адміністратор", callback_data="role:administrator"),
             InlineKeyboardButton(text="👨‍⚕️ Лікар", callback_data="role:doctor")],
            [InlineKeyboardButton(text="🏠 На головну", callback_data="Home")]
        ]
    )
    await message.answer(text='Вибери роль', reply_markup=keyboard_doc)
    await state.set_state(AddDoctor.role_doc)


@admin_router.callback_query(F.data.in_(['role:administrator', 'role:doctor']))
async def get_role_doc(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name_doc = data.get('name_doc')
    role_doc = callback.data.split(':')[1]
    code = generate_unique_code()

    cur.execute("""INSERT INTO users (full_name, role, code, is_verified) VALUES(?,?,?,?)""", (name_doc, role_doc, code, 0))
    base.commit()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
    await state.clear()
    await callback.message.answer(f'✅ Лікаря додано. Ось його код для доступу до кабінету {code}', reply_markup=builder.as_markup())


@admin_router.callback_query(F.data == 'del_doctor')
async def get_admin_key(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
    await callback.message.answer('⬇️ Для видалення лікаря введіть ключ Адміністратора',
                                  reply_markup=builder.as_markup())
    await state.set_state(DellDoctor.code_admin)

@admin_router.message(DellDoctor.code_admin)
async def get_doc_key(message: types.Message, state: FSMContext):
    code_admin = message.text.upper()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
    try:
        chek_code = cur.execute("""SELECT role FROM users WHERE code=?""", (code_admin,)).fetchone()
        if chek_code is not None and chek_code[0] == 'administrator':
            await message.answer('⬇️ Введіть код лікаря.', reply_markup=builder.as_markup())
            await state.set_state(DellDoctor.coode_doc)
        else:
            await message.answer('❌ Код введено невірно спробуйте ще раз', reply_markup=builder.as_markup())
            await state.set_state(DellDoctor.code_admin)

    except Exception as e:
        logger.error(f"[DB] Помилка під час SELECT: {e} функція - get_doc_key")
        await message.answer("⚠️ Помилка бази даних. "
                             "Спробуйте пізніше або зверніться до адміністратора.", reply_markup=builder.as_markup())
        await state.clear()

@admin_router.message(DellDoctor.coode_doc)
async def dell_doc(message: types.Message, state: FSMContext):
    code_doc = message.text
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🏠 На головну", callback_data="Home"))
    try:
        check_doc = cur.execute("""SELECT 1 FROM users WHERE code=?""", (code_doc,)).fetchone()
        if check_doc is not None:
            cur.execute("""DELETE FROM users WHERE code=?""", (code_doc,))
            base.commit()
            await message.answer('✅ Лікаря видалено.', reply_markup=builder.as_markup())
            await state.clear()
        else:
            await message.answer('❌ Лікаря не найдено в базі даних спробуйте ввести код ще раз.',
                                 reply_markup=builder.as_markup())
            await state.set_state(DellDoctor.coode_doc)

    except Exception as e:
        logger.error(f"[DB] Помилка під час SELECT: {e} функція - dell_doc")
        await message.answer("⚠️ Помилка бази даних. "
                             "Спробуйте пізніше або зверніться до адміністратора.", reply_markup=builder.as_markup())
        await state.clear()

