import datetime
import os
from typing import Dict, List, Tuple

import sqlite3

import tasks


conn = sqlite3.connect(os.path.join("db", "tasks.db"))
cursor = conn.cursor()

USER_INFO = 'user_info'


def insert(table: str, column_values: Dict):
    columns = ', '.join(column_values.keys())
    values = [tuple(column_values.values())]
    placeholders = ", ".join("?" * len(column_values.keys()))
    cursor.executemany(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders});", values
    )
    conn.commit()


def insert_user(user_id: int, bot_api: str):
    # status 0 - active, 1 - bloc
    cursor.execute(f"SELECT {user_id} FROM {USER_INFO} WHERE user_id = {user_id}")
    rows = cursor.fetchall()

    update_status_of_user(user_id, 0)

    example = []
    if rows == example:
        values = [user_id, bot_api, 0, 0.0, 0]
        cursor.execute(
            f"INSERT INTO {USER_INFO} (user_id, bot_api, counter_or_invite, balance, status)"
            f" VALUES (?, ?, ?, ?, ?);", values
        )
        conn.commit()
    else:
        return -1


def update_status_of_user(user_id: int, status: int):
    cursor.execute(f"UPDATE {USER_INFO} SET status = {status} "
                   f"WHERE user_id = {user_id}")
    conn.commit()


async def update_referral(user_id: int):
    cursor.execute(f"UPDATE {USER_INFO} SET counter_or_invite = counter_or_invite + 1 "
                   f"WHERE user_id = {user_id}")
    conn.commit()


async def update_balance_referral(user_id: int):
    cursor.execute(f"UPDATE {USER_INFO} SET balance = balance + 100 "
                   f"WHERE user_id = {user_id}")
    conn.commit()


# not_use
def get_counter_of_invite(user_id: int):
    cursor.execute(f"SELECT counter_or_invite FROM {USER_INFO} WHERE user_id = {user_id}")
    rows = cursor.fetchall()
    return rows


def get_bots():
    cursor.execute(f"SELECT * FROM bots")
    rows = cursor.fetchall()
    return dict(rows)


def get_bot_users(bot_api: str, status: int):
    cursor.execute(f"SELECT user_id FROM user_info WHERE bot_api like \'{bot_api}\' and status={status}")
    rows = cursor.fetchall()
    rows_list = []
    for row in rows:
        rows_list.append(row[0])
    return rows_list


async def get_timer(user_id: int):
    cursor.execute(f"SELECT timer FROM withdraw WHERE user_id = {user_id}")
    rows = cursor.fetchall()
    return rows


async def get_withdraw_info(user_id: int):
    cursor.execute(f"SELECT system, balance, number FROM withdraw WHERE user_id = {user_id}")
    rows = cursor.fetchall()
    return rows[0]


async def fetchall(table: str, columns: List[str], task_id: int) -> List[Tuple]:
    columns_joined = ", ".join(columns)
    cursor.execute(f"SELECT {columns_joined} FROM {table} WHERE id={task_id}")
    rows = cursor.fetchall()
    result = []
    for row in rows:
        dict_row = {}
        for index, column in enumerate(columns):
            dict_row[column] = row[index]
        result.append(dict_row)
    return result[0]


# not_use
def update_done_task(id: int):
    cursor.execute(f"UPDATE done_tasks SET following_a_link=1 where id={id}")
    conn.commit()


def fetchall_names():
    cursor.execute(f"SELECT id, name FROM tasks where out_of_deadline=0")
    rows = cursor.fetchall()
    print("categori 0")
    return rows


def fetchall_negative_names():
    cursor.execute(f"SELECT id, name FROM tasks where out_of_deadline=1")
    rows = cursor.fetchall()
    print("categori 1")
    return rows


async def fetch_task(user_id: int):
    user_id = int(user_id)
    list_ = ['id', 'url', 'deadline', 'category']
    columns_joined = ", ".join(list_)
    cursor.execute(f"SELECT {columns_joined} FROM tasks "
                   f"WHERE out_of_deadline=0 AND "
                   f"NOT EXISTS"
                   f"(SELECT task_id, user_id FROM done_tasks "
                   f"where done_tasks.task_id=tasks.id "
                   f"and done_tasks.user_id={user_id})"
                   f"ORDER BY priority DESC, created DESC")

    rows = cursor.fetchall()
    print(rows)
    task_dict = {}
    time = datetime.datetime.now()

    for i in range(len(list_)):
        task_dict[list_[i]] = rows[0][i]
    if str(task_dict['deadline']) < str(time):
        out_of_deadline_update('tasks', task_dict['id'])
        fetch_task(user_id)
    return task_dict


def update_deadline_status():
    list_ = ['id', 'url', 'deadline', 'category']
    columns_joined = ", ".join(list_)
    cursor.execute(f"SELECT {columns_joined} FROM tasks "
                   f"WHERE out_of_deadline=0")

    rows = cursor.fetchall()
    print(rows)
    task_dict = {}
    time = datetime.datetime.now()

    for item in rows:
        if str(item[2]) < str(time):
            out_of_deadline_update('tasks', item[0])


async def fetch_text_for_category(category: str):
    category_ = str(category)
    cursor.execute(f"SELECT Text_for_category FROM category_name where category like \'{category_}\'")
    rows = cursor.fetchall()
    return rows[0][0]


async def fetch_text_for_command(command: str):
    command_ = str(command)
    cursor.execute(f"SELECT text FROM texts where command like \'{command_}\'")
    rows = cursor.fetchall()
    return rows[0][0]


async def balance_update(praise, user_id):
    cursor.execute(f"UPDATE {USER_INFO} SET balance=balance+{praise} where user_id={user_id}")
    conn.commit()
    return


async def fetch_balance(user_id):
    cursor.execute(f"SELECT balance, counter_or_invite FROM {USER_INFO} where user_id={user_id}")
    rows = cursor.fetchall()
    return rows[0]


async def is_task_done(task_id: int, user_id: int):
    cursor.execute(f"SELECT id FROM done_tasks where task_id={task_id} and user_id={user_id}")
    rows = cursor.fetchall()
    if not rows:
        return None
    else:
        return rows[0][0]


async def get_praise(category: str):
    category_ = str(category)
    cursor.execute(f"SELECT praise FROM category_name where category like \'{category_}\'")
    rows = cursor.fetchall()
    return rows[0][0]


async def delete(table: str, row_id: int) -> None:
    row_id = int(row_id)
    cursor.execute(f"delete from {table} where id={row_id}")
    conn.commit()


def restatr_task(row_id: int) -> None:
    row_id = int(row_id)
    cursor.execute(f"delete from done_tasks where task_id={row_id}")
    conn.commit()


def out_of_deadline_update(table: str, row_id: int) -> None:
    cursor.execute(f"UPDATE {table} SET out_of_deadline=1 where id={row_id}")
    conn.commit()


def get_priority(row_id: int):
    row_id = int(row_id)
    cursor.execute(f"SELECT name, priority, deadline FROM tasks where id={row_id}")
    rows = cursor.fetchall()
    print('........')
    print(rows)
    return rows[0]


def cheng_priority(row_id: int, priority: int):
    row_id = int(row_id)
    cursor.execute(f"UPDATE tasks SET priority={priority} where id={row_id}")
    conn.commit()


async def cheng_deadline(row_id: int, deadline):
    row_id = int(row_id)

    data = await fetchall("tasks", ['name', 'url', 'priority', 'created', 'deadline', 'category', 'out_of_deadline'],
                          row_id)
    task = await tasks.add_task(data['name'], data['url'], data['priority'], deadline, data['category'])
    await delete("tasks", row_id)


async def cheng_in_doneTask(table: str, task_id: int, user_id: int):
    cursor.execute(f"UPDATE {table} SET status=\'done\' where task_id={task_id} and user_id={user_id}")
    conn.commit()
    return


async def skip_in_doneTask(table: str, task_id: int, user_id: int):
    cursor.execute(f"UPDATE {table} SET status=\'skip\' where task_id={task_id} and user_id={user_id}")
    conn.commit()
    return


async def cheng_following(table: str, task_id: int, user_id: int):
    cursor.execute(f"UPDATE {table} SET following_a_link=1 where task_id={task_id} and user_id={user_id}")
    conn.commit()


def get_cursor():
    return cursor


def _init_db():
    """Инициализирует БД"""
    with open("createdb.sql", "r", encoding='utf-8') as f:
        sql = f.read()
    cursor.executescript(sql)
    conn.commit()


def check_db_exists():
    """Проверяет, инициализирована ли БД, если нет — инициализирует"""
    cursor.execute("SELECT name FROM sqlite_master "
                   "WHERE type='table' AND name='tasks'")
    table_exists = cursor.fetchall()
    if table_exists:
        return
    _init_db()


check_db_exists()
