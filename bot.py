import logging
import telebot
from telebot import types
from db import *

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CREATE_BILL, ADD_FRIENDS, MARK_PAYMENT, GROUP_TRIP, TRACK_DEBTS = range(5)

# Словарь для хранения ожидаемых участников
expected_participants = {}

# Замените 'YOUR_TOKEN' на токен вашего бота
bot = telebot.TeleBot("{{sensitive_data}}")

markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
markup.add(types.KeyboardButton(text="/menu"))

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Я бот для отслеживания общих расходов. Что вы хотите сделать?\n'
                                      '/create_bill - Создать новый счет\n'
                                      '/group_trip - Создать групповую поездку\n'
                                      '/track_debts - Отследить долги\n'
                                      '/pay - Заплатить долг', reply_markup=markup )

# Команда /menu
@bot.message_handler(commands=['menu'])
def menu(message):
    bot.send_message(message.chat.id, 'Вы в меню. Что вы хотите сделать?\n'
                                      '/create_bill - Создать новый счет\n'
                                      '/track_debts - Отследить долги\n'
                                      '/pay - Заплатить долг', reply_markup=markup )

# Команда /create_bill
@bot.message_handler(commands=['create_bill'])
def create_bill(message):
    bot.send_message(message.chat.id, 'Введите название счета:', reply_markup=markup)
    bot.register_next_step_handler(message, create_bill_name)

# Обработка названия счета
def create_bill_name(message):
    bill_name = message.text
    bot.send_message(message.chat.id, 'Введите сумму счета:', reply_markup=markup)
    bot.register_next_step_handler(message, create_bill_amount, bill_name)

# Обработка суммы счета
def create_bill_amount(message, bill_name):
    bill_amount = float(message.text)
    bot.send_message(message.chat.id, 'Введите количество участников счета:', reply_markup=markup)
    bot.register_next_step_handler(message, create_bill_participants, bill_name, bill_amount)

# Обработка количества участников
def create_bill_participants(message, bill_name, bill_amount):
    num_participants = int(message.text)
    expected_participants[message.chat.id] = dict()
    expected_participants[message.chat.id]['num_participants'] = num_participants
    expected_participants[message.chat.id]['participants'] = []
    expected_participants[message.chat.id]['usernames'] = []
    expected_participants[message.chat.id]['bill_name'] = bill_name
    expected_participants[message.chat.id]['bill_amount'] = bill_amount
    bot.send_message(message.chat.id, f'Пожалуйста, каждый участник должен нажать кнопку "JOIN". Сначала пишет {message.from_user.first_name}, ему должны! Ожидается {num_participants} участников.', reply_markup=types.InlineKeyboardMarkup([[types.InlineKeyboardButton("JOIN", callback_data="join")]]))

# Обработка нажатия кнопки "JOIN"
@bot.callback_query_handler(func=lambda call: call.data == "join")
def join(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name  # Используем username, если есть, иначе first_name
    if chat_id in expected_participants.keys() and len(expected_participants[chat_id]['participants']) < expected_participants[chat_id]['num_participants']:
        if user_id not in expected_participants[chat_id]['participants']:
            expected_participants[chat_id]['participants'].append(user_id)
            expected_participants[chat_id]['usernames'].append(username)
            add_group_member(chat_id, user_id, username)
            bot.send_message(chat_id, f'Участник {username} добавлен в список.')
            if len(expected_participants[chat_id]['participants']) == expected_participants[chat_id]['num_participants']:
                bill_name = expected_participants[chat_id]['bill_name']
                bill_amount = expected_participants[chat_id]['bill_amount']
                participants_id = expected_participants[chat_id]['participants']
                participants_un = expected_participants[chat_id]['usernames']
                add_debts_for_all(chat_id, participants_id[0], bill_amount)
                bot.send_message(chat_id, f'Счет "{bill_name}" на сумму {bill_amount} создан для друзей: {", ".join(participants_un)}')
                del expected_participants[chat_id]
        else:
            bot.send_message(chat_id, 'Вы уже добавлены в список.')
    else:
        bot.send_message(chat_id, 'Команда /join не применима в этом чате.')

# Команда /group_trip
@bot.message_handler(commands=['group_trip'])
def group_trip(message):
    bot.send_message(message.chat.id, 'Введите название поездки:', reply_markup=markup)
    bot.register_next_step_handler(message, group_trip_name)

# Функция /pay
@bot.message_handler(commands=['pay'])
def pay(message):
    # bot.send_message(message.chat.id, "Формат ввода: /pay <сумма> <кому перевод>\n"
    #                                    "Пример: /pay 330 user812", reply_markup=markup )
    s = message.text.split()
    
    if(len(s) == 3):
        print('Зашол в иф')
        minimal_transfers = minimal_money_transfers(message.chat.id)
        debt_whom = get_user_id_by_username(s[2])
        print("после дебт хом")
        pay_amount = float(s[1])
        who1 = 0
        whom1 = 0
        amount1 = 0
        for who, whom, amount in minimal_transfers:
            if(who == message.from_user.id and whom == debt_whom):
                who1 = who
                whom1 = whom
                amount1 = amount
                if(amount < pay_amount):
                    bot.send_message(message.chat.id, "Сумма погашения должна быть меньше либо равной сумме долга")
                    return
                else:
                    break

        add_debt_for_one(message.chat.id, debt_whom, pay_amount, message.from_user.id)
        name_who = get_username(who1)
        name_whom = get_username(whom1)
        if(amount1 == pay_amount):
            bot.send_message(message.chat.id, f"Долг {name_who} пользователю {name_whom} успешно погашен!")
        else:
            bot.send_message(message.chat.id, f"Долг {name_who} пользователю {name_whom} уменьшен на {pay_amount} руб. Теперь: {amount-pay_amount}")

    
    else:
        bot.send_message(message.chat.id, "Введите команду в формате: /pay SUM USERNAME")


# Обработка названия поездки
def group_trip_name(message):
    trip_name = message.text
    bot.send_message(message.chat.id, f'Поездка "{trip_name}" создана. Теперь вы можете добавлять счета.', reply_markup=markup)

# Команда /track_debts
@bot.message_handler(commands=['track_debts'])
def track_debts(message):
    bot.send_message(message.chat.id, 'Все долги в этом чате:\n', reply_markup=markup)
    
    minimal_transfers = minimal_money_transfers(message.chat.id)

    if minimal_transfers == []:
        bot.send_message(message.chat.id, "Долгов нет")
    else:
        for who, whom, amount in minimal_transfers:
            name_who = get_username(who)
            name_whom = get_username(whom)
            bot.send_message(message.chat.id, f"{name_who} должен {amount} руб. пользователю {name_whom}")

# Основная функция
def main():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    init_db()
    main()