import telebot
from dotenv import load_dotenv
from os import getenv
from manage_establishments import add_establishment
from get_establishments import get_establishments

# Load environmental variables
load_dotenv()

# Set up environment variables
BOT_TOKEN = getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Welcome Message Handler
@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "👋 Hey there! What's cookin'? 🍽️")

# Add Establishment Message Handler
@bot.message_handler(commands=['add'])
def add_handler(message):
    bot.reply_to(message, "🍴 What's the name of the restaurant you'd like to add?")
    bot.register_next_step_handler(message, add_establishment_process_step)

def add_establishment_process_step(message):
    establishment_name = message.text

    try:
        bot.reply_to(message, "👨‍🍳 Chef's kiss! 🤤 I'm adding it to your list. I'll pop you a message as soon as I'm done 🤞")
        add_establishment(establishment_name)
        bot.reply_to(message, f"🙌 {establishment_name} has been added to your list!")
    except Exception as e:
        # Send an error message back to the user
        bot.reply_to(message, "Oops! 🙊 Something went wrong when I tried adding this restaurant. Try again later?")
        # Print the error message to the console for debugging
        print(f"An error occurred while adding {establishment_name}: {e}")

# Search Establishment Message Handler
@bot.message_handler(commands=['search'])
def search_handler(message):
    bot.reply_to(message, "🕵️ What restaurant are you in the mood for? 🤔")
    bot.register_next_step_handler(message, search_process_step)

def search_process_step(message):
    establishment_name = message.text

    try:
        bot.reply_to(message, "⏳ I'm on it! One second please while I search for that restaurant 🔍")
        establishments = get_establishments(establishment_name)
        if establishments:
            bot.reply_to(message, f"👀 Whoa! Look at all these restaurants with '{establishment_name}' in them! 😲\n\n{establishments}")
        else:
            bot.reply_to(message, f"👎 Golly gee, {establishment_name} doesn't appear to be in my list. 👻")
    except Exception as e:
        # Send an error message back to the user
        bot.reply_to(message, "Oops! 🙊 Something went wrong when I tried searching for this restaurant. Try again later?")
        # Print the error message to the console for debugging
        print(f"An error occurred while searching for {establishment_name}: {e}")

# Call bot.polling in a try-Except block to prevent the code from crashing
if __name__ == "__main__":
    try:
        bot.polling()
    except Exception as e:
        print(e)
