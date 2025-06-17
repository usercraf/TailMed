import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import CommandStart

from key_file import TOKEN


bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart)
async def start(message: types.Message):
    await message.answer('Давай почнемо')



# Запуск процесса поллинга новых апдейтов
async def main():
    print('Bot run')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())