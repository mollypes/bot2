from datetime import datetime, timedelta
from typing import NamedTuple, Optional

import pytz

import db

TIMER = 168  # 7 days


class Task(NamedTuple):
    id: Optional[int]
    name: str
    url: str
    priority: int
    created: datetime
    deadline: datetime
    category: str
    out_of_deadline: int
    raw_text: str


class DoneTask(NamedTuple):
    id: Optional[int]
    task_id: int
    user_id: str
    status: str
    following_a_link: int


class WithdrawDone(NamedTuple):
    user_id: int
    system: str
    balance: int
    number: int
    timer: str


class Bott(NamedTuple):
    bot_name: str
    bot_api: str


async def add_task(name: str, url: str, priority: int, deadline: int, category: str) -> Task:
    """Добавляет новое сообщение.
    Принимает на вход текст сообщения, пришедшего в бот."""
    created = _get_now_formatted()
    Deadline = deadline__formatted(int(deadline))
    out_of_deadline = 0
    raw_message = name + ', ' + url + ', ' + str(priority) + ', ' + str(deadline) + ', ' + category
    inserted_row_id = db.insert("tasks", {
        "name": name,
        "url": url,
        "priority": priority,
        "created": created,
        "deadline": Deadline,
        "category": category,
        "out_of_deadline": out_of_deadline,
        "raw_text": raw_message,
    })

    return Task(id=None,
                name=name,
                url=url,
                priority=priority,
                created=created,
                deadline=deadline,
                category=category,
                out_of_deadline=out_of_deadline,
                raw_text=raw_message,
                )


async def add_done_task(task_id: int, user_id: int, status: str, following_a_link: int) -> DoneTask:
    """Добавляет новое сообщение.
    Принимает на вход текст сообщения, пришедшего в бот."""
    inserted_row_id = db.insert("done_tasks", {
        "task_id": task_id,
        "user_id": user_id,
        "status": status,
        "following_a_link": following_a_link,
    })
    return DoneTask(id=None,
                    task_id=task_id,
                    user_id=user_id,
                    status=status,
                    following_a_link=following_a_link,
                    )


async def add_withdraw(user_id: int, system: str, balance: int, number: int) -> WithdrawDone:
    """Добавляет новое сообщение.
    Принимает на вход текст сообщения, пришедшего в бот."""
    created = _get_now_formatted()
    timer = deadline__formatted(int(TIMER))
    inserted_row_id = db.insert("withdraw", {
        "user_id": user_id,
        "system": system,
        "balance": balance,
        "number": number,
        "timer": timer,
    })
    return WithdrawDone(user_id=user_id,
                        system=system,
                        balance=balance,
                        number=number,
                        timer=timer,
                        )


async def add_bot(bot_name: str, bot_api: str) -> Bott:
    inserted_row_id = db.insert("bots", {
        "bot_name": bot_name,
        "bot_api": bot_api,
    })
    return Bott(bot_name=bot_name,
                bot_api=bot_api,
                )


def _get_now_formatted() -> str:
    """Возвращает сегодняшнюю дату строкой"""
    return _get_now_datetime().strftime("%Y-%m-%d %H:%M:%S")


def _get_now_datetime() -> datetime:
    """Возвращает сегодняшний datetime с учётом времненной зоны Мск."""
    tz = pytz.timezone("Europe/Moscow")
    now = datetime.now(tz)
    return now


def deadline__formatted(n: int) -> str:
    return _deadline(n).strftime("%Y-%m-%d %H:%M:%S")


def _deadline(n: int) -> datetime:
    deadline = _get_now_datetime() + timedelta(days=n)
    return deadline


def timer_(time: str):
    timer = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    timer__ = timer - now
    return str(timer__)

def timer(time: str):
    timer = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    timer_ = timer - now
    item = str(timer_).split('.')
    item1 = item[0].split(",")
    item2 = item1[0].split() + item1[1].split(":")
    return item2