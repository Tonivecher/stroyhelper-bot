import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Укажи свой токен бота
TOKEN = "YOUR_BOT_TOKEN"

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Создаём объект бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Клавиатура для выбора разделов
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📐 Рассчитать площадь")],
        [KeyboardButton(text="🔍 Выбрать материалы")],
        [KeyboardButton(text="💰 Оценить стоимость")],
        [KeyboardButton(text="📝 Заметки")],
    ],
    resize_keyboard=True
)

# Список материалов
materials = {
    "Гипсокартон": 3.5,
    "Штукатурка (гипсовая)": 2.0,
    "Штукатурка (цементная)": 2.5,
    "Керамическая плитка": 1.8,
    "Ламинат": 1.2,
    "Обои (виниловые)": 0.9,
    "ДСП / МДФ": 3.0,
    "Краска (латексная)": 1.5,
    "Минвата": 1.7
}

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я StroyHelper — помогу рассчитать материалы для ремонта.\nВыбери действие:",
        reply_markup=main_keyboard
    )

# Обработчик выбора расчёта площади
@dp.message(lambda message: message.text == "📐 Рассчитать площадь")
async def calculate_area(message: types.Message):
    await message.answer("Введите ширину и длину комнаты через пробел (например: 5.2 4.8):")

    @dp.message()
    async def get_dimensions(msg: types.Message):
        try:
            width, length = map(float, msg.text.split())
            area = width * length
            await msg.answer(f"Площадь комнаты: {area:.2f} м²")
        except ValueError:
            await msg.answer("Некорректный ввод. Введите два числа через пробел.")

# Обработчик выбора материалов
@dp.message(lambda message: message.text == "🔍 Выбрать материалы")
async def list_materials(message: types.Message):
    text = "📋 Доступные материалы:\n"
    for mat, price in materials.items():
        text += f"• {mat} — {price} руб./м²\n"
    await message.answer(text)

# Обработчик оценки стоимости
@dp.message(lambda message: message.text == "💰 Оценить стоимость")
async def estimate_cost(message: types.Message):
    await message.answer("Введите название материала и площадь через пробел (например: Ламинат 25):")

    @dp.message()
    async def get_cost(msg: types.Message):
        try:
            material, area = msg.text.rsplit(maxsplit=1)
            area = float(area)
            if material in materials:
                cost = materials[material] * area
                await msg.answer(f"Примерная стоимость: {cost:.2f} руб.")
            else:
                await msg.answer("Материал не найден. Проверьте название.")
        except ValueError:
            await msg.answer("Некорректный ввод. Введите название материала и площадь.")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())