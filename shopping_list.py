
import json
import os
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

SHOPPING_LIST_FILE = "shopping_list.json"

# Состояния для добавления товара с количеством
class ShoppingListStates(StatesGroup):
    waiting_for_quantity = State()
    waiting_for_unit = State()

# Словарь с типами товаров и их единицами измерения
MATERIAL_UNITS = {
    "Клей": "мешков",
    "Штукатурка": "мешков",
    "Гипсокартон": "листов",
    "Керамическая плитка": "м²",
    "Ламинат": "м²",
    "Керамогранит": "м²",
    "Краска": "банок",
    "Обои": "рулонов"
}

# Функция загрузки списка покупок
def load_shopping_list():
    if not os.path.exists(SHOPPING_LIST_FILE):
        return {}
    with open(SHOPPING_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Функция сохранения списка покупок
def save_shopping_list(data):
    with open(SHOPPING_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Функция добавления товара в список
def add_to_list(user_id, item, quantity=None, unit=None):
    data = load_shopping_list()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = []
    
    # Проверяем, есть ли уже такой товар в списке
    existing_item = None
    for i, entry in enumerate(data.get(user_id, [])):
        if isinstance(entry, dict) and entry.get("item") == item:
            existing_item = i
            break
        elif entry == item:
            existing_item = i
            break
    
    # Добавляем или обновляем товар
    if quantity and unit:
        item_data = {"item": item, "quantity": quantity, "unit": unit}
        if existing_item is not None:
            data[user_id][existing_item] = item_data
        else:
            data[user_id].append(item_data)
    else:
        if existing_item is None:
            data[user_id].append(item)
    
    save_shopping_list(data)

# Функция получения списка покупок
def get_list(user_id):
    data = load_shopping_list()
    return data.get(str(user_id), [])

# Функция удаления товара из списка
def remove_from_list(user_id, item):
    data = load_shopping_list()
    user_id = str(user_id)
    if user_id in data:
        # Проверяем тип элементов в списке
        for i, entry in enumerate(data[user_id]):
            if isinstance(entry, dict) and entry.get("item") == item:
                data[user_id].pop(i)
                break
            elif entry == item:
                data[user_id].pop(i)
                break
        
        if not data[user_id]:  # Если список пуст, удаляем пользователя
            del data[user_id]
        save_shopping_list(data)

# Функция очистки списка покупок
def clear_list(user_id):
    data = load_shopping_list()
    user_id = str(user_id)
    if user_id in data:
        del data[user_id]
        save_shopping_list(data)

# Команда просмотра списка покупок
@router.message(Command("shopping_list"))
async def cmd_shopping_list(message: Message):
    items = get_list(message.from_user.id)
    if not items:
        await message.reply("🛒 Ваш список покупок пуст.")
        return
    
    text = "🛒 Ваш список покупок:\n"
    for item in items:
        if isinstance(item, dict):
            text += f"• {item['item']} - {item['quantity']} {item['unit']}\n"
        else:
            text += f"• {item}\n"
    
    # Кнопка очистки списка
    clear_button = InlineKeyboardButton(text="Очистить список", callback_data="clear_list")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[clear_button]])
    
    await message.reply(text, reply_markup=keyboard)

# Команда добавления в список покупок
@router.message(Command("add_to_list"))
async def cmd_add_to_list(message: Message):
    items = list(MATERIAL_UNITS.keys())
    buttons = [[InlineKeyboardButton(text=item, callback_data=f"select_{item}")] for item in items]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.reply("Выберите материал для добавления в список покупок:", reply_markup=keyboard)

# Обработчик callback для выбора материала
@router.callback_query(lambda c: c.data and c.data.startswith("select_"))
async def process_select_material(callback_query: types.CallbackQuery, state: FSMContext):
    item = callback_query.data.split("select_")[1]
    await state.update_data(item=item)
    
    await callback_query.message.answer(f"Введите количество {item} (число):")
    await state.set_state(ShoppingListStates.waiting_for_quantity)
    await callback_query.answer()

# Обработчик ввода количества
@router.message(ShoppingListStates.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = float(message.text)
        data = await state.get_data()
        item = data["item"]
        
        await state.update_data(quantity=quantity)
        
        unit = MATERIAL_UNITS.get(item, "шт")
        
        # Добавляем товар в список
        add_to_list(message.from_user.id, item, quantity, unit)
        
        await message.answer(f"✅ {item} в количестве {quantity} {unit} добавлен в список покупок!")
        await state.clear()
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число!")

# Обработчик callback для очистки списка
@router.callback_query(lambda c: c.data == "clear_list")
async def process_clear_list(callback_query: types.CallbackQuery):
    clear_list(callback_query.from_user.id)
    await callback_query.answer("🗑 Ваш список покупок очищен.", show_alert=True)

# Команда удаления из списка
@router.message(Command("remove_from_list"))
async def cmd_remove_from_list(message: Message):
    items = get_list(message.from_user.id)
    if not items:
        await message.reply("Ваш список покупок пуст.")
        return
    
    buttons = []
    for item in items:
        if isinstance(item, dict):
            buttons.append([InlineKeyboardButton(
                text=f"{item['item']} - {item['quantity']} {item['unit']}", 
                callback_data=f"remove_{item['item']}"
            )])
        else:
            buttons.append([InlineKeyboardButton(text=item, callback_data=f"remove_{item}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.reply("Выберите материал для удаления из списка:", reply_markup=keyboard)

# Обработчик callback для удаления из списка
@router.callback_query(lambda c: c.data and c.data.startswith("remove_"))
async def process_remove_from_list(callback_query: types.CallbackQuery):
    item = callback_query.data.split("remove_")[1]
    remove_from_list(callback_query.from_user.id, item)
    await callback_query.answer(f"❌ {item} удален из списка.", show_alert=True)
