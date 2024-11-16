import sqlite3
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    # Таблица для хранения информации о группах и их участниках
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS groups (
                   group_id INTEGER NOT NULL,
                   user_id INTEGER NOT NULL,
                   user_name TEXT NOT NULL)
                   """)
    
    # Таблица для хранения долгов
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS debts (
                   group_id INTEGER NOT NULL,
                   user_id_who INTEGER NOT NULL,
                   sum REAL NOT NULL,
                   user_id_towhom INTEGER NOT NULL)
                   """)
    
    conn.commit()

def add_debt_for_one(group_id, user_id, amount, debtor_id):
    cursor.execute("""INSERT INTO debts (
                   group_id, user_id_who, 
                   sum, user_id_towhom) VALUES (?, ?, ?, ?
                   )""", (group_id, user_id, amount, debtor_id))
    conn.commit()
    print(f'Добавлен долг: {amount} от пользователя {debtor_id} к пользователю {user_id}.')


def add_debts_for_all(group_id, user_id, amount):
    cursor.execute("""SELECT user_id
                   FROM groups
                   WHERE group_id = ?
                   GROUP BY user_id
                   """, (group_id,))
    list_of_debtors = cursor.fetchall()
    length = len(list_of_debtors)
    s = round(amount / length, 2)
    l = [(group_id, hui[0], s, user_id) for hui in list_of_debtors if hui[0] != user_id]
    cursor.executemany("""INSERT INTO debts (group_id, user_id_who, sum, user_id_towhom) VALUES (?, ?, ?, ?)""", l)
    conn.commit()

def minimal_money_transfers(group_id):
    # Получаем все операции для заданной группы
    cursor.execute("""
        SELECT user_id_who, SUM(sum) as total_owed, user_id_towhom
        FROM debts
        WHERE group_id = ?
        GROUP BY user_id_who
    """, (group_id,))
    debts = cursor.fetchall()

    # Используем словарь для хранения чистого долга каждого пользователя
    net_balance = {}

    # Обходим все записи долгов и вычисляем чистые долги
    for who, total_owed, towhom in debts:
        net_balance[who] = net_balance.get(who, 0) - total_owed
        net_balance[towhom] = net_balance.get(towhom, 0) + total_owed
    print("Внутри ммт")

    # Составляем список минимальных операций перевода
    transfers = []
    
    # Получаем положительные и отрицательные долги
    creditors = {user: balance for user, balance in net_balance.items() if balance > 0}
    debtors = {user: -balance for user, balance in net_balance.items() if balance < 0}

    # Применяем алгоритм перевода
    while creditors and debtors:
        creditor, credit_amount = creditors.popitem()
        debtor, debt_amount = debtors.popitem()

        transfer_amount = min(credit_amount, debt_amount)
        transfers.append((debtor, creditor, transfer_amount))

        if credit_amount > transfer_amount:
            creditors[creditor] = credit_amount - transfer_amount
        if debt_amount > transfer_amount:
            debtors[debtor] = debt_amount - transfer_amount

    for transfer in transfers:
        print(f"Пользователь {transfer[0]} должен заплатить пользователю {transfer[1]} сумму {transfer[2]}")
        
    return transfers

def add_group_member(group_id, user_id, user_name):
    cursor.execute("""INSERT INTO groups (group_id, user_id, user_name) VALUES (?, ?, ?)""", (group_id, user_id, user_name))
    conn.commit()

def get_group_members(group_id):
    cursor.execute("""SELECT user_id FROM groups WHERE group_id = ?""", (group_id,))
    return [row[0] for row in cursor.fetchall()]

def get_username(user_id):
    cursor.execute("""SELECT user_name FROM groups WHERE user_id = ?""", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else "Unknown"

def get_user_id_by_username(username):
    cursor.execute("""SELECT user_id FROM groups WHERE user_name = ?""", (username,))
    result = cursor.fetchone()
    return result[0] if result else "Unknown"