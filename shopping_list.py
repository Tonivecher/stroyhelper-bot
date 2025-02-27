
import json
import os
import logging
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()

SHOPPING_LIST_FILE = "shopping_list.json"

# Состояния для списков покупок
class ShoppingListStates(StatesGroup):
    waiting_for_quantity = State()
    waiting_for_unit = State()
    waiting_for_list_name = State()
    selecting_list = State()

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

# Функция загрузки списков покупок
def load_shopping_list():
    if not os.path.exists(SHOPPING_LIST_FILE):
        return {}
    try:
        with open(SHOPPING_LIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Проверка структуры данных и исправление, если необходимо
            for user_id in data:
                if isinstance(data[user_id], list):
                    data[user_id] = {"lists": {}}
            return data
    except json.JSONDecodeError:
        # В случае ошибки декодирования JSON, вернем пустой словарь
        return {}

# Функция сохранения списков покупок
def save_shopping_list(data):
    with open(SHOPPING_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Функция добавления товара в список
def add_to_list(user_id, list_name, item, quantity=None, unit=None):
    data = load_shopping_list()
    user_id = str(user_id)
    
    if user_id not in data:
        data[user_id] = {"lists": {}}
    
    if "lists" not in data[user_id]:
        data[user_id]["lists"] = {}
    
    if list_name not in data[user_id]["lists"]:
        data[user_id]["lists"][list_name] = []
    
    # Проверяем, есть ли уже такой товар в списке
    existing_item = None
    for i, entry in enumerate(data[user_id]["lists"][list_name]):
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
            data[user_id]["lists"][list_name][existing_item] = item_data
        else:
            data[user_id]["lists"][list_name].append(item_data)
    else:
        if existing_item is None:
            data[user_id]["lists"][list_name].append(item)
    
    save_shopping_list(data)

# Функция получения всех списков пользователя
def get_user_lists(user_id):
    data = load_shopping_list()
    user_id = str(user_id)
    
    if user_id not in data:
        return {}
    
    # Проверяем, что data[user_id] - это словарь, а не список
    if isinstance(data[user_id], list):
        # Если это список, преобразуем его в словарь
        data[user_id] = {"lists": {}}
        save_shopping_list(data)
    
    if "lists" not in data[user_id]:
        data[user_id]["lists"] = {}
        save_shopping_list(data)
    
    return data[user_id]["lists"]

# Функция получения конкретного списка покупок
def get_list(user_id, list_name):
    data = load_shopping_list()
    user_id = str(user_id)
    
    if user_id not in data or "lists" not in data[user_id] or list_name not in data[user_id]["lists"]:
        return []
    
    return data[user_id]["lists"][list_name]

# Функция создания нового списка
def create_list(user_id, list_name):
    data = load_shopping_list()
    user_id = str(user_id)
    
    if user_id not in data:
        data[user_id] = {"lists": {}}
    
    # Проверяем, что data[user_id] - это словарь, а не список
    if isinstance(data[user_id], list):
        # Если это список, преобразуем его в словарь
        data[user_id] = {"lists": {}}
    
    if "lists" not in data[user_id]:
        data[user_id]["lists"] = {}
    
    if list_name not in data[user_id]["lists"]:
        data[user_id]["lists"][list_name] = []
        save_shopping_list(data)
        return True
    
    return False

# Функция удаления товара из списка
def remove_from_list(user_id, list_name, item):
    data = load_shopping_list()
    user_id = str(user_id)
    
    if user_id in data and "lists" in data[user_id] and list_name in data[user_id]["lists"]:
        # Проверяем тип элементов в списке
        for i, entry in enumerate(data[user_id]["lists"][list_name]):
            if isinstance(entry, dict) and entry.get("item") == item:
                data[user_id]["lists"][list_name].pop(i)
                break
            elif entry == item:
                data[user_id]["lists"][list_name].pop(i)
                break
        
        save_shopping_list(data)

# Функция удаления списка
def delete_list(user_id, list_name):
    data = load_shopping_list()
    user_id = str(user_id)
    
    if user_id in data and "lists" in data[user_id] and list_name in data[user_id]["lists"]:
        del data[user_id]["lists"][list_name]
        save_shopping_list(data)
        return True
    
    return False

# Функция очистки списка покупок
def clear_list(user_id, list_name):
    data = load_shopping_list()
    user_id = str(user_id)
    
    if user_id in data and "lists" in data[user_id] and list_name in data[user_id]["lists"]:
        data[user_id]["lists"][list_name] = []
        save_shopping_list(data)
        return True
    
    return False

# Обработчики команд

# Обработчик команды списка покупок
@router.message(Command("shopping_list"))
async def cmd_shopping_list(message: Message, state: FSMContext):
    await show_lists_menu(message, state)

# Функция для показа меню со списками
async def show_lists_menu(message: Message, state: FSMContext = None):
    user_lists = get_user_lists(message.from_user.id)
    
    buttons = []
    if user_lists:
        for list_name in user_lists:
            buttons.append([InlineKeyboardButton(text=f"📋 {list_name}", callback_data=f"open_list:{list_name}")])
    
    buttons.append([InlineKeyboardButton(text="✨ Создать новый список", callback_data="create_new_list")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer("🛒 Ваши списки покупок:", reply_markup=keyboard)

# Обработчик команды создания нового списка
@router.callback_query(lambda c: c.data == "create_new_list")
async def process_create_list(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Введите название для нового списка покупок:")
    await state.set_state(ShoppingListStates.waiting_for_list_name)

# Обработчик ввода названия списка
@router.message(ShoppingListStates.waiting_for_list_name)
async def process_list_name(message: Message, state: FSMContext):
    list_name = message.text.strip()
    
    if not list_name:
        await message.answer("Название списка не может быть пустым. Попробуйте еще раз:")
        return
    
    try:
        logger.info(f"Попытка создания списка '{list_name}' пользователем {message.from_user.id}")
        
        # Проверим текущую структуру данных
        current_data = load_shopping_list()
        logger.info(f"Текущие данные для пользователя {message.from_user.id}: {current_data.get(str(message.from_user.id), {})}")
        
        created = create_list(message.from_user.id, list_name)
        
        if created:
            await message.answer(f"✅ Список \"{list_name}\" создан успешно!")
        else:
            await message.answer(f"⚠️ Список с названием \"{list_name}\" уже существует.")
        
        await state.clear()
        await show_lists_menu(message)
    except Exception as e:
        logger.error(f"Ошибка при создании списка: {e}", exc_info=True)
        await message.answer("Произошла ошибка при создании списка. Пожалуйста, попробуйте еще раз.")
        await state.clear()

# Обработчик открытия списка
@router.callback_query(lambda c: c.data and c.data.startswith("open_list:"))
async def process_open_list(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        list_name = callback_query.data.split(":")[1]
        items = get_list(callback_query.from_user.id, list_name)
        
        await callback_query.answer()
        
        if not items:
            text = f"📋 Список \"{list_name}\" пуст."
        else:
            text = f"📋 Список \"{list_name}\":\n"
            for item in items:
                if isinstance(item, dict) and 'item' in item and 'quantity' in item and 'unit' in item:
                    text += f"• {item['item']} - {item['quantity']} {item['unit']}\n"
                elif isinstance(item, str):
                    text += f"• {item}\n"
                else:
                    # Обработка некорректного формата элемента
                    text += f"• [Элемент в неправильном формате]\n"
        
        # Кнопки управления списком
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"add_to_list:{list_name}")],
            [InlineKeyboardButton(text="➖ Удалить товар", callback_data=f"remove_from_list:{list_name}")],
            [InlineKeyboardButton(text="🗑 Очистить список", callback_data=f"clear_list:{list_name}")],
            [InlineKeyboardButton(text="❌ Удалить список", callback_data=f"delete_list:{list_name}")],
            [InlineKeyboardButton(text="🔙 К списку списков", callback_data="back_to_lists")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка при открытии списка: {e}")
        await callback_query.answer("Произошла ошибка при открытии списка")
        await show_lists_menu(callback_query.message)

# Обработчик добавления товара в список
@router.callback_query(lambda c: c.data and c.data.startswith("add_to_list:"))
async def process_add_to_list(callback_query: types.CallbackQuery, state: FSMContext):
    list_name = callback_query.data.split(":")[1]
    await state.update_data(current_list=list_name)
    
    items = list(MATERIAL_UNITS.keys())
    buttons = [[InlineKeyboardButton(text=item, callback_data=f"select_{item}")] for item in items]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"open_list:{list_name}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.answer()
    await callback_query.message.edit_text("Выберите материал для добавления в список:", reply_markup=keyboard)

# Обработчик возврата к списку списков
@router.callback_query(lambda c: c.data == "back_to_lists")
async def process_back_to_lists(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await show_lists_menu(callback_query.message)

# Обработчик выбора материала
@router.callback_query(lambda c: c.data and c.data.startswith("select_"))
async def process_select_material(callback_query: types.CallbackQuery, state: FSMContext):
    item = callback_query.data.split("select_")[1]
    data = await state.get_data()
    list_name = data.get("current_list")
    
    await state.update_data(item=item)
    
    await callback_query.answer()
    await callback_query.message.edit_text(f"Введите количество {item} (число):")
    await state.set_state(ShoppingListStates.waiting_for_quantity)

# Обработчик ввода количества
@router.message(ShoppingListStates.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = float(message.text)
        data = await state.get_data()
        item = data["item"]
        list_name = data["current_list"]
        
        unit = MATERIAL_UNITS.get(item, "шт")
        
        # Добавляем товар в список
        add_to_list(message.from_user.id, list_name, item, quantity, unit)
        
        await message.answer(f"✅ {item} в количестве {quantity} {unit} добавлен в список \"{list_name}\"!")
        await state.clear()
        
        # Показываем обновленный список
        items = get_list(message.from_user.id, list_name)
        if not items:
            text = f"📋 Список \"{list_name}\" пуст."
        else:
            text = f"📋 Список \"{list_name}\":\n"
            for item in items:
                if isinstance(item, dict):
                    text += f"• {item['item']} - {item['quantity']} {item['unit']}\n"
                else:
                    text += f"• {item}\n"
        
        # Кнопки управления списком
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"add_to_list:{list_name}")],
            [InlineKeyboardButton(text="➖ Удалить товар", callback_data=f"remove_from_list:{list_name}")],
            [InlineKeyboardButton(text="🗑 Очистить список", callback_data=f"clear_list:{list_name}")],
            [InlineKeyboardButton(text="❌ Удалить список", callback_data=f"delete_list:{list_name}")],
            [InlineKeyboardButton(text="🔙 К списку списков", callback_data="back_to_lists")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, reply_markup=keyboard)
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число!")

# Обработчик удаления товара из списка
@router.callback_query(lambda c: c.data and c.data.startswith("remove_from_list:"))
async def process_remove_from_list_menu(callback_query: types.CallbackQuery, state: FSMContext):
    list_name = callback_query.data.split(":")[1]
    items = get_list(callback_query.from_user.id, list_name)
    
    await callback_query.answer()
    
    if not items:
        await callback_query.message.edit_text(
            f"📋 Список \"{list_name}\" пуст.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"open_list:{list_name}")]
            ])
        )
        return
    
    buttons = []
    for item in items:
        if isinstance(item, dict):
            item_text = f"{item['item']} - {item['quantity']} {item['unit']}"
            buttons.append([InlineKeyboardButton(text=item_text, callback_data=f"remove_item:{list_name}:{item['item']}")])
        else:
            buttons.append([InlineKeyboardButton(text=item, callback_data=f"remove_item:{list_name}:{item}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"open_list:{list_name}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(f"Выберите товар для удаления из списка \"{list_name}\":", reply_markup=keyboard)

# Обработчик выбора товара для удаления
@router.callback_query(lambda c: c.data and c.data.startswith("remove_item:"))
async def process_remove_item(callback_query: types.CallbackQuery, state: FSMContext):
    _, list_name, item = callback_query.data.split(":", 2)
    
    remove_from_list(callback_query.from_user.id, list_name, item)
    
    await callback_query.answer(f"❌ {item} удален из списка.")
    
    # Показываем обновленный список
    items = get_list(callback_query.from_user.id, list_name)
    if not items:
        text = f"📋 Список \"{list_name}\" пуст."
    else:
        text = f"📋 Список \"{list_name}\":\n"
        for item in items:
            if isinstance(item, dict):
                text += f"• {item['item']} - {item['quantity']} {item['unit']}\n"
            else:
                text += f"• {item}\n"
    
    # Кнопки управления списком
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"add_to_list:{list_name}")],
        [InlineKeyboardButton(text="➖ Удалить товар", callback_data=f"remove_from_list:{list_name}")],
        [InlineKeyboardButton(text="🗑 Очистить список", callback_data=f"clear_list:{list_name}")],
        [InlineKeyboardButton(text="❌ Удалить список", callback_data=f"delete_list:{list_name}")],
        [InlineKeyboardButton(text="🔙 К списку списков", callback_data="back_to_lists")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback_query.message.edit_text(text, reply_markup=keyboard)

# Обработчик очистки списка
@router.callback_query(lambda c: c.data and c.data.startswith("clear_list:"))
async def process_clear_list(callback_query: types.CallbackQuery, state: FSMContext):
    list_name = callback_query.data.split(":")[1]
    cleared = clear_list(callback_query.from_user.id, list_name)
    
    if cleared:
        await callback_query.answer(f"🗑 Список \"{list_name}\" очищен.")
    else:
        await callback_query.answer("Произошла ошибка при очистке списка.")
    
    # Показываем пустой список
    text = f"📋 Список \"{list_name}\" пуст."
    
    # Кнопки управления списком
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"add_to_list:{list_name}")],
        [InlineKeyboardButton(text="❌ Удалить список", callback_data=f"delete_list:{list_name}")],
        [InlineKeyboardButton(text="🔙 К списку списков", callback_data="back_to_lists")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback_query.message.edit_text(text, reply_markup=keyboard)

# Обработчик удаления списка
@router.callback_query(lambda c: c.data and c.data.startswith("delete_list:"))
async def process_delete_list(callback_query: types.CallbackQuery, state: FSMContext):
    list_name = callback_query.data.split(":")[1]
    deleted = delete_list(callback_query.from_user.id, list_name)
    
    if deleted:
        await callback_query.answer(f"❌ Список \"{list_name}\" удален.")
    else:
        await callback_query.answer("Произошла ошибка при удалении списка.")
    
    await show_lists_menu(callback_query.message)
