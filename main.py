import logging
from asyncio import sleep
from random import randint
from typing import Union

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
# from aiogram.methods

import db
import exceptions
import tasks
from middlewares import AccessMiddleware

logging.basicConfig(level=logging.INFO)

API_TOKEN = '5342785168:AAEAMraHrYNqgYrXCuGnDnzHttoy4jYIvWM'
ACCESS_ID = '751728247' # Ars
# ACCESS_ID = '1663296441'  # Ars2
# ACCESS_ID = '480511953'  # Vlada

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(AccessMiddleware(ACCESS_ID))


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await bot.send_message(message.chat.id,
                           "Меню Admin-бота:\n"
                           "/tasks - Вывести список всех задач\n"
                           "/addtask - Добавить новую задачу\n"
                           "/broadcast - Рассылка\n"
                           "/statistics - Статистика подключеных бонусов\n"
                           )


#  ********************** TASKS **********************

# Создаем CallbackData-объекты, которые будут нужны для работы с менюшкой
menu_cd = CallbackData("show_menu", "level", "category", "tasks", "action")
action_item = CallbackData("action", "task_id")


# С помощью этой функции будем формировать коллбек дату для каждого элемента меню, в зависимости от
# переданных параметров. Если Подкатегория, или айди товара не выбраны - они по умолчанию равны нулю
def make_callback_data(level, category="0", tasks="0", action="0"):
    return menu_cd.new(level=level, category=category, tasks=tasks, action=action)


CATEGORY = {'Актуальные': 0, 'Не актуальные': 1}


# Создаем функцию, которая отдает клавиатуру с доступными категориями
async def categories_keyboard():
    db.update_deadline_status()

    # Указываем, что текущий уровень меню - 0
    CURRENT_LEVEL = 0

    # Создаем Клавиатуру
    markup = InlineKeyboardMarkup(row_width=1)

    for category in list(CATEGORY.items()):
        # Сформируем текст, который будет на кнопке
        button_text = f"{category[0]}"

        # Сформируем колбек дату, которая будет на кнопке. Следующий уровень - текущий + 1, и перечисляем категории
        callback_data = make_callback_data(level=CURRENT_LEVEL + 1, category=category[1])

        # Вставляем кнопку в клавиатуру
        markup.insert(
            InlineKeyboardButton(text=button_text, callback_data=callback_data)
        )

    # Возвращаем созданную клавиатуру в хендлер
    return markup


# Создаем функцию, которая отдает клавиатуру с доступными подкатегориями, исходя из выбранной категории
async def subcategories_keyboard(category):
    # Текущий уровень - 1
    CURRENT_LEVEL = 1
    markup = InlineKeyboardMarkup(row_width=1)

    # Забираем список товаров с РАЗНЫМИ подкатегориями из базы данных с учетом выбранной категории и проходим по ним
    if int(category) == 0:
        tasks = dict(db.fetchall_names())
    if int(category) == 1:
        tasks = dict(db.fetchall_negative_names())
    for task in tasks.keys():
        # Сформируем текст, который будет на кнопке
        button_text = f"{tasks[task]}"

        # Сформируем колбек дату, которая будет на кнопке
        callback_data = make_callback_data(level=CURRENT_LEVEL + 1,
                                           category=category, tasks=task)
        markup.insert(
            InlineKeyboardButton(text=button_text, callback_data=callback_data)
        )

    # Создаем Кнопку "Назад", в которой прописываем колбек дату такую, которая возвращает
    # пользователя на уровень назад - на уровень 0.
    markup.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=make_callback_data(level=CURRENT_LEVEL - 1))
    )
    return markup


# Создаем функцию, которая отдает клавиатуру с доступными товарами, исходя из выбранной категории и подкатегории
ACTIONS = ["Изменить приоритет", "Обнулить выполнение", "Изменить дедлайн", "Удалит"]


async def items_keyboard(category, tasks):
    CURRENT_LEVEL = 2

    # Устанавливаю row_width = 1, чтобы показывалась одна кнопка в строке на товар
    markup = InlineKeyboardMarkup(row_width=1)

    for action in ACTIONS:
        # Сформируем текст, который будет на кнопке
        button_text = f"{action}"

        # Сформируем колбек дату, которая будет на кнопке
        callback_data = make_callback_data(level=CURRENT_LEVEL + 1,
                                           category=category, tasks=tasks,
                                           action=action)
        markup.insert(
            InlineKeyboardButton(
                text=button_text, callback_data=callback_data)
        )

    # Создаем Кнопку "Назад", в которой прописываем колбек дату такую, которая возвращает
    # пользователя на уровень назад - на уровень 1 - на выбор подкатегории
    markup.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=make_callback_data(level=CURRENT_LEVEL - 1,
                                             category=category))
    )
    return markup


# Хендлер на команду /menu
@dp.message_handler(commands='tasks')
async def show_menu(message: types.Message):
    # Выполним функцию, которая отправит пользователю кнопки с доступными категориями
    await list_categories(message)


# Та самая функция, которая отдает категории. Она может принимать как CallbackQuery, так и Message
# Помимо этого, мы в нее можем отправить и другие параметры - category, subcategory, item_id,
# Поэтому ловим все остальное в **kwargs
async def list_categories(message: Union[CallbackQuery, Message], **kwargs):
    # Клавиатуру формируем с помощью следующей функции (где делается запрос в базу данных)
    markup = await categories_keyboard()

    # Проверяем, что за тип апдейта. Если Message - отправляем новое сообщение
    if isinstance(message, Message):
        await message.answer("Виды задач:", reply_markup=markup)

    # Если CallbackQuery - изменяем это сообщение
    elif isinstance(message, CallbackQuery):
        call = message
        await call.message.edit_reply_markup(markup)


# Функция, которая отдает кнопки с подкатегориями, по выбранной пользователем категории
async def list_subcategories(callback: CallbackQuery, category, **kwargs):
    markup = await subcategories_keyboard(category)

    # Изменяем сообщение, и отправляем новые кнопки с подкатегориями
    await callback.message.edit_reply_markup(markup)


# Функция, которая отдает кнопки с Названием и ценой товара, по выбранной категории и подкатегории
async def list_items(callback: CallbackQuery, category, tasks, **kwargs):
    markup = await items_keyboard(category, tasks)

    name, priority, deadline = db.get_priority(tasks)
    text = f"Текущая задача: {name}\n" \
           f"Текущий приоритет: {priority}\n" \
           f"Текущий дедлайн: {deadline}\n\n" \
           f"Действия:"

    # Изменяем сообщение, и отправляем новые кнопки с подкатегориями
    await callback.message.edit_text(text=text, reply_markup=markup)


async def cheng_pioritet(call, task):
    priority_deadline = db.get_priority(task)
    priority = priority_deadline[1]

    markup = InlineKeyboardMarkup(row_width=1)
    button1 = InlineKeyboardButton('Увеличить приортите на 1', callback_data=f'pluse:{priority}:{task}')
    button2 = InlineKeyboardButton('Уменьшить приортите на 1', callback_data=f'minus:{priority}:{task}')
    markup.add(button1, button2)

    await call.message.edit_text(text="В какую сторону изменить приоритет?", reply_markup=markup)


@dp.callback_query_handler(lambda c: 'pluse' in c.data)
async def button_plus(call: types.callback_query):
    pluse, priority, task = call.data.split(":")
    new_priority = int(priority) + 1

    db.cheng_priority(task, new_priority)
    current_priority = db.get_priority(task)

    text = f"Текущая задача: {current_priority[0]}\n" \
           f"Текущий приоритет: {current_priority[1]}"

    await call.message.edit_text(text=text)

    make_callback_data(0)


@dp.callback_query_handler(lambda c: 'minus' in c.data)
async def button_minus(call: types.callback_query):
    minus, priority, task = call.data.split(":")
    new_priority = int(priority) - 1

    db.cheng_priority(task, new_priority)
    current_priority = db.get_priority(task)

    text = f"Текущая задача: {current_priority[0]}\n" \
           f"Текущий приоритет: {current_priority[1]}"

    await call.message.edit_text(text=text)

    make_callback_data(0)


async def cheng_deadline(call, task):

    markup = InlineKeyboardMarkup(row_width=1)
    button1 = InlineKeyboardButton('Дедлайн истечет через 1 день', callback_data=f'deadline:1:{task}')
    button2 = InlineKeyboardButton('Дедлайн истечет через 1 неделю', callback_data=f'deadline:7:{task}')
    button3 = InlineKeyboardButton('Дедлайн истечет через 2 недели', callback_data=f'deadline:14:{task}')
    button4 = InlineKeyboardButton('Дедлайн истечет через 1 месяц', callback_data=f'deadline:30:{task}')
    markup.add(button1, button2, button3, button4)

    await call.message.edit_text(text="Выбери новый дедлайн:", reply_markup=markup)


@dp.callback_query_handler(lambda c: 'deadline' in c.data)
async def button_minus(call: types.callback_query):
    deadline, new_dedline, task = call.data.split(":")

    await db.cheng_deadline(task, new_dedline)

    text = f"Дедлайн изменен. Срок выполнения истечет через {new_dedline} дней."

    await call.message.edit_text(text=text)

    make_callback_data(0)


# Функция, которая отдает уже кнопку Купить товар по выбранному товару
async def show_item(callback: CallbackQuery, category, tasks, action):
    if action == ACTIONS[0]:
        await cheng_pioritet(callback, tasks)
        make_callback_data(0)
    elif action == ACTIONS[1]:
        db.restatr_task(tasks)
        await callback.message.edit_text(text="Выполнение задачи было обнулено!")
        make_callback_data(0)
    elif action == ACTIONS[2]:
        await cheng_deadline(callback, tasks)
        make_callback_data(0)
    elif action == ACTIONS[3]:
        await db.delete('tasks', tasks)
        await callback.message.edit_text(text="Задача удалена из базы данных!")
        make_callback_data(0)


# Функция, которая обрабатывает ВСЕ нажатия на кнопки в этой менюшке
@dp.callback_query_handler(menu_cd.filter())
async def navigate(call: CallbackQuery, callback_data: dict):
    """
    :param call: Тип объекта CallbackQuery, который прилетает в хендлер
    :param callback_data: Словарь с данными, которые хранятся в нажатой кнопке
    """

    # Получаем текущий уровень меню, который запросил пользователь
    current_level = callback_data.get("level")

    # Получаем категорию, которую выбрал пользователь (Передается всегда)
    category = callback_data.get("category")

    # Получаем подкатегорию, которую выбрал пользователь (Передается НЕ ВСЕГДА - может быть 0)
    tasks = callback_data.get("tasks")

    # Получаем айди товара, который выбрал пользователь (Передается НЕ ВСЕГДА - может быть 0)
    action = callback_data.get("action")

    # Прописываем "уровни" в которых будут отправляться новые кнопки пользователю
    levels = {
        "0": list_categories,  # Отдаем категории
        "1": list_subcategories,  # Отдаем подкатегории
        "2": list_items,
        "3": show_item,  # Отдаем товары
    }

    # Забираем нужную функцию для выбранного уровня
    current_level_function = levels[current_level]

    # Выполняем нужную функцию и передаем туда параметры, полученные из кнопки
    await current_level_function(
        call,
        category=category,
        tasks=tasks,
        action=action
    )


#  ********************** ADD TASK **********************


class Task(StatesGroup):
    name = State()
    url = State()
    priority = State()
    category = State()
    deadline = State()


@dp.message_handler(commands='addtask')
async def cmd_addtask(message: types.Message):
    await Task.name.set()
    await message.reply("Если вы допустили ошибку в добавлении задания или передумали его добавлять - воспользуйтесь "
                        "командой /cancel в любой момент добавления.\n\n"
                        "Введи название задачи")


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Добавление новой задачи отменено.')


@dp.message_handler(state=Task.name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Process task name
    """
    async with state.proxy() as data:
        data['name'] = message.text

    await Task.next()
    await message.answer("Жду ссылку на задание.")


@dp.message_handler(state=Task.url)
async def process_url(message: types.Message, state: FSMContext):
    """
    Process task URL
    """
    async with state.proxy() as data:
        data['url'] = message.text

    await Task.next()
    await message.answer("Укажи приоритет задачи от 1 до 10.")


@dp.message_handler(lambda message: not message.text.isdigit(), state=Task.priority)
async def process_priority_invalid(message: types.Message):
    """
    If priority is invalid
    """
    return await message.reply("Приоритет должен быть цифрой.\nПопробуй еще раз. (От 1 до 10)")


@dp.message_handler(lambda message: message.text.isdigit(), state=Task.priority)
async def process_priority(message: types.Message, state: FSMContext):
    # Update state and data
    await Task.next()
    await state.update_data(priority=int(message.text))

    #  Configure ReplyKeyboardMarkup
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Подписка Inst", "Лайк Inst", "Подписка на канал",
               "Подписка на Tik-Tok", "Перейти на сайт",
               "Подписка ВК", "Лайк ВК",
               "Пpослушивание музыки ВК")
    markup.add("Другое")

    await message.answer("Выбери категорию задачи", reply_markup=markup)


@dp.message_handler(lambda message: message.text not in ["Подписка Inst", "Лайк Inst", "Подписка на канал",
                                                         "Подписка на Tik-Tok", "Перейти на сайт",
                                                         "Подписка ВК", "Лайк ВК",
                                                         "Пpослушивание музыки ВК", "Другое"], state=Task.category)
async def process_category_invalid(message: types.Message):
    """
    In this example category is Wrong.
    """
    return await message.reply("Кажется, ты выбрал что-то не то.\nПопробуй еще раз.")


@dp.message_handler(state=Task.category)
async def process_category(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['category'] = message.text

    # Remove keyboard
    markup = types.ReplyKeyboardRemove()
    await Task.next()
    await message.answer("Сколько ДНЕЙ есть на выполнение задания?",
                         reply_markup=markup)


@dp.message_handler(lambda message: not message.text.isdigit(), state=Task.deadline)
async def process_deadline_invalid(message: types.Message):
    """
    If deadline is invalid
    """
    return await message.reply("Дедлайн должен быть указан в часах.\nПопробуй еще раз.")


@dp.message_handler(lambda message: message.text.isdigit(), state=Task.deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    # Update state and data
    await Task.next()
    await state.update_data(deadline=int(message.text))

    async with state.proxy() as data:
        try:
            task = await tasks.add_task(data['name'], data['url'], data['priority'], data['deadline'], data['category'])
        except exceptions.NotCorrectMessage:
            await message.answer("Не могу записать такую задачу 😢")
            return

        answer_message = (
            f"Добвалена новая задача: \n{data['name']}"
        )
        await message.answer(answer_message)
        text_ = await db.fetch_text_for_category(data['category'])
        praise_ = await db.get_praise(data['category'])

        markup = InlineKeyboardMarkup(row_width=1)
        button1 = InlineKeyboardButton('💎 Перейти по ссылке', url=data['url'], callback_data='url')
        button2 = InlineKeyboardButton('✅ Я выполнил', callback_data='rev')
        button3 = InlineKeyboardButton('❌ Пропустить задание', callback_data='skip')
        markup.add(button1, button2, button3)

        await bot.send_message(
            message.chat.id,
            f"➕ Новое задание на {praise_}:"
            f"\n\n{text_} \n\n"
            f"2️⃣ Возвращайтесь⚡️сюда, чтобы получить 💰 вознаграждение.",
            reply_markup=markup
        )

    # Finish conversation
    await state.finish()


########################### РАССЫЛКА ########################

import requests


class Mailing(StatesGroup):
    Text = State()
    url = State()
    bot_api = State()


@dp.message_handler(commands=["broadcast"])
async def mailing(message: types.Message):
    await message.answer("Пришлите текст рассылки")
    await Mailing.Text.set()


@dp.message_handler(state=Mailing.Text)
async def mailing(message: types.Message, state: FSMContext):
    text = message.text
    await state.update_data(text=text)

    await message.answer("Введите ссылку для данной рассылки")

    await Mailing.url.set()

# @dp.message_handler(state=Mailing.Text)
# async def mailing(message: types.Message, state: FSMContext):
#     text = message.message_id
#     await state.update_data(text=text)
#
#     await message.answer("Введите ссылку для данной рассылки")
#
#     await Mailing.url.set()


@dp.message_handler(state=Mailing.url)
async def mailing_start(message: types.Message, state: FSMContext):
    url = message.text
    print("url = ", url)
    await state.update_data(url=url)

    bots_dict = db.get_bots()
    markup = InlineKeyboardMarkup(row_width=1)
    for bot in bots_dict.keys():
        button = InlineKeyboardButton(bot, callback_data=bots_dict[bot])
        markup.add(button)
        print(bot, bots_dict[bot])

    await message.answer("Выбери бота, куда надо отправить рассылку",
                         reply_markup=markup)
    await Mailing.bot_api.set()

# from aiogram.methods.copy_message import CopyMessage

@dp.callback_query_handler(state=Mailing.bot_api)
async def mailing_start(call: types.CallbackQuery, state: FSMContext):
    # MessageId = await bot(CopyMessage(...))
    data = await state.get_data()
    text = data.get("text")
    #    url = data.get("url")
    await state.reset_state()
    await call.message.edit_reply_markup()

    bot_api = call.data
    print("text = ", text)

    users = db.get_bot_users(bot_api=bot_api, status=0)
    print("bot_api =  ", bot_api)
    markup = InlineKeyboardMarkup(row_width=1)
    button1 = InlineKeyboardButton('💎 Перейти в канал', url=data['url'])
    markup.add(button1)
    counter_for_all_users = 0
    counter_for_bloc_users = 0
    for user in users:
        try:
            print("user_id =  ", user)
            # print("from_chat_id =  ", from_chat_id)
            requests.get(
                'https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}&reply_markup={}'.format(
                    bot_api, user, text, markup))

            # requests.get(
            #     'https://api.telegram.org/bot{}/copyMessage?chat_id={}&from_chat_id={}&message_id={}'.format(
            #         bot_api, user, from_chat_id, message_id))

            counter_for_all_users += 1
            await sleep(0.3)
        except Exception:
            db.update_status_of_user(user, 1)
            counter_for_bloc_users += 1
    await call.message.answer(f"Рассылка выполнена."
                              f"\nПолучило письма {counter_for_all_users} пользователей."
                              f"\nЗаблокированно {counter_for_bloc_users} пользователей.")

    await state.finish()


"""
@dp.message_handler(commands=['broadcast'])
async def send_welcome(message: types.Message):
    # вывод всех возможных ботов по имени
    bots_dict = db.get_bots()
    bot_markup = InlineKeyboardMarkup(row_width=1)
    for bot in bots_dict.keys():
        button = InlineKeyboardButton(bot, callback_data=bots_dict[bot])
        bot_markup.add(button)

    await message.answer("Выбери бота, куда надо отправить рассылку",
                         reply_markup=bot_markup)

    # ожидание на ввод текста в md

    # отправка сообщения
    # если ловишь ошибку, то пометка о блоке

    api_token = '2079872666:AAGj-tH_4WasvGQCBvggT9tLzDAlj4OtAy0'
    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
        chat_id='480511953',
        text='Hello world!'
    ))

"""


################# STATISTIC #########################


@dp.message_handler(commands=['statistics'])
async def send_statistics(message: types.Message):
    markup = InlineKeyboardMarkup(row_width=1)
    button1 = InlineKeyboardButton('Фэйк статистика', callback_data='face')
    markup.add(button1)

    bots = db.get_bots()

    text = str()
    for bot_api in bots.keys():
        active_users = db.get_bot_users(bots[bot_api], 0)
        bloc_users = db.get_bot_users(bots[bot_api], 1)
        use_now = randint(6, 13)

        if len(active_users) > use_now:
            text += "\n\n" + f"Бот - {bot_api}\n" \
                             f"Всего пользователей: {len(active_users) + len(bloc_users)}\n" \
                             f"Активных пользователй: {len(active_users)} \n" \
                             f"Заблокировали: {len(bloc_users)}\n" \
                             f"Используют бота сейчас: {use_now}"
        else:
            text += "\n\n" + f"Бот - {bot_api}\n" \
                             f"Всего пользователей: {len(active_users) + len(bloc_users)}\n" \
                             f"Активных пользователй: {len(active_users)} \n" \
                             f"Заблокировали: {len(bloc_users)}\n"

    await bot.send_message(message.chat.id, text=text, reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == 'face')
async def button_face(call: types.callback_query):
    bots = db.get_bots()

    text = str()
    for bot_api in bots.keys():
        active_users = db.get_bot_users(bots[bot_api], 0)
        bloc_users = db.get_bot_users(bots[bot_api], 1)
        use_now = randint(6, 13)

        if len(active_users) > use_now:
            text += "\n\n" + f"Бот - {bot_api}\n" \
                             f"Всего пользователей: {len(active_users) * 9 + int(len(bloc_users) / 3)}\n" \
                             f"Активных пользователй: {len(active_users) * 9} \n" \
                             f"Заблокировали: {int(len(bloc_users) / 3)}\n" \
                             f"Используют бота сейчас: {use_now * 4}"
        else:
            text += "\n\n" + f"Бот - {bot_api}\n" \
                             f"Всего пользователей: {(len(active_users) * 9 + 2) + int(len(bloc_users) / 3)}\n" \
                             f"Активных пользователй: {len(active_users) * 9 + 2} \n" \
                             f"Заблокировали: {int(len(bloc_users) / 3)}\n" \
                             f"Используют бота сейчас: {len(active_users) * 2}"

    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text)


################## ADD BOT #######################

class Bot(StatesGroup):
    bot_name = State()
    bot_api = State()


@dp.message_handler(commands='addbot')
async def cmd_addbot(message: types.Message):
    await Bot.bot_name.set()
    await message.reply("Введи имя бота")


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Добавление нового бота отменено.')


@dp.message_handler(state=Bot.bot_name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Process task name
    """
    async with state.proxy() as data:
        data['bot_name'] = message.text

    await Bot.next()
    await message.answer("Введи API бота")


@dp.message_handler(state=Bot.bot_api)
async def process_url(message: types.Message, state: FSMContext):
    """
    Process task URL
    """
    async with state.proxy() as data:
        data['bot_api'] = message.text

    await Task.next()
    async with state.proxy() as data:
        try:
            bot = await tasks.add_bot(data['bot_name'], data['bot_api'])
        except exceptions.NotCorrectMessage:
            await message.answer("Не могу записать такую задачу 😢")
            return

        answer_message = (
            f"Добвалена новый бот: \n{data['bot_name']}"
        )
        await message.answer(answer_message)

    # Finish conversation
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
