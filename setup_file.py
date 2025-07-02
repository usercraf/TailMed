import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from key_file import TOKEN
from log_file import logger
from key_file import cur
from admin_file import admin_router
from user_file import user_router
from doctor_file import doctor_router
from test_file import test_router

bot = Bot(token=TOKEN)
dp = Dispatcher()


def get_admin_buttons():
    return {
        'add_doctor': '👨‍⚕️ Додати лікаря',
        'del_doctor': '🤷 Видалити лікаря',
    }

async def show_main_menu(user_id: int, user_name: str, reply_func, state: FSMContext):
    await state.clear()
    admin_id = cur.execute("""SELECT full_name, role, is_verified FROM users WHERE telegram_id =?""", (user_id,)).fetchone()
    builder = InlineKeyboardBuilder()
    if admin_id is not None:
        full_name, role, verified = admin_id
        if role == 'administrator':
            for key, value in get_admin_buttons().items():
                builder.add(InlineKeyboardButton(text=value, callback_data=key))
            builder.adjust(1)
            logger.info(f"Користувач {user_name} (ID: {user_id}) увійшов як адміністратор")
            await reply_func(f'👨🏻‍💼 {full_name}, давай почнемо', reply_markup=builder.as_markup())

        elif role == 'doctor' and verified:
            builder.add(InlineKeyboardButton(text='🩺 Меню лікаря', callback_data='doc_meny'))
            builder.adjust(1)
            logger.info(f"Користувач {user_name} (ID: {user_id}) увійшов як лікар")
            await reply_func(f'👨‍⚕️ Вітаю лікарю {full_name}, що будемо робити?', reply_markup=builder.as_markup())

    else:
        logger.info(f"Користувач {user_name} (ID: {user_id}) увійшов як користувач")
        builder.add(InlineKeyboardButton(text='✍🏻 Запис до лікаря', callback_data='record_to_doctor'))
        await reply_func(f'👋 Вітаю Вас {user_name}. Давай почнемо', reply_markup=builder.as_markup())


@dp.message(Command("start"))
async def handle_start(message: types.Message, state: FSMContext):
    await show_main_menu(
        user_id=message.from_user.id,
        user_name=message.from_user.first_name,
        reply_func=message.answer,
        state=state
    )

@dp.callback_query(F.data == 'Home')
async def handle_home(callback: types.CallbackQuery, state: FSMContext):
    await show_main_menu(
        user_id=callback.from_user.id,
        user_name=callback.from_user.first_name,
        reply_func=callback.message.answer,
        state=state
    )
    await callback.answer()

# Запуск процесса поллинга новых апдейтов
async def main():
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(doctor_router)
    dp.include_router(test_router)

    tryings = 0
    while True:
        try:
            print("🚀 Bot run")
            await dp.start_polling(bot)
        except TelegramNetworkError as e:
            tryings += 1
            logger.warning(f"⚠️ TelegramNetworkError: {e}. Спроба №{tryings}")
            await asyncio.sleep(1.0 * tryings)
        except Exception as e:
            logger.exception(f"💥 Невідома помилка polling: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())