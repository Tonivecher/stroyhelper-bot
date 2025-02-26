
import json
import os
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

router = Router()

SHOPPING_LIST_FILE = "shopping_list.json"

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
def add_to_list(user_id, item):
    data = load_shopping_list()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = []
    if item not in data[user_id]:
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
    if user_id in data and item in data[user_id]:
        data[user_id].remove(item)
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
    text = "🛒 Ваш список покупок:\n" + "\n".join(f"• {item}" for item in items)
    
    # Кнопка очистки списка
    clear_button = InlineKeyboardButton(text="Очистить список", callback_data="clear_list")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[clear_button]])
    
    await message.reply(text, reply_markup=keyboard)

# Команда добавления в список покупок
@router.message(Command("add_to_list"))
async def cmd_add_to_list(message: Message):
    items = ["Клей", "Штукатурка", "Гипсокартон", "Керамическая плитка", "Ламинат"]
    buttons = [[InlineKeyboardButton(text=item, callback_data=f"add_{item}")] for item in items]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.reply("Выберите материал для добавления в список покупок:", reply_markup=keyboard)

# Обработчик callback для добавления в список
@router.callback_query(lambda c: c.data and c.data.startswith("add_"))
async def process_add_to_list(callback_query: types.CallbackQuery):
    item = callback_query.data.split("add_")[1]
    add_to_list(callback_query.from_user.id, item)
    await callback_query.answer(f"✅ {item} добавлен в список покупок!", show_alert=True)

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
    buttons = [[InlineKeyboardButton(text=item, callback_data=f"remove_{item}")] for item in items]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.reply("Выберите материал для удаления из списка:", reply_markup=keyboard)

# Обработчик callback для удаления из списка
@router.callback_query(lambda c: c.data and c.data.startswith("remove_"))
async def process_remove_from_list(callback_query: types.CallbackQuery):
    item = callback_query.data.split("remove_")[1]
    remove_from_list(callback_query.from_user.id, item)
    await callback_query.answer(f"❌ {item} удален из списка.", show_alert=True)
