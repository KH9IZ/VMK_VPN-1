"""FAQ menu implementation."""

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telebot.formatting import mbold
from models import QuestionAnswer

class FaqMenu:
    """Inline keyboard for FAQ."""

    back_button_text: str = "«Back"
    faq_title_text: str = "Frequently asked questions"
    __bot: TeleBot = None
    __markups_stack: list[tuple[str, InlineKeyboardMarkup]] = []
    QUESTION_PREFIX: str = "faq_question_"
    BACK_BUTTON_DATA: str = "faq_back"

    def __init__(self, bot: TeleBot, title: str, back_button_text: str):
        """Init new FAQ menu handler."""
        self.__bot = bot
        self.back_button_text = back_button_text
        self.faq_title_text = title

    def __save_last_menu(self, call: CallbackQuery) -> None:
        """Save last menu to stack.

        This menu will be opened on back button.
        """
        self.__markups_stack.append((call.message.text, call.message.reply_markup))

    def __add_back_button(self, markup: InlineKeyboardMarkup) -> None:
        """Add back button to a markup."""
        markup.add(InlineKeyboardButton(self.back_button_text,
                                        callback_data=self.BACK_BUTTON_DATA))

    @staticmethod
    def __create_default_markup() -> InlineKeyboardMarkup:
        """Create markup with default settings."""
        markup = InlineKeyboardMarkup()
        markup.row_width = 1
        return markup

    def __gen_faq_markup(self) -> InlineKeyboardMarkup:
        """Create inline keyboard for FAQ."""
        markup = FaqMenu.__create_default_markup()
        query = QuestionAnswer.select()
        for question in query:
            data = self.QUESTION_PREFIX + str(question.id)
            markup.add(InlineKeyboardButton(question.question,
                                            callback_data=data))
        self.__add_back_button(markup)
        return markup

    def __gen_question_markup(self) -> InlineKeyboardMarkup:
        """Create inline keyboard for question and answer."""
        markup = FaqMenu.__create_default_markup()
        self.__add_back_button(markup)
        return markup

    def __get_message_for_question(self, data: str) -> str:
        """Return formatted message with question and the answer."""
        question_id = int(data.removeprefix(self.QUESTION_PREFIX))
        query = QuestionAnswer.select().where(QuestionAnswer.id == question_id).limit(1)
        message_text = mbold(query[0].question) + '\n\n' + query[0].answer
        return message_text

    def handle_menu_query(self, call: CallbackQuery) -> None:
        """Handle FAQ menu.

        Last menu will be saved in stack, and in keyboard the "back"
        button will be added. On back event the previous menu text and
        markup will be popped from the stack.
        """
        self.__save_last_menu(call)
        self.__bot.edit_message_text(self.faq_title_text, call.message.chat.id,
                              call.message.message_id, reply_markup=self.__gen_faq_markup())

    def handle_back_query(self, call: CallbackQuery) -> None:
        """Handle back button.

        Take menu from stack.
        """
        last_menu = self.__markups_stack.pop()
        if last_menu is not None and last_menu:
            self.__bot.edit_message_text(last_menu[0], call.message.chat.id,
                                  call.message.message_id, reply_markup=last_menu[1])
        else:
            raise ValueError("No previous menu found!")

    def handle_question(self, call: CallbackQuery) -> None:
        """Handle FAQ question button."""
        self.__save_last_menu(call)
        self.__bot.edit_message_text(self.__get_message_for_question(call.data),
                                     call.message.chat.id,
                                     call.message.message_id,
                                     reply_markup=self.__gen_question_markup(),
                                     parse_mode='MARKDOWN')
