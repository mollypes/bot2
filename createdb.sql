create table tasks(
    id integer primary key,
    name text,
    url text,
    priority integer,
    created datetime,
    deadline datetime,
    category text,
    out_of_deadline integer,
    raw_text text
);


create table done_tasks(
    id integer primary key,
    task_id integer,
    user_id integer,
    status text,
    following_a_link integer
);


create table category_name(
    id integer primary key,
    category text,
    Text_for_category text,
    praise int
);


create table user_info(
    user_id int,
    bot_api text,
    counter_or_invite int,
    balance real,
    status int,
    status_for_wr text
);


create table withdraw(
    user_id int,
    system text,
    balance real,
    number text,
    timer datetime
);

create table bots(
    bot_name text,
    bot_api text
);

create table texts(
    command text,
    text text
);


insert into category_name (category, Text_for_category, praise)
values
    ("Подписка Inst", "🔽Скорее подписывыйся на этого пользователя Instagram🔽", "0"),
    ("Лайк Inst", "📷Срочно поставь лайк этому посту в Instagram 📷", "0"),
    ("Подписка на канал", "Подпишись на канал и получи свои бонусы 💸", "0"),
    ("Подписка на Tik-Tok", "🔽Скорее подписывыйся на этого пользователя Tik-Tok🔽", "0"),
    ("Перейти на сайт", "Кликай по ссылке и переходи на сайт 📲", "0"),
    ("Подписка ВК", "Подпишись и получи свои бонусы 💸", "0"),
    ("Лайк ВК", "Тут ждут твоего лайка ❤", "0"),
    ("Пpослушивание музыки ВК", "🎧 Послушай это! 🎧", "0"),
    ("Другое", "0", "0");


insert into texts (command)
values
    ("❓ Помощь")



