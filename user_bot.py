import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton

import db
import exceptions
import tasks

logging.basicConfig(level=logging.INFO)

API_TOKEN = '5337359559:AAEHMQ_K32fgBHm_XJfsgGa3sfc0BfTUs8Y'

EARN = '💎 Заработать'
BALANCE = '💰 Баланс'
WITHDRAW = '💸 Вывод'
INVITE = '💌 Приглашенные'
HELP = '❓ Помощь'

VAL = '₽'

REFERRALS = 5
MIN_WITHDRAW = 3000

BOT_NAME = 'BankOfSubsbot'

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

start_markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, )
buttons = [
    KeyboardButton(EARN, callback_data='button1'),
    KeyboardButton(BALANCE, callback_data='button2'),
    KeyboardButton(WITHDRAW, callback_data='button3'),
    KeyboardButton(INVITE, callback_data='button4'),
    KeyboardButton(HELP, callback_data='button5')]
start_markup.add(buttons[0]).row(buttons[1], buttons[2]).row(buttons[3], buttons[4])


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Отправляет приветственное сообщение и помощь по боту"""
    user_id = message.from_user.id

    is_user = db.insert_user(user_id, API_TOKEN)

    if len(message.text.split()) > 1:
        referral_id = message.text.split()[1]
    else:
        referral_id = None

    if is_user != -1:
        if referral_id is not None:
            if int(referral_id) != int(user_id):
                await db.update_referral(referral_id)
                await db.update_balance_referral(referral_id)

    await message.reply("Выбери действие", reply_markup=start_markup)


async def help_reply(message: types.Message):
    text = await db.fetch_text_for_command(message.text)

    await message.answer(f"{text}")


async def invite_reply(message: types.Message):
    id_ = message.from_user.id
    link = f'https://telegram.me/{BOT_NAME}?start={str(id_)}'

    counter_of_users_ = await db.fetch_balance(id_)
    counter_of_users = counter_of_users_[1]
    if counter_of_users >= 5:
        status = "Подтвержденный"
    else:
        status = "Не подтвержденный"

    text = f"🗣 Приглашено человек: {counter_of_users}\n\n" \
           f"За каждого приглашенного друга вы будете получать 100₽\n\n" \
           f"Для получения бонуса, отправь ссылку другу:\n\n{link}\n\n" \
           f"🌚 Ваш статус: {status}\n\n" \
           f"Для того чтобы получить именной статус, пригласите от {REFERRALS}-х человек по своей партнерской ссылке."

    await message.answer(text)


async def new_task(message: types.Message, user_id=None):
    try:
        print(user_id)
        if user_id is None:
            user_id = message.from_user.id
            print(user_id)

        data = await db.fetch_task(user_id)

        task_id = data['id']
        praise_ = await db.get_praise(data['category'])

        is_done = await db.is_task_done(task_id, user_id)
        # print(is_done)
        if is_done is None:
            text_ = await db.fetch_text_for_category(data['category'])

            markup = InlineKeyboardMarkup(row_width=1)
            button1 = InlineKeyboardButton('💎 Перейти по ссылке', url=data['url'], callback_data='url')
            button2 = InlineKeyboardButton('✅ Я выполнил', callback_data=f'rev:{praise_}:{task_id}')
            button3 = InlineKeyboardButton('❌ Пропустить задание', callback_data=f'skip:{task_id}')
            markup.add(button1, button2, button3)
            print("try")
            await bot.send_message(
                message.chat.id,
                f"➕ Новое задание на {praise_}{VAL}:"
                f"\n\n{text_} \n\n"
                f"2️⃣ Возвращайтесь⚡️сюда, чтобы получить 💰 вознаграждение.",
                reply_markup=markup
            )

            try:
                done_task = await tasks.add_done_task(task_id, user_id, 'offer', 0)

            except exceptions.NotCorrectMessage:
                await message.answer("Не могу записать такую задачу 😢")
                return
        else:
            await message.answer("Кажется, задач пока нет 😢\nПопробуй еще через пару часов!")
            return
    except IndexError:
        await message.answer("Кажется, задач пока нет 😢\nПопробуй еще через пару часов!")
        return

    # @dp.callback_query_handler(lambda c: c.data == 'url')
    # async def button_url(call: types.callback_query):
    #     await db.cheng_following('done_tasks', task_id, user_id)


@dp.callback_query_handler(lambda c: 'rev' in c.data)
async def button_rev(call: types.CallbackQuery):
    user_id = call.from_user.id
    print(user_id)
    rev, praise_, task_id = call.data.split(":")
    await db.cheng_in_doneTask('done_tasks', task_id, user_id)
    await db.balance_update(praise_, user_id)

    markup1 = InlineKeyboardMarkup(row_width=1)
    button_newtask = InlineKeyboardButton("✨Получить новое задание✨", callback_data='new_task')
    markup1.add(button_newtask)

    await bot.edit_message_text(chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=f"Ты выполнил задание!\n\n"
                                     f"Награда: {praise_}{VAL}", )
    # reply_markup=markup1)


@dp.callback_query_handler(lambda c: 'skip' in c.data)
async def button_skip(call: types.CallbackQuery):
    user_id_ = call.from_user.id
    skip, task_id = call.data.split(":")

    await db.skip_in_doneTask('done_tasks', task_id, user_id_)

    markup1 = InlineKeyboardMarkup(row_width=1)
    button_newtask = InlineKeyboardButton("✨Получить новое задание✨", callback_data='new_task')
    markup1.add(button_newtask)

    await bot.edit_message_text(chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=f"Вы отказались от задания.\n\n"
                                     f" Награда: 0{VAL}", )
    # reply_markup=markup1)


# @dp.callback_query_handler(lambda c: c.data == 'new_task')
# async def button_new_task(message: types.Message):
#     await new_task(message)
#     return


async def balance(message: types.Message):
    user_id = message.from_user.id
    balance, counter_or_invite = await db.fetch_balance(user_id)
    await message.answer(f"💰 Мой баланс:\n\n"
                         f"Сумма: {balance}{VAL}\n\n"
                         f"Вы пригласили {counter_or_invite} друзей.")


async def check_for_withdraw(balance, counter_or_invite):
    if counter_or_invite < REFERRALS:
        await bot.edit_message_text(chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=f"Вы пригласили только {counter_or_invite} друзей...\n"
                                         f"А для вывода необходимо {REFERRALS}\n\n"
                                         f"Друзья засчитываются только после того как ОНИ ПЕРЕШЛИ ПО ВАШЕЙ "
                                         f"ССЫЛКЕ-ПРИГЛАШЕНИЮ!")
    elif balance < MIN_WITHDRAW:
        await bot.edit_message_text(chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=f"Вы зарботали только {balance}...\n"
                                         f"А для вывода минимально необходимо {MIN_WITHDRAW}\n\n"
                                         f"Продолжайте выполнять задания! И скоро Вы сможете получить свои деньги!")


class Withdraw(StatesGroup):
    system = State()
    number = State()


async def withdraw(message: types.Message):
    await Withdraw.system.set()

    markup = ReplyKeyboardMarkup(row_width=1)
    button1 = KeyboardButton('QIWI', callback_data='Qiwi')
    button2 = KeyboardButton('YooMoney', callback_data='YoMoney')
    button3 = KeyboardButton('Банковская карта', callback_data='credit_card')
    markup.add(button1, button2, button3)

    await bot.send_message(
        message.chat.id,
        "Выберите платежную систему для вывода:",
        reply_markup=markup
    )


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


@dp.message_handler(lambda message: message.text not in ["QIWI", "YooMoney", "Банковская карта"],
                    state=Withdraw.system)
async def process_category_invalid(message: types.Message):
    """
    In this example category is Wrong.
    """
    return await message.reply("Кажется, ты выбрал что-то не то.\nПопробуй еще раз.")


@dp.message_handler(state=Withdraw.system)
async def system_name(message: types.Message, state: FSMContext):
    """
        system name
    """
    async with state.proxy() as data:
        data['system'] = message.text

    await Withdraw.next()
    markup_ = types.ReplyKeyboardRemove()
    await message.answer("Введите номер счета:", reply_markup=markup_)


@dp.message_handler(state=Withdraw.number)
async def system_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    balance, counter_or_invite = await db.fetch_balance(user_id)

    await Withdraw.next()
    async with state.proxy() as data:
        data['number'] = message.text

    async with state.proxy() as data:
        try:
            if counter_or_invite < REFERRALS:
                await message.answer(f"Вы пригласили только {counter_or_invite} друзей...\n"
                                     f"А для вывода необходимо {REFERRALS}\n\n"
                                     f"Друзья засчитываются только после того как ОНИ ПЕРЕШЛИ ПО ВАШЕЙ "
                                     f"ССЫЛКЕ-ПРИГЛАШЕНИЮ!")
            elif balance < MIN_WITHDRAW:
                await message.answer(f"Вы зарботали только {balance}...\n"
                                     f"А для вывода минимально необходимо {MIN_WITHDRAW}\n\n"
                                     f"Продолжайте выполнять задания! И скоро Вы сможете получить свои деньги!")
            else:
                withdraw = await tasks.add_withdraw(user_id, data['system'], balance, data['number'])
                answer_message = (
                    f"Система вывода: {data['system']}\n"
                    f"Номер счета: {data['number']}\n"
                    f"Размер вывода: {balance}\n"
                    f"До выввода осталось ровно 7 дней!\n\n"
                    f"Можешь продолжить выполнение задач;) Для этого кликни /start"
                )
                await message.answer(answer_message)
                await check_for_withdraw(balance, counter_or_invite)

        except exceptions.NotCorrectMessage:
            await message.answer("Не могу записать запрос на вывод 😢")
            return
        finally:
            await message.answer("Выбери действие", reply_markup=start_markup)


@dp.message_handler(lambda message: message.text)
async def main_handler(message: types.Message):
    if message.text == EARN:
        await new_task(message)
    elif message.text == BALANCE:
        await balance(message)
    elif message.text == WITHDRAW:
        user_id = message.from_user.id
        get_timer = await db.get_timer(user_id)
        empty = []
        if get_timer == empty:
            await withdraw(message)
        else:
            get_timer = get_timer[0][0]
            if tasks.timer_(get_timer) > "0":
                time = tasks.timer(get_timer)
                data = await db.get_withdraw_info(user_id)
                await message.answer(f"Система вывода: {data[0]}\n"
                                     f"Номер счета: {data[2]}\n"
                                     f"Размер вывода: {data[1]}\n"
                                     f"До выввода осталось {time[0]} дней, {time[2]} часов и {time[3]} минут!\n\n"
                                     f"Можешь продолжить выполнение задач;) Для этого кликни /start")
            else:
                await message.answer("Вы нарушили права!")

    elif message.text == INVITE:
        await invite_reply(message)
    elif message.text == HELP:
        await help_reply(message)
    else:
        await message.answer("Что-то пошло не так! Выбери любую из конопок")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
