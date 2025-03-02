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
from material_calculator import MaterialCalculation, MaterialUnit
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Union
import shopping_list

# Типы помещений
class RoomType(Enum):
    KITCHEN = "Кухня"
    BEDROOM = "Спальня"
    LIVING_ROOM = "Гостиная"
    BATHROOM = "Ванная"
    CUSTOM = "Другое"

# Формы помещений
class RoomShape(Enum):
    RECTANGULAR = "Прямоугольная"
    SQUARE = "Квадратная"
    CIRCULAR = "Круглая"
    CUSTOM = "Нестандартная"

# Данные о помещении
@dataclass
class RoomData:
    room_type: RoomType
    shape: RoomShape
    length: Optional[float] = None
    width: Optional[float] = None
    height: float = 2.5
    diameter: Optional[float] = None
    windows: List[Dict[str, float]] = None
    doors: List[Dict[str, float]] = None
    custom_measurements: List[Dict[str, float]] = None

    def __post_init__(self):
        self.windows = self.windows or []
        self.doors = self.doors or []
        self.custom_measurements = self.custom_measurements or []

# Состояния для калькулятора площади
class AreaCalculatorStates(StatesGroup):
    waiting_for_room_type = State()
    waiting_for_room_shape = State()
    waiting_for_length = State()
    waiting_for_width = State()
    waiting_for_height = State()
    waiting_for_diameter = State()
    waiting_for_windows = State()
    waiting_for_doors = State()
    waiting_for_custom_measurements = State()

# Состояния для калькулятора бюджета
class BudgetCalculatorStates(StatesGroup):
    waiting_for_budget = State()
    waiting_for_material = State()

class MaterialCalculatorStates(StatesGroup):
    waiting_for_area = State()
    waiting_for_material_type = State()
    waiting_for_discount = State()

# Состояния для AI чата
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
        [KeyboardButton(text="📋 Материалы"), KeyboardButton(text="📐 Калькулятор площади")],
        [KeyboardButton(text="💰 Калькулятор бюджета"), KeyboardButton(text="🧮 Калькулятор стоимости")],
        [KeyboardButton(text="🛒 Список покупок"), KeyboardButton(text="🤖 AI Помощник")]
    ],
    resize_keyboard=True
)

# Клавиатура для выбора типа помещения
def get_room_type_keyboard():
    buttons = [[KeyboardButton(text=room_type.value)] for room_type in RoomType]
    buttons.append([KeyboardButton(text="🔙 Назад в меню")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Клавиатура для выбора формы помещения
def get_room_shape_keyboard():
    buttons = [[KeyboardButton(text=shape.value)] for shape in RoomShape]
    buttons.append([KeyboardButton(text="🔙 Назад в меню")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Обработчик кнопки "Назад в меню"
@dp.message(F.text == "🔙 Назад в меню")
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Выберите действие:", reply_markup=keyboard)

# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("👋 Привет! Я StroyHelper бот. Выберите действие:", reply_markup=keyboard)

# Обработчик кнопки "Калькулятор площади"
@dp.message(F.text == "📐 Калькулятор площади")
async def area_calculator_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите тип помещения:",
        reply_markup=get_room_type_keyboard()
    )
    await state.set_state(AreaCalculatorStates.waiting_for_room_type)

# Обработчик выбора типа помещения
@dp.message(AreaCalculatorStates.waiting_for_room_type)
async def process_room_type(message: types.Message, state: FSMContext):
    try:
        room_type = next(rt for rt in RoomType if rt.value == message.text)
        await state.update_data(room_type=room_type.name)
        await message.answer(
            "Выберите форму помещения:",
            reply_markup=get_room_shape_keyboard()
        )
        await state.set_state(AreaCalculatorStates.waiting_for_room_shape)
    except StopIteration:
        await message.answer("Пожалуйста, выберите тип помещения из предложенных вариантов.")

# Обработчик выбора формы помещения
@dp.message(AreaCalculatorStates.waiting_for_room_shape)
async def process_room_shape(message: types.Message, state: FSMContext):
    try:
        room_shape = next(rs for rs in RoomShape if rs.value == message.text)
        await state.update_data(room_shape=room_shape.name)

        if room_shape == RoomShape.CIRCULAR:
            await message.answer(
                "Введите диаметр помещения в метрах:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            await state.set_state(AreaCalculatorStates.waiting_for_diameter)
        else:
            await message.answer(
                "Введите длину помещения в метрах:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            await state.set_state(AreaCalculatorStates.waiting_for_length)
    except StopIteration:
        await message.answer("Пожалуйста, выберите форму помещения из предложенных вариантов.")

# Обработчик ввода длины помещения
@dp.message(AreaCalculatorStates.waiting_for_length)
async def process_length(message: types.Message, state: FSMContext):
    try:
        length = float(message.text)
        if length <= 0:
            raise ValueError("Длина должна быть положительным числом")

        await state.update_data(length=length)
        data = await state.get_data()

        if data["room_shape"] == RoomShape.SQUARE.name:
            await state.update_data(width=length)
            await message.answer("Введите высоту потолков в метрах:")
            await state.set_state(AreaCalculatorStates.waiting_for_height)
        else:
            await message.answer("Введите ширину помещения в метрах:")
            await state.set_state(AreaCalculatorStates.waiting_for_width)
    except ValueError as e:
        await message.answer("Пожалуйста, введите корректное положительное число.")

# Обработчик ввода ширины помещения
@dp.message(AreaCalculatorStates.waiting_for_width)
async def process_width(message: types.Message, state: FSMContext):
    try:
        width = float(message.text)
        if width <= 0:
            raise ValueError("Ширина должна быть положительным числом")

        await state.update_data(width=width)
        await message.answer("Введите высоту потолков в метрах:")
        await state.set_state(AreaCalculatorStates.waiting_for_height)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")

# Обработчик ввода высоты помещения
@dp.message(AreaCalculatorStates.waiting_for_height)
async def process_height(message: types.Message, state: FSMContext):
    try:
        height = float(message.text)
        if height <= 0:
            raise ValueError("Высота должна быть положительным числом")

        data = await state.get_data()
        await state.update_data(height=height)

        # Расчет площади и объема
        if data["room_shape"] == RoomShape.RECTANGULAR.name or data["room_shape"] == RoomShape.SQUARE.name:
            length = data["length"]
            width = data["width"]
            floor_area = length * width
            wall_area = 2 * (length + width) * height
            volume = floor_area * height

            result = (
                f"📊 Результаты расчета:\n\n"
                f"📏 Площадь пола: {floor_area:.2f} м²\n"
                f"🏗 Площадь стен (без учета окон и дверей): {wall_area:.2f} м²\n"
                f"📦 Объем помещения: {volume:.2f} м³\n\n"
                f"❓ Хотите указать размеры окон и дверей для более точного расчета?"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="add_openings")],
                [InlineKeyboardButton(text="Нет", callback_data="skip_openings")]
            ])

            await message.answer(result, reply_markup=keyboard)
        elif data["room_shape"] == RoomShape.CIRCULAR.name:
            diameter = data["diameter"]
            radius = diameter / 2
            floor_area = 3.14159 * radius * radius
            wall_area = 3.14159 * diameter * height
            volume = floor_area * height

            result = (
                f"📊 Результаты расчета для круглого помещения:\n\n"
                f"📏 Площадь пола: {floor_area:.2f} м²\n"
                f"🏗 Площадь стен (без учета окон и дверей): {wall_area:.2f} м²\n"
                f"📦 Объем помещения: {volume:.2f} м³\n\n"
                f"❓ Хотите указать размеры окон и дверей для более точного расчета?"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="add_openings")],
                [InlineKeyboardButton(text="Нет", callback_data="skip_openings")]
            ])

            await message.answer(result, reply_markup=keyboard)

        await state.set_state(AreaCalculatorStates.waiting_for_windows)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")

# Обработчики кнопок для окон и дверей
@dp.callback_query(lambda c: c.data == "add_openings")
async def process_add_openings(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Введите количество окон в помещении (если окон нет, введите 0):"
    )
    await state.set_state(AreaCalculatorStates.waiting_for_windows)

@dp.callback_query(lambda c: c.data == "skip_openings")
async def process_skip_openings(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Расчет завершен! Вы можете начать новый расчет или выбрать другое действие:",
        reply_markup=keyboard
    )
    await state.clear()

# Обработчик ввода диаметра для круглого помещения
@dp.message(AreaCalculatorStates.waiting_for_diameter)
async def process_diameter(message: types.Message, state: FSMContext):
    try:
        diameter = float(message.text)
        if diameter <= 0:
            raise ValueError("Диаметр должен быть положительным числом")

        await state.update_data(diameter=diameter)
        await message.answer("Введите высоту потолков в метрах:")
        await state.set_state(AreaCalculatorStates.waiting_for_height)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")


# Обработчик кнопки "Материалы"
@dp.message(F.text == "📋 Материалы")
async def materials_button(message: types.Message):
    await message.answer("📦 Выберите категорию материалов:", reply_markup=get_categories_keyboard())

# Калькулятор бюджета
@dp.message(F.text == "💰 Калькулятор бюджета")
async def budget_calculator(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Назад в меню")]],
        resize_keyboard=True
    )
    await message.answer("Введите ваш бюджет в рублях:", reply_markup=keyboard)
    await state.set_state(BudgetCalculatorStates.waiting_for_budget)

@dp.message(BudgetCalculatorStates.waiting_for_budget)
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


# Создаем экземпляр AI помощника
ai_helper = AIHelper()

# Добавляем обработчик для AI помощника
@dp.message(F.text == "🛒 Список покупок")
async def shopping_list_menu(message: types.Message):
    shopping_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Показать список")],
            [KeyboardButton(text="➕ Добавить товар")],
            [KeyboardButton(text="➖ Удалить товар")],
            [KeyboardButton(text="🔙 Назад в меню")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("Управление списком покупок:", reply_markup=shopping_keyboard)

@dp.message(F.text == "📝 Показать список")
async def show_shopping_list(message: types.Message):
    await shopping_list.cmd_shopping_list(message)

@dp.message(F.text == "➕ Добавить товар")
async def add_to_shopping_list(message: types.Message):
    await shopping_list.cmd_add_to_list(message)

@dp.message(F.text == "➖ Удалить товар")
async def remove_from_shopping_list(message: types.Message):
    await shopping_list.cmd_remove_from_list(message)

@dp.message(F.text == "🤖 AI Помощник")
async def ai_helper_start(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Назад в меню")]],
        resize_keyboard=True
    )
    await message.answer(
        "Задайте мне вопрос о строительных материалах, и я постараюсь помочь!\n"
        "Например:\n"
        "- Какой ламинат лучше выбрать для кухни?\n"
        "- Чем отличается керамогранит от керамической плитки?\n"
        "- Какая краска подойдет для ванной комнаты?",
        reply_markup=keyboard
    )
    await state.set_state(AIStates.waiting_for_question)

@dp.message(AIStates.waiting_for_question)
async def process_ai_question(message: types.Message, state: FSMContext):
    await message.answer("Думаю над ответом...")
    response = await ai_helper.get_response(message.text)
    await message.answer(response)
    await state.clear()


# Обработчики callback-запросов для списка покупок
@dp.callback_query(lambda c: c.data and c.data.startswith("add_"))
async def callback_add_to_list(callback_query: types.CallbackQuery):
    await shopping_list.process_add_to_list(callback_query)
    
@dp.callback_query(lambda c: c.data and c.data.startswith("remove_"))
async def callback_remove_from_list(callback_query: types.CallbackQuery):
    await shopping_list.process_remove_from_list(callback_query)
    
@dp.callback_query(lambda c: c.data == "clear_list")
async def callback_clear_list(callback_query: types.CallbackQuery):
    await shopping_list.process_clear_list(callback_query)

# Запуск бота
async def main():
    # Регистрация маршрутизатора для списка покупок
    dp.include_router(shopping_list.router)
    
    # Clear any existing webhook and drop pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Set allowed_updates to empty list to minimize conflicts
    await dp.start_polling(bot, allowed_updates=[])


# Обработчик калькулятора стоимости материалов
@dp.message(F.text == "🧮 Калькулятор стоимости")
async def material_calculator_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите площадь помещения в квадратных метрах:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад в меню")]],
            resize_keyboard=True
        )
    )
    await state.set_state(MaterialCalculatorStates.waiting_for_area)

@dp.message(MaterialCalculatorStates.waiting_for_area)
async def process_area(message: types.Message, state: FSMContext):
    try:
        area = float(message.text)
        if area <= 0:
            raise ValueError("Площадь должна быть положительным числом")
        
        await state.update_data(area=area)
        
        # Создаем клавиатуру с доступными материалами
        material_buttons = []
        for category in materials:
            for material in materials[category]:
                if "price" in materials[category][material]:
                    material_buttons.append([KeyboardButton(text=f"{category} - {material}")])
        
        material_buttons.append([KeyboardButton(text="🔙 Назад в меню")])
        material_keyboard = ReplyKeyboardMarkup(keyboard=material_buttons, resize_keyboard=True)
        
        await message.answer(
            "Выберите материал для расчета:",
            reply_markup=material_keyboard
        )
        await state.set_state(MaterialCalculatorStates.waiting_for_material_type)
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число!")

@dp.message(MaterialCalculatorStates.waiting_for_material_type)
async def process_material_type(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад в меню":
        await back_to_menu(message, state)
        return

    try:
        category, material = message.text.split(" - ")
        data = await state.get_data()
        area = data["area"]
        
        material_info = materials[category][material]
        price = material_info["price"]
        
        calculator = MaterialCalculation(
            area=area,
            price_per_unit=price,
            unit=MaterialUnit.SQUARE_METER
        )
        
        result = calculator.calculate()
        
        response = (
            f"📊 Расчет стоимости материалов:\n\n"
            f"🏗 Материал: {material}\n"
            f"📏 Площадь: {area} м²\n"
            f"💵 Цена за м²: {price} руб\n"
            f"📦 Необходимое количество: {result['amount']} м²\n"
            f"💰 Общая стоимость: {result['total_cost']} руб\n\n"
            f"* Учтен запас {calculator.waste_percent}% на подрезку"
        )
        
        await message.answer(response, reply_markup=keyboard)
        await state.clear()
        
    except (ValueError, KeyError):
        await message.answer(
            "Произошла ошибка при расчете. Пожалуйста, выберите материал из списка.",
            reply_markup=keyboard
        )
        await state.clear()

if __name__ == "__main__":
    asyncio.run(main())