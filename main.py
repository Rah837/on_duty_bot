from vk_api import VkApi
from vk_api.bot_longpoll\
    import VkBotLongPoll, VkBotEventType

from copy import copy

import time

import json



ADMIN_ID = 273345651
GROUP_ID = 178757316

TOKEN = "83a23c3123f2eceeb1cfc311a61ea7a78d9ca531e41157d7a9724b7090f2d5ee164448c42e91986f9e64b"

ON_DUTIES_FILE_NAME = "on_duties.json"
CHAT_IDS_FILE_NAME = "chat_ids.json"

COMMANDS = {
    "add new on duty ": "add",
    "delete this on duty ": "del",
    "today was on duty ": "on",
    "today can not be on duty ": "cant",
    "Null": "Null",
}


time_midnight = False


def is_empty(dict):
    return not bool(dict)

def now():
    return time.gmtime(time.time())

def is_midnight(time):
    global time_midnight

    last = time_midnight
    time_midnight = time.tm_hour + 3 == 9

    return time_midnight and not last


class Group:
    def __init__(self, session):
        try:
            with open(ON_DUTIES_FILE_NAME) as file:
                self.on_duties = json.load(file)           
        except FileNotFoundError:
            self.on_duties = {}

        try:
            with open(CHAT_IDS_FILE_NAME) as file:
                self.chat_ids = json.load(file)
        except FileNotFoundError:
            self.chat_ids = []

        self.able_on_duties = {}

        self.session = session

    def __del__(self):
        with open(ON_DUTIES_FILE_NAME, "w") as file:
            json.dump(self.on_duties, file, indent=4)

        with open(CHAT_IDS_FILE_NAME, "w") as file:
            json.dump(self.chat_ids, file, indent=4)

    def on_message(self, text, id):
        if text == "who is on duty?":
            message = "nobody is on duty"\
                if is_empty(self.able_on_duties)\
                else self.able_on_duties_string()
                
            self.send(id, message)

        if text == "who must be on duty today?":
            message = "no one can be on duty today"\
                if is_empty(self.able_on_duties)\
                else "today must be on duty {}"\
                    .format(self.on_duty_today())
                
            self.send(id, message)

        if text == "add this chat":
            self.chat_ids.append(id)
            self.send(id, "this chat was added")

        if text == "delete this chat":
            try:
                self.chat_ids.remove(id)
                self.send(id, "this chat was removed")
            except ValueError:
                self.send(id, "this chat was not listed")

        return False

    def on_command(self, cmd, arg, id):
        if cmd == "cant":
            if arg in self.able_on_duties:
                del self.able_on_duties[arg]

                message = "today there is no one on duty"\
                    if is_empty(self.able_on_duties)\
                    else "then today must be on duty {}"\
                        .format(self.on_duty_today())
                    
                self.send(id, message)
            else:
                self.send(id, "this student is not on duty today")

        return False


    def on_admin_message(self, text, id):
        if text == "stop":
            return True

        if text == "update":
            self.update()

        return False

    def on_admin_command(self, cmd, arg, id):
        if cmd == "add":
            if arg in self.on_duties:
                self.send(id, "this student is already on duty")
            else:
                self.on_duties[arg] = 0 if is_empty(self.on_duties)\
                    else max(self.on_duties.values())
                self.send(id, "{} was added".format(arg))

        if cmd == "del":
            if arg in self.on_duties:
                del self.on_duties[arg]
                self.send(id, "{} was deleted".format(arg))
            else:
                self.send(id, "this student is not on duty")


        return False


    def update(self):
        if not is_empty(self.able_on_duties):
            self.on_duties[self.on_duty_today()] += 1

        self.able_on_duties = copy(self.on_duties)

        if not is_empty(self.able_on_duties):
            for id in self.chat_ids:
                self.send(id, "today must be on duty {}"\
                    .format(self.on_duty_today()))

    def send(self, id, message):
        self.session.method("messages.send", {
            "peer_id": id,
            "random_id": 0,
            "message": message
        })

    def able_on_duties_string(self):
        string = "on duty:\n"

        for student in self.able_on_duties:
            string += "{} was on duty: {}\n"\
                .format(student, str(self.able_on_duties[student]))

        return string

    def on_duty_today(self):
        return min(self.able_on_duties, key=self.able_on_duties.get)


def main_loop(group, longpoll):
    while True:
        if is_midnight(now()):
            group.update()
        
        events = longpoll.check()
        for bot_event in events:
            if bot_event.type == VkBotEventType.MESSAGE_NEW:
                event = bot_event.object
                src = event.text
                text = src.lower()

                cmd = next((cmd for cmd in COMMANDS if text.startswith(cmd)), "Null")
                short = COMMANDS[cmd]
                arg = src[len(cmd):]

                if group.on_message(text, event.peer_id)\
                    or group.on_command(short, arg, event.peer_id):
                    return

                if event.from_id == ADMIN_ID:
                    if group.on_admin_message(text, event.peer_id)\
                        or group.on_admin_command(short, arg, event.peer_id):
                        return

def main():
    vk_session = VkApi(token=TOKEN, api_version="5.92")
    group = Group(vk_session)
    longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)

    main_loop(group, longpoll)

if __name__ == "__main__":
    main()