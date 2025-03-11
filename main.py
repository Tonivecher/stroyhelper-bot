import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Укажи свой токен бота
TOKEN = "YOUR_BOT_TOKEN"

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Создание класса состояний для FSM
class BotStates(StatesGroup):
    waiting_for_dimensions = State()
    waiting_for_cost_input = State()
    waiting_for_note = State()

# Создаём объект бота и диспетчера с хранилищем состояний
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Клавиатура для выбора разделов
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📐 Рассчитать площадь")],
        [KeyboardButton(text="🔍 Выбрать материалы")],
        [KeyboardButton(text="💰 Оценить стоимость")],
        [KeyboardButton(text="📝 Заметки")],
        [KeyboardButton(text="🏠 Главное меню")]
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

# Обработчик команды /start и возврата в главное меню
@dp.message(Command("start"))
@dp.message(lambda message: message.text == "🏠 Главное меню")
async def cmd_start(message: types.Message, state: FSMContext):
    # Сбрасываем состояние при возврате в главное меню
    await state.clear()
    
    await message.answer(
        "Привет! Я StroyHelper — помогу рассчитать материалы для ремонта.\nВыбери действие:",
        reply_markup=main_keyboard
    )

# Обработчик выбора расчёта площади
@dp.message(lambda message: message.text == "📐 Рассчитать площадь")
async def calculate_area(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_dimensions)
    await message.answer("Введите ширину и длину комнаты через пробел (например: 5.2 4.8):")

# Обработчик для получения размеров комнаты
@dp.message(StateFilter(BotStates.waiting_for_dimensions))
async def get_dimensions(message: types.Message, state: FSMContext):
    try:
        width, length = map(float, message.text.split())
        area = width * length
        await message.answer(f"Площадь комнаты: {area:.2f} м²", reply_markup=main_keyboard)
        # Сбрасываем состояние
        await state.clear()
    except ValueError:
        await message.answer("Некорректный ввод. Введите два числа через пробел.")

# Обработчик выбора материалов
@dp.message(lambda message: message.text == "🔍 Выбрать материалы")
async def list_materials(message: types.Message, state: FSMContext):
    # Сбрасываем состояние при просмотре материалов
    await state.clear()
    
    text = "📋 Доступные материалы:\n"
    for mat, price in materials.items():
        text += f"• {mat} — {price} руб./м²\n"
    await message.answer(text, reply_markup=main_keyboard)

# Обработчик оценки стоимости
@dp.message(lambda message: message.text == "💰 Оценить стоимость")
async def estimate_cost(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_cost_input)
    
    text = "📋 Доступные материалы:\n"
    for mat in materials.keys():
        text += f"• {mat}\n"
    
    await message.answer(
        text + "\nВведите название материала и площадь через пробел (например: Ламинат 25):"
    )

# Обработчик для получения стоимости
@dp.message(StateFilter(BotStates.waiting_for_cost_input))
async def get_cost(message: types.Message, state: FSMContext):
    try:
        material, area = message.text.rsplit(maxsplit=1)
        area = float(area)
        
        if material in materials:
            cost = materials[material] * area
            await message.answer(f"Примерная стоимость: {cost:.2f} руб.", reply_markup=main_keyboard)
            # Сбрасываем состояние
            await state.clear()
        else:
            await message.answer("Материал не найден. Проверьте название.")
    except ValueError:
        await message.answer("Некорректный ввод. Введите название материала и площадь.")

# Обработчик для заметок
@dp.message(lambda message: message.text == "📝 Заметки")
async def handle_notes(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_note)
    await message.answer("Введите вашу заметку для проекта ремонта:")

# Обработчик для получения заметки
@dp.message(StateFilter(BotStates.waiting_for_note))
async def get_note(message: types.Message, state: FSMContext):
    note = message.text
    
    # Здесь можно добавить сохранение заметки в базу данных
    
    await message.answer(f"Заметка сохранена:\n\n{note}", reply_markup=main_keyboard)
    # Сбрасываем состояние
    await state.clear()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())