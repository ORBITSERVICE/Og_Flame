import logging
import os
import uuid
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)
from cryptography.fernet import Fernet

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- STATES ---
(
    START,
    REGISTERED,
    MENU,
    BUY_SESSION,
    CONFIRM_PURCHASE,
    ADMIN_MENU,
    ADD_SESSION,
    REMOVE_SESSION,
) = range(8)

# --- GLOBAL DATA ---
ADMIN_IDS = [123456789]  # Replace with actual admin IDs
SESSION_PRICES = {"session1.txt": 10, "session2.txt": 15}  # Example prices
SESSION_FILES = ["session1.txt", "session2.txt"]  # Example session files

# Generate encryption key (keep this secure)
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

# --- HELPER FUNCTIONS (MOCK - Replace with actual database operations) ---
def add_user(user_id):
    """Mock function to add user to the database."""
    print(f"User {user_id} added to the database.")

def get_session_details(session_file):
    """Mock function to get session details from the database."""
    return {"filename": session_file, "price": SESSION_PRICES.get(session_file, 0)}

def process_payment(user_id, session_file):
    """Mock function to process payment."""
    print(f"Payment processed for user {user_id} for {session_file}.")
    return True  # Simulate successful payment

def is_admin(user_id):
    """Mock function to check if a user is an admin."""
    return user_id in ADMIN_IDS

# --- COMMAND HANDLERS ---
def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and checks if the user is registered."""
    user = update.effective_user
    user_id = user.id
    reply_keyboard = [["Register"]]
    update.message.reply_text(
        f"Hi {user.first_name}, welcome to the Session Bot!\n"
        "Please register to continue.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Register?"
        ),
    )
    return START

def register(update: Update, context: CallbackContext) -> int:
    """Registers the user."""
    user = update.effective_user
    user_id = user.id
    add_user(user_id)  # Add user to the database
    update.message.reply_text("You are now registered!", reply_markup=ReplyKeyboardRemove())
    return MENU

def menu(update: Update, context: CallbackContext) -> int:
    """Displays the main menu."""
    user_id = update.effective_user.id
    if is_admin(user_id):
        reply_keyboard = [["Buy Session"], ["Admin Menu"]]
    else:
        reply_keyboard = [["Buy Session"]]
    update.message.reply_text(
        "What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Choose an action"
        ),
    )
    return MENU

def buy_session(update: Update, context: CallbackContext) -> int:
    """Displays available sessions for purchase."""
    reply_keyboard = [[session] for session in SESSION_FILES]
    reply_keyboard.append(["Back to Menu"])
    update.message.reply_text(
        "Choose a session to purchase:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return BUY_SESSION

def confirm_session(update: Update, context: CallbackContext) -> int:
    """Confirms the session purchase."""
    session_file = update.message.text
    if session_file == "Back to Menu":
        return menu(update, context)
    context.user_data["selected_session"] = session_file
    session_details = get_session_details(session_file)
    if not session_details:
        update.message.reply_text("Invalid session file.")
        return BUY_SESSION
    reply_keyboard = [["Confirm", "Cancel"]]
    update.message.reply_text(
        f"You have selected {session_details['filename']}. Price: {session_details['price']} credits. Confirm purchase?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return CONFIRM_PURCHASE

def process_purchase(update: Update, context: CallbackContext) -> int:
    """Processes the session purchase."""
    choice = update.message.text
    if choice == "Confirm":
        user = update.effective_user
        user_id = user.id
        session_file = context.user_data.get("selected_session")
        if not session_file:
            update.message.reply_text("No session selected. Please try again.")
            return BUY_SESSION
        if process_payment(user_id, session_file):
            # Encrypt the file
            with open(session_file, "rb") as file:
                file_data = file.read()
            encrypted_data = cipher.encrypt(file_data)
            # Save the encrypted file
            encrypted_filename = f"{session_file}.enc"
            with open(encrypted_filename, "wb") as file:
                file.write(encrypted_data)
            update.message.reply_text("Payment successful! Sending session file...")
            # Send the encrypted file to the user
            with open(encrypted_filename, "rb") as file:
                update.message.reply_document(document=file, filename=encrypted_filename)
            # Clean up the encrypted file
            os.remove(encrypted_filename)
            return ConversationHandler.END
        else:
            update.message.reply_text("Payment failed. Please try again.")
            return BUY_SESSION
    else:
        update.message.reply_text("Purchase cancelled.")
        return BUY_SESSION

def admin_menu(update: Update, context: CallbackContext) -> int:
    """Displays the admin menu."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("You are not authorized to access this menu.")
        return ConversationHandler.END
    reply_keyboard = [["Add Session", "Remove Session"], ["Back to Menu"]]
    update.message.reply_text(
        "Admin Menu: What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return ADMIN_MENU

def add_session(update: Update, context: CallbackContext) -> int:
    """Handles adding a new session (not implemented)."""
    update.message.reply_text("Adding session (not implemented).")
    return ADMIN_MENU

def remove_session(update: Update, context: CallbackContext) -> int:
    """Handles removing a session (not implemented)."""
    update.message.reply_text("Removing session (not implemented).")
    return ADMIN_MENU

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.effective_user
    logger.info("User %s canceled the conversation.", user.id)
    update.message.reply_text(
        "Bye! Hope to see you again.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater("7992378132:AAGaK8PLAXhz3tKYSm-sbkg_sdf0E4y400g")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Define the conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START: [MessageHandler(Filters.text & ~Filters.command, register)],
            MENU: [MessageHandler(Filters.text & ~Filters.command, menu)],
            BUY_SESSION: [MessageHandler(Filters.text & ~Filters.command, confirm_session)],
            CONFIRM_PURCHASE: [MessageHandler(Filters.text & ~Filters.command, process_purchase)],
            ADMIN_MENU: [MessageHandler(Filters.text & ~Filters.command, admin_menu)],
            ADD_SESSION: [MessageHandler(Filters.text & ~Filters.command, add_session)],
            REMOVE_SESSION: [MessageHandler(Filters.text & ~Filters.command, remove_session)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add the conversation handler to the dispatcher
    dispatcher.add_handler(conv_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()