import telebot
from dotenv import load_dotenv
from os import getenv
from add_establishment import add_location
from get_establishments import get_establishments
import requests

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
        bot.reply_to(message, "👨‍🍳 Chef's kiss! 🤤 I'm adding it to your list. I'll pop you a message when I'm done 🤞")
        url = "https://fastapi-production-d559.up.railway.app/add_establishment/"
        query = {"name": establishment_name}  # Update the query to include the missing name field
        response = requests.post(url, json=query)
        if response.status_code == 200:
            bot.reply_to(message, f"🙌 {establishment_name} has been added to your list!")
        else:
            print(f"An error occurred: {response.json()}")
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
        url = "https://fastapi-production-d559.up.railway.app/search_establishments/"
        data = {"term": establishment_name}
        response = requests.post(url, json=data)

        if response.status_code == 200:
            result = response.json()["result"]
            bot.reply_to(message, f"👀 Whoa! Look at all these restaurants with '{establishment_name}' in them! 😲\n\n{result}")
        else:
            print(f"An error occurred: {response.status_code}")
            bot.reply_to(message, f"👎 Hmm, {establishment_name} doesn't appear to be on the list. 👻")
    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")
            # Print the error message with traceback information to the console for debugging
        import traceback
        traceback.print_exc()

# Call bot.polling in a try-Except block to prevent the code from crashing
if __name__ == "__main__":
    try:
        bot.polling()
    except Exception as e:
        print(e)
