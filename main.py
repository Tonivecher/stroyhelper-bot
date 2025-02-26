import logging
import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from ai_helper import AIHelper

# Состояния для калькуляторов площади и бюджета
class CalcStates(StatesGroup):
    waiting_for_length = State()
    waiting_for_width = State()
    waiting_for_material = State()
    waiting_for_budget = State()

# Добавляем новое состояние для AI чата
class AIStates(StatesGroup):
    waiting_for_question = State()

# Загрузка переменных окружения
load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    logging.critical("Ошибка: BOT_TOKEN не установлен! Выход.")
    exit(1)

# Логирование
logging.basicConfig(level=logging.INFO)

# Создание бота и диспетчера с FSM хранилищем
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Загрузка материалов из JSON
with open("materials.json", "r", encoding="utf-8") as file:
    materials = json.load(file)

# Главное меню
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Материалы")],
        [KeyboardButton(text="📐 Калькулятор площади")],
        [KeyboardButton(text="💰 Калькулятор бюджета")],
        [KeyboardButton(text="🤖 AI Помощник")]
    ],
    resize_keyboard=True
)

# Клавиатура категорий
def get_categories_keyboard():
    buttons = []
    for category in materials:
        buttons.append([InlineKeyboardButton(text=category, callback_data=f"category:{category}")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура подкатегорий
def get_subcategories_keyboard(category):
    buttons = []
    for subcategory in materials[category]:
        buttons.append([InlineKeyboardButton(text=subcategory, callback_data=f"subcategory:{category}:{subcategory}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_categories")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура брендов
def get_brands_keyboard(category, subcategory):
    buttons = []
    for brand in materials[category][subcategory]["brands"]:
        buttons.append([InlineKeyboardButton(text=brand, callback_data=f"brand:{category}:{subcategory}:{brand}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_subcategories:{category}")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("👋 Привет! Я StroyHelper бот. Выберите действие:", reply_markup=keyboard)

# Обработчик кнопки "Материалы"
@dp.message(F.text == "📋 Материалы")
async def materials_button(message: types.Message):
    await message.answer("📦 Выберите категорию материалов:", reply_markup=get_categories_keyboard())

# Калькулятор площади
@dp.message(F.text == "📐 Калькулятор площади")
async def area_calculator(message: types.Message, state: FSMContext):
    await message.answer("Введите длину помещения в метрах:")
    await state.set_state(CalcStates.waiting_for_length)

@dp.message(CalcStates.waiting_for_length)
async def process_length(message: types.Message, state: FSMContext):
    try:
        length = float(message.text)
        await state.update_data(length=length)
        await message.answer("Введите ширину помещения в метрах:")
        await state.set_state(CalcStates.waiting_for_width)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число!")

@dp.message(CalcStates.waiting_for_width)
async def process_width(message: types.Message, state: FSMContext):
    try:
        width = float(message.text)
        data = await state.get_data()
        length = data.get("length")
        area = length * width
        await message.answer(f"Площадь помещения: {area:.2f} м²")
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число!")

# Калькулятор бюджета
@dp.message(F.text == "💰 Калькулятор бюджета")
async def budget_calculator(message: types.Message, state: FSMContext):
    await message.answer("Введите ваш бюджет в рублях:")
    await state.set_state(CalcStates.waiting_for_budget)

@dp.message(CalcStates.waiting_for_budget)
async def process_budget(message: types.Message, state: FSMContext):
    try:
        budget = float(message.text)
        suggestions = []
        for category in materials:
            for subcategory in materials[category]:
                if "price" in materials[category][subcategory]:
                    price = materials[category][subcategory]["price"]
                    if price <= budget:
                        suggestions.append(f"{category} - {subcategory}: {price} руб.")

        if suggestions:
            response = "Доступные материалы в пределах вашего бюджета:\n\n" + "\n".join(suggestions)
        else:
            response = "Материалов в пределах вашего бюджета не найдено."

        await message.answer(response)
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число!")

# Обработчик выбора категории
@dp.callback_query(F.data.startswith("category:"))
async def category_callback(callback: types.CallbackQuery):
    category = callback.data.split(":")[1]
    await callback.answer()
    await callback.message.edit_text(
        f"📌 Категория: {category}\nВыберите подкатегорию:",
        reply_markup=get_subcategories_keyboard(category)
    )

# Обработчик выбора подкатегории
@dp.callback_query(F.data.startswith("subcategory:"))
async def subcategory_callback(callback: types.CallbackQuery):
    _, category, subcategory = callback.data.split(":")
    await callback.answer()
    await callback.message.edit_text(
        f"🔹 Подкатегория: {subcategory}\nВыберите бренд:",
        reply_markup=get_brands_keyboard(category, subcategory)
    )

# Обработчик выбора бренда
@dp.callback_query(F.data.startswith("brand:"))
async def brand_callback(callback: types.CallbackQuery):
    _, category, subcategory, brand = callback.data.split(":")
    info = materials[category][subcategory]
    price = info.get("price", "Нет данных")
    description = info.get("description", "Описание отсутствует")

    response = (
        f"✅ Выбрано:\n"
        f"<b>Категория:</b> {category}\n"
        f"<b>Подкатегория:</b> {subcategory}\n"
        f"<b>Бренд:</b> {brand}\n"
        f"<b>Цена:</b> {price} руб.\n\n"
        f"📦 Подробности: {description}"
    )
    await callback.answer()
    await callback.message.edit_text(response, parse_mode="HTML")

# Навигационные обработчики
@dp.callback_query(F.data == "back_to_categories")
async def back_to_categories_callback(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("📦 Выберите категорию материалов:", reply_markup=get_categories_keyboard())

@dp.callback_query(F.data.startswith("back_to_subcategories:"))
async def back_to_subcategories_callback(callback: types.CallbackQuery):
    _, category = callback.data.split(":")
    await callback.answer()
    await callback.message.edit_text(
        f"📌 Категория: {category}\nВыберите подкатегорию:",
        reply_markup=get_subcategories_keyboard(category)
    )

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("👋 Добро пожаловать! Выберите действие:", reply_markup=keyboard)

# Создаем экземпляр AI помощника
ai_helper = AIHelper()

# Добавляем обработчик для AI помощника
@dp.message(F.text == "🤖 AI Помощник")
async def ai_helper_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Задайте мне вопрос о строительных материалах, и я постараюсь помочь!\n"
        "Например:\n"
        "- Какой ламинат лучше выбрать для кухни?\n"
        "- Чем отличается керамогранит от керамической плитки?\n"
        "- Какая краска подойдет для ванной комнаты?"
    )
    await state.set_state(AIStates.waiting_for_question)

@dp.message(AIStates.waiting_for_question)
async def process_ai_question(message: types.Message, state: FSMContext):
    await message.answer("Думаю над ответом...")
    response = await ai_helper.get_response(message.text)
    await message.answer(response)
    await state.clear()


# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())