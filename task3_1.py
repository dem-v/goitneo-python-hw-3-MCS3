from collections import UserDict, defaultdict
from datetime import datetime
import pickle

MAX_DELTA_DAYS = 7
WEEKDAYS_LIST = [datetime(year=2001, month=1, day=i).strftime('%A') for i in range(1,8)]
BINARY_STORAGE_FILENAME = 'dump.pickle'

class DefaultExecutionDict(UserDict):
    def __getitem__(self, key):
        if not key in self.data.keys():
            return DEFAULT_METHOD
        else:
            return self.data.get(key)


def input_error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyExistInContacts as e:
            return f"This contact exists {e}."
        except KeyNotExistInContacts as e:
            return f"This contact does not exist {e}."
        except KeyError as e:
            return f"This contact does not exist {e}."
        except IndexError:
            return f"Bad arguments {args[1:]}."
        except BadPhoneNumber as e:
            return f"The phone number {e} does not match the requirements."
        except PhoneNumberIsMissing as e:
            return f"This number does not exist {e}."
        except BadBirthdayFormat as e:
            return f"Birthday format '{e}' is incorrect. It should be DD.MM.YYYY."

    return inner


class KeyExistInContacts(Exception):
    pass


class KeyNotExistInContacts(Exception):
    pass


class BadPhoneNumber(Exception):
    pass


class PhoneNumberIsMissing(Exception):
    pass


class BadBirthdayFormat(Exception):
    pass


class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return self.value == other.value


class Name(Field):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return str(self.value) == str(other.value)


class Phone(Field):
    def __init__(self, value):
        if len(value) == 10 and value.isnumeric():
            self.value = value
        else:
            raise BadPhoneNumber(value)

    def __str__(self):
        return str(self.value)


class Birthday:
    def __init__(self, value):
        if type(value) == str:
            self.value = datetime.strptime(value, '%d.%m.%Y')
        elif type(value) == datetime:
            self.value = value

    def __str__(self):
        return str(self.value.strftime('%d.%m.%Y'))

    def __eq__(self, other):
        if type(other) == str:
            return self.value.date == datetime.strptime(other, '%d.%m.%Y').date
        elif type(other) == datetime:
            return self.value.date == other.value.date
        else:
            return False


class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def __str__(self):
        return f"Contact name: {self.name.value}, phones: {'; '.join(p.value for p in self.phones)}{f', birthday {self.show_birthday()}' if self.birthday is not None else ''}"

    def __eq__(self, __value: object) -> bool:
        return self.name == __value.name and not bool(
            set(self.phones).intersection(__value.phones)
        )

    @input_error
    def add_phone(self, phone: str):
        p = Phone(phone)
        self.phones.append(p)

    @input_error
    def edit_phone(self, orig_phone: str, new_phone: str):
        a = Phone(orig_phone)
        b = Phone(new_phone)

        try:
            ind = self.phones.index(a)
        except ValueError:
            raise PhoneNumberIsMissing(orig_phone)

        self.phones[ind] = b

    @input_error
    def remove_phone(self, phone: str):
        p = Phone(phone)
        self.phones.remove(p)

    @input_error
    def find_phone(self, phone: str):
        p = Phone(phone)
        return p if p in self.phones else None
    
    @input_error
    def add_birthday(self, value):
        try:
            self.birthday = Birthday(value)
        except ValueError:
            raise BadBirthdayFormat(value)
        
    def show_birthday(self):
        return str(self.birthday)
            

class AddressBook(UserDict):
    def add_record(self, rec: Record):
        self.data[str(rec.name)] = rec

    def find(self, name: str):
        if not name in self.data.keys():
            return None
        else:
            return self.data.get(name)

    def delete(self, name: str):
        if name in self.data.keys():
            _ = self.data.pop(name)
            
    def get_birthdays_per_week(self) -> str:
        user_bd_by_weekday = defaultdict(list)
        current_date = datetime.today().date()
        for name, user in self.data.items():
            if user.birthday is None:
                continue
            
            birthday = user.birthday.value.date() 
            birthday_this_year = birthday.replace(year=current_date.year)
            
            today_distance = (birthday_this_year - current_date).days
            #let's not forget about those who had birthday on weekend and today is Monday
            if today_distance < 0:
                today_distance = (birthday_this_year.replace(year=current_date.year + 1) - current_date).days
                if today_distance > MAX_DELTA_DAYS:
                    continue
            
            if today_distance > MAX_DELTA_DAYS:
                continue
            
            bd_week_day = birthday_this_year.weekday()
            
            if (bd_week_day == 5 and today_distance < MAX_DELTA_DAYS - 2) or (bd_week_day == 6 and today_distance < MAX_DELTA_DAYS - 1):
                bd_week_day = 0
                
            bd_week_day_name = WEEKDAYS_LIST[bd_week_day]
            
            user_bd_by_weekday[bd_week_day_name].append(name)

        return ''.join(['{}: {}\n'.format(d, user_bd_by_weekday[d]) for d in user_bd_by_weekday if len(user_bd_by_weekday[d]) > 0])


def parse_input(user_input):
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, *args


@input_error
def write_contact(contacts, args, is_change=False, *_):
    if len(args) != 2:
        raise IndexError()
    name, phone = args

    rec = contacts.find(name)
    if rec is not None and not is_change:
        raise KeyExistInContacts(name)
    elif rec is None and is_change:
        raise KeyNotExistInContacts(name)

    if not is_change: 
        rec = Record(name)
        a = rec.add_phone(phone)
        if a is not None:
            return a
        contacts.add_record(rec)
    else:
        if len(rec.phones) == 0:
            return f"Contact {name} doesn't have phone numbers."
        a = rec.edit_phone(str(rec.phones[0]), phone)
        if a is not None:
            return a

    return f"Contact {name} {'changed' if is_change else 'added'}."

@input_error
def write_contact_add(contacts, args, *_):
    if len(args) != 2:
        raise IndexError()
    name, phone = args

    rec = contacts.find(name)
    if rec is not None:
        raise KeyExistInContacts(name)

    rec = Record(name)
    a = rec.add_phone(phone)
    if a is not None:
        return a
    contacts.add_record(rec)

    return f"Contact {name} added."

@input_error
def write_contact_change(contacts, args, *_):
    if len(args) != 3:
        raise IndexError()
    name, phone_old, phone_new = args

    rec = contacts.find(name)
    if rec is None:
        raise KeyNotExistInContacts(name)

    if len(rec.phones) == 0:
        return f"Contact {name} doesn't have phone numbers."
    p = rec.find_phone(phone_old)
    if p is None:
        return f"Contact {name} doesn't have phone number {phone_old}."
    a = rec.edit_phone(str(p), phone_new)
    if a is not None:
        return a

    return f"Contact {name} updated."


@input_error
def get_phone(contacts, args, *_):
    name = args[0]
    if name not in contacts.keys():
        raise KeyNotExistInContacts(name)
    return f"{contacts[name]}"


@input_error
def add_birthday(contacts: AddressBook, args, *_):
    if len(args) != 2:
        raise IndexError()
    name, birthday = args

    rec = contacts.find(name) 
    if rec is None:
        raise KeyNotExistInContacts(name)

    a = rec.add_birthday(birthday)
    if a is not None:
        return a
    return f"Set birthday for contact {name} at {birthday}."


@input_error
def get_birthday(contacts, args, *_):
    name = args[0]
    rec = contacts.find(name) 
    if rec is None:
        raise KeyNotExistInContacts(name)
    return f"Birthday of {name} is at {rec.show_birthday()}"


def show_all_birthdays_for_week(contacts: AddressBook, *_):
    return contacts.get_birthdays_per_week()


def print_phonebook(contacts, *_):
    return "\n".join(["{}".format(v) for _, v in contacts.items()])


def print_goodbye(*_):
    return "Good bye!"


def print_hello(*_):
    return "How can I help you?"


def print_bad(*_):
    return "Invalid command."


OPERATIONS = DefaultExecutionDict(
    {
        "close": print_goodbye,
        "exit": print_goodbye,
        "hello": print_hello,
        "add": write_contact_add,
        "change": write_contact_change,
        "phone": get_phone,
        "all": print_phonebook,
        "add-birthday": add_birthday,
        "show-birthday": get_birthday,
        "birthdays": show_all_birthdays_for_week,
    }
)

DEFAULT_METHOD = print_bad


def main():
    try:
        with open(BINARY_STORAGE_FILENAME, 'rb') as fh:
            book = pickle.load(fh) 
        print("Loaded previous address book")
    except Exception as e:
        print(f"Previous address book could not be loaded. {e} \nInitializing new one.")
        book = AddressBook()
        
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")
        command, *args = parse_input(user_input)

        print(
            OPERATIONS[command](book, args)
        )
        if command in ["close", "exit"]:
            break
        
    retry = True
    while retry:
        retry = False
        try:
            with open(BINARY_STORAGE_FILENAME, 'wb') as fh:
                pickle.dump(book, fh)
            print("The address book was saved")
        except Exception as e:
            print(f"The address book could not be saved. Error: {e}")
            a = input("Would you like to retry? (y/n, default n)")
            if a == 'y' or a[0] == 'y':
                retry = True


if __name__ == "__main__":
    main()

