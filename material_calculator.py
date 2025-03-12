import logging
import asyncio
import os
import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Union, Any

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, FSInputFile
)
import aiosqlite
import fpdf

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Константы
DEFAULT_UNIT = "м"  # По умолчанию измерения в метрах
UNITS = {"м": 1, "см": 0.01, "мм": 0.001}
MATERIAL_TYPES = ["Обои", "Плитка", "Ламинат", "Штукатурка", "Краска", "Наливной пол"]

# Определение состояний FSM
class AreaCalculator(StatesGroup):
    # Основные размеры помещения
    waiting_for_room_length = State()
    waiting_for_room_width = State()
    waiting_for_room_height = State()

    # Единицы измерения
    select_unit = State()

    # Вычеты
    ask_for_deduction = State()
    deduction_type = State()
    deduction_length = State()
    deduction_width = State()

    # Материалы
    select_material = State()
    material_thickness = State()

    # Сохранение и управление расчетами
    saving_calculation = State()
    manage_calculations = State()
    export_format = State()

# Функции для работы с базой данных
async def init_db():
    async with aiosqlite.connect("area_calculator.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                room_length REAL NOT NULL,
                room_width REAL NOT NULL,
                room_height REAL,
                unit TEXT NOT NULL,
                total_area REAL NOT NULL,
                net_area REAL NOT NULL,
                material_type TEXT,
                material_thickness REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS deductions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculation_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                length REAL NOT NULL,
                width REAL NOT NULL,
                area REAL NOT NULL,
                FOREIGN KEY (calculation_id) REFERENCES calculations (id) ON DELETE CASCADE
            )
        ''')
        
        await db.commit()

async def save_calculation(user_id: int, data: Dict[str, Any]) -> int:
    async with aiosqlite.connect("area_calculator.db") as db:
        cursor = await db.execute('''
            INSERT INTO calculations (user_id, room_length, room_width, room_height, unit, total_area, net_area, material_type, material_thickness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data.get("room_length", 0),
            data.get("room_width", 0),
            data.get("room_height", 0),
            data.get("unit", DEFAULT_UNIT),
            data.get("total_area", 0),
            data.get("net_area", 0),
            data.get("material_type", ""),
            data.get("material_thickness", 0)
        ))
        await db.commit()
        calculation_id = cursor.lastrowid

        if "deductions" in data and data["deductions"]:
            for deduction in data["deductions"]:
                await db.execute('''
                    INSERT INTO deductions (calculation_id, type, length, width, area)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    calculation_id,
                    deduction.get("type", ""),
                    deduction.get("length", 0),
                    deduction.get("width", 0),
                    deduction.get("area", 0)
                ))
            await db.commit()
        
        return calculation_id

async def get_user_calculations(user_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect("area_calculator.db") as db:
        db.row_factory = aiosqlite.Row
        calculations = []

        async with db.execute(
            "SELECT * FROM calculations WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ) as cursor:
            async for row in cursor:
                calculation = dict(row)
                calculation["deductions"] = []
                
                async with db.execute(
                    "SELECT * FROM deductions WHERE calculation_id = ?",
                    (row["id"],)
                ) as deductions_cursor:
                    async for deduction_row in deductions_cursor:
                        calculation["deductions"].append(dict(deduction_row))
                
                calculations.append(calculation)
        
        return calculations

async def delete_calculation(calculation_id: int) -> bool:
    async with aiosqlite.connect("area_calculator.db") as db:
        await db.execute("DELETE FROM calculations WHERE id = ?", (calculation_id,))
        await db.commit()
        return True

# Вспомогательные функции
def convert_to_meters(value: float, unit: str) -> float:
    return value * UNITS.get(unit, 1)

def format_area(area: float, unit: str) -> str:
    if unit == "м":
        return f"{round(area, 2)} м²"
    elif unit == "см":
        return f"{round(area * 10000, 2)} см²"
    elif unit == "мм":
        return f"{round(area * 1000000, 2)} мм²"
    return f"{round(area, 2)} м²"

def format_volume(volume: float, unit: str, thickness_unit: str = None) -> str:
    if thickness_unit and thickness_unit != unit:
        volume = volume * (UNITS.get(thickness_unit, 1) / UNITS.get(unit, 1))

    if unit == "м":
        return f"{round(volume, 3)} м³"
    elif unit == "см":
        return f"{round(volume * 1000000, 2)} см³"
    elif unit == "мм":
        return f"{round(volume * 1000000000, 2)} мм³"
    return f"{round(volume, 3)} м³"

# Создание клавиатур
def get_main_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🧮 Новый расчет")],
        [KeyboardButton(text="📋 Мои расчеты"), KeyboardButton(text="ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_unit_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Метры (м)", callback_data="unit_м"),
            InlineKeyboardButton(text="Сантиметры (см)", callback_data="unit_см"),
            InlineKeyboardButton(text="Миллиметры (мм)", callback_data="unit_мм")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Да", callback_data=f"{prefix}_yes"),
            InlineKeyboardButton(text="Нет", callback_data=f"{prefix}_no")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_deduction_type_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Окно", callback_data="deduction_window")],
        [InlineKeyboardButton(text="Дверь", callback_data="deduction_door")],
        [InlineKeyboardButton(text="Колонна", callback_data="deduction_column")],
        [InlineKeyboardButton(text="Ниша", callback_data="deduction_niche")],
        [InlineKeyboardButton(text="Завершить вычеты", callback_data="deduction_done")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_material_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for i in range(0, len(MATERIAL_TYPES), 2):
        row = []
        row.append(InlineKeyboardButton(text=MATERIAL_TYPES[i], callback_data=f"material_{MATERIAL_TYPES[i]}"))
        if i + 1 < len(MATERIAL_TYPES):
            row.append(InlineKeyboardButton(text=MATERIAL_TYPES[i + 1], callback_data=f"material_{MATERIAL_TYPES[i + 1]}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="Пропустить", callback_data="material_skip")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_export_format_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Сообщение в Telegram", callback_data="export_message"),
            InlineKeyboardButton(text="PDF документ", callback_data="export_pdf")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Обработчики команд
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        "Я расширенный калькулятор площади для Stroyhelper. "
        "С моей помощью вы можете легко рассчитать площадь помещения с учетом вычетов, "
        "получить расчеты для отделки и многое другое!\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    help_text = (
        "📚 <b>Помощь по использованию калькулятора площади</b>\n\n"
        "🧮 <b>Новый расчет</b> - начать новый расчет площади. Вам будет предложено:\n"
        "   - Выбрать единицы измерения\n"
        "   - Ввести размеры помещения\n"
        "   - Добавить вычеты (окна, двери и т.д.)\n"
        "   - Выбрать тип материала\n"
        "   - Указать толщину материала (при необходимости)\n\n"
        "📋 <b>Мои расчеты</b> - просмотр и управление сохраненными расчетами. Вы можете:\n"
        "   - Просмотреть детали любого расчета\n"
        "   - Удалить ненужные расчеты\n"
        "   - Экспортировать расчет (как сообщение или PDF)\n\n"
        "Для расчета площади введите размеры в выбранных единицах измерения, "
        "бот автоматически выполнит все необходимые преобразования и вычисления."
    )
    await message.answer(help_text, reply_markup=get_main_keyboard())

@router.message(F.text == "🧮 Новый расчет")
async def start_new_calculation(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(deductions=[], unit=DEFAULT_UNIT)

    await message.answer(
        "Выберите единицы измерения для расчёта:",
        reply_markup=get_unit_keyboard()
    )
    await state.set_state(AreaCalculator.select_unit)

@router.message(F.text == "📋 Мои расчеты")
async def show_calculations(message: Message, state: FSMContext):
    calculations = await get_user_calculations(message.from_user.id)

    if not calculations:
        await message.answer(
            "У вас пока нет сохраненных расчетов. Чтобы создать новый расчет, "
            "нажмите кнопку '🧮 Новый расчет'.", reply_markup=get_main_keyboard()
        )
        return

    buttons = []
    for calc in calculations[:10]:
        created_at = datetime.datetime.fromisoformat(calc["created_at"].replace('Z', '+00:00'))
        formatted_date = created_at.strftime("%d.%m.%Y %H:%M")
        area_text = f"{format_area(calc['net_area'], calc['unit'])} - {formatted_date}"
        buttons.append([InlineKeyboardButton(text=area_text, callback_data=f"view_calc_{calc['id']}")])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])

    await message.answer(
        "Выберите расчет для просмотра:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(AreaCalculator.manage_calculations)

# Обработчики коллбэков
@router.callback_query(F.data.startswith("unit_"))
async def process_unit_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    unit = callback.data.split("_")[1]
    await state.update_data(unit=unit)

    await callback.message.edit_text(
        f"Выбраны единицы измерения: {unit}\n\n"
        f"Теперь введите длину помещения (в {unit}):"
    )
    await state.set_state(AreaCalculator.waiting_for_room_length)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        "Вы вернулись в главное меню. Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.message.delete()

@router.callback_query(F.data.startswith("view_calc_"))
async def view_calculation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    calc_id = int(callback.data.split("_")[2])

    calculations = await get_user_calculations(callback.from_user.id)
    calculation = next((c for c in calculations if c["id"] == calc_id), None)

    if not calculation:
        await callback.message.edit_text(
            "Расчет не найден. Возможно, он был удален.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_calculations")]
            ])
        )
        return

    total_area = calculation["total_area"]
    net_area = calculation["net_area"]
    unit = calculation["unit"]

    text = [
        f"📊 <b>Информация о расчете #{calculation['id']}</b>",
        f"📏 Размеры помещения: {calculation['room_length']} × {calculation['room_width']} {unit}",
        f"📐 Общая площадь: {format_area(total_area, unit)}",
        f"🧮 Площадь с учетом вычетов: {format_area(net_area, unit)}"
    ]

    if calculation["room_height"]:
        text.append(f"🏢 Высота: {calculation['room_height']} {unit}")
        
        wall_perimeter = 2 * (calculation['room_length'] + calculation['room_width'])
        wall_area = wall_perimeter * calculation['room_height']
        text.append(f"🧱 Площадь стен: {format_area(wall_area, unit)}")

    if calculation["material_type"]:
        text.append(f"🧰 Тип материала: {calculation['material_type']}")
        
        if calculation["material_thickness"]:
            text.append(f"📏 Толщина материала: {calculation['material_thickness']} {unit}")
            
            material_volume = net_area * calculation['material_thickness']
            text.append(f"📦 Объем материала: {format_volume(material_volume, unit)}")

    if calculation["deductions"]:
        text.append("\n<b>Вычеты:</b>")
        for i, deduction in enumerate(calculation["deductions"], 1):
            deduction_type_names = {
                "window": "Окно",
                "door": "Дверь",
                "column": "Колонна",
                "niche": "Ниша"
            }
            deduction_type = deduction_type_names.get(deduction["type"], deduction["type"])
            text.append(
                f"{i}. {deduction_type}: {deduction['length']} × {deduction['width']} {unit} "
                f"({format_area(deduction['area'], unit)})"
            )

    created_at = datetime.datetime.fromisoformat(calculation["created_at"].replace('Z', '+00:00'))
    formatted_date = created_at.strftime("%d.%м.%Y %H:%M")
    text.append(f"\n📅 Дата создания: {formatted_date}")

    buttons = [
        [
            InlineKeyboardButton(text="📤 Экспортировать", callback_data=f"export_calc_{calc_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_calc_{calc_id}")
        ],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_calculations")]
    ]

    await callback.message.edit_text(
        "\n".join(text),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "back_to_calculations")
async def back_to_calculations(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_calculations(callback.message, state)
    await callback.message.delete()

@router.callback_query(F.data.startswith("delete_calc_"))
async def confirm_delete_calculation(callback: CallbackQuery):
    await callback.answer()
    calc_id = int(callback.data.split("_")[2])

    await callback.message.edit_text(
        "Вы уверены, что хотите удалить этот расчет? Это действие нельзя отменить.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{calc_id}"),
                InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"view_calc_{calc_id}")
            ]
        ])
    )

@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_calculation_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    calc_id = int(callback.data.split("_")[2])

    result = await delete_calculation(calc_id)

    if result:
        await callback.message.edit_text(
            "✅ Расчет успешно удален.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_calculations")]
            ])
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при удалении расчета. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [