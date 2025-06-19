import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from key_file import TOKEN
from log_file import logger
from key_file import cur, base

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart)
async def start(message: types.Message):
    admin_id = cur.execute("""SELECT 1 FROM users WHERE telegram_id =?""", (message.from_user.id,)).fetchone()
    btn = {'add_doctor': 'Додати лікаря', 'del_doctor' : 'Видалити лікаря', 'verification' : 'Верифікація лікаря'}
    print(admin_id)
    if admin_id is not None:
        builder = InlineKeyboardBuilder()
        for key, value in btn.items():
            builder.add(types.InlineKeyboardButton(text=value, callback_data=key))
        builder.adjust(1)
        logger.info(f"Користувач {message.from_user.first_name} (ID: {message.from_user.id}) виконав вхід як адміністратор")
        await message.answer(f'{message.from_user.first_name} Давай почнемо', reply_markup=builder.as_markup())
    else:
        logger.info(
            f"Користувач {message.from_user.first_name} (ID: {message.from_user.id}) виконав вхід як користувач")
        await message.answer(f'Вітаю Вас {message.from_user.first_name}. Давай почнемо')


@dp.callback_query(F.data == 'Home')
async def home_btn(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    # record_to_coach = types.ReplyKeyboardMarkup(
    #     keyboard=[[types.KeyboardButton(text="Запис до тренера ⏺️")],
    #               [types.KeyboardButton(text="Я тренер 💪")],],
    #     resize_keyboard=True,
    #     one_time_keyboard=True,
    # )

    await callback.message.answer('Ви на початковій сторінці')

    await callback.answer()




# Запуск процесса поллинга новых апдейтов
async def main():
    print('Bot run')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())