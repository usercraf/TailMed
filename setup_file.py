import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import CommandStart, Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from key_file import TOKEN
from log_file import logger
from key_file import cur, base
from admin_file import admin_router

bot = Bot(token=TOKEN)
dp = Dispatcher()


def get_admin_buttons():
    return {
        'add_doctor': '👨‍⚕️ Додати лікаря',
        'del_doctor': '🤷 Видалити лікаря',
    }

async def show_main_menu(user_id: int, user_name: str, reply_func):
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
            builder.add(InlineKeyboardButton(text='🩺 Меню лікаря', callback_data='doc_'))
            builder.adjust(1)
            logger.info(f"Користувач {user_name} (ID: {user_id}) увійшов як лікар")
            await reply_func(f'👨‍⚕️ Вітаю лікарю {full_name}, що будемо робити?', reply_markup=builder.as_markup())

    else:
        logger.info(f"Користувач {user_name} (ID: {user_id}) увійшов як користувач")
        await reply_func(f'👋 Вітаю Вас {user_name}. Давай почнемо')


@dp.message(Command("start"))
async def handle_start(message: types.Message):
    await show_main_menu(
        user_id=message.from_user.id,
        user_name=message.from_user.first_name,
        reply_func=message.answer
    )

@dp.callback_query(F.data == 'Home')
async def handle_home(callback: types.CallbackQuery):
    await show_main_menu(
        user_id=callback.from_user.id,
        user_name=callback.from_user.first_name,
        reply_func=callback.message.answer
    )
    await callback.answer()

# Запуск процесса поллинга новых апдейтов
async def main():
    dp.include_router(admin_router)
    print('Bot run')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())