import asyncio
import os
import json
import random
import logging
import socket
from telethon import TelegramClient, events, errors
from telethon.errors import SessionPasswordNeededError, UserDeactivatedBanError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from colorama import init, Fore
import pyfiglet

# Initialize colorama for colored output
init(autoreset=True)

CREDENTIALS_FOLDER = 'sessions'

if not os.path.exists(CREDENTIALS_FOLDER):
    os.mkdir(CREDENTIALS_FOLDER)

# Set up logging
logging.basicConfig(
    filename='og_flame_service.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

AUTO_REPLY_MESSAGE = """
Hey sir.👋 Please message @OrbitService if you're interested in buying our service. 

➡️ This is just a promotional working ID. Thanks for visiting us! 🙏  
🔺️ Our channel: @OrbitShoppy ✅️  
🔺️ Our proofs: @LegitProofs99 ✅️
"""

# Save session credentials to a file
def save_credentials(session_name, credentials):
    path = os.path.join(CREDENTIALS_FOLDER, f"{session_name}.json")
    with open(path, 'w') as f:
        json.dump(credentials, f)

# Load session credentials from file
def load_credentials(session_name):
    path = os.path.join(CREDENTIALS_FOLDER, f"{session_name}.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}

def display_banner():
    print(Fore.RED + pyfiglet.figlet_format("Og_Flame"))
    print(Fore.GREEN + "Made by @Og_Flame\n")

def is_internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except (OSError, socket.error):
        return False

async def forward_messages_to_groups(client, last_message, session_name, rounds, delay_between_rounds):
    group_dialogs = [dialog for dialog in await client.get_dialogs() if dialog.is_group]

    if not group_dialogs:
        print(Fore.RED + f"No groups found for session {session_name}.")
        logging.warning(f"No groups found for session {session_name}.")
        return

    for round_num in range(1, rounds + 1):
        print(Fore.YELLOW + f"\nStarting round {round_num} for session {session_name}...")
        group_count = 0

        for dialog in group_dialogs:
            group = dialog.entity
            try:
                await client.forward_messages(group, last_message)
                print(Fore.GREEN + f"Message forwarded to {group.title} using {session_name}")
                logging.info(f"Message forwarded to {group.title} using {session_name}")
            except errors.FloodWaitError as e:
                print(Fore.RED + f"Rate limit exceeded. Waiting for {e.seconds} seconds.")
                logging.warning(f"Rate limit exceeded for {group.title}. Waiting for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                print(Fore.RED + f"Failed to forward message to {group.title}: {str(e)}")
                logging.error(f"Failed to forward message to {group.title}: {str(e)}")

            group_count += 1
            delay = random.randint(15, 30)
            print(f"Waiting for {delay} seconds before forwarding to the next group...")
            await asyncio.sleep(delay)

        print(Fore.GREEN + f"Round {round_num} completed for session {session_name}.")
        if round_num < rounds:
            print(Fore.CYAN + f"Waiting for {delay_between_rounds} seconds before starting the next round...")
            await asyncio.sleep(delay_between_rounds)

async def auto_reply(client, session_name):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        # Check if the message is a direct message
        if event.is_private:
            # Send auto-reply message
            await event.reply(AUTO_REPLY_MESSAGE)
            print(Fore.GREEN + f"Replied to message from {event.sender_id} in session {session_name}")
            logging.info(f"Replied to message from {event.sender_id} in session {session_name}")

    # Run the client indefinitely to listen for messages
    await client.run_until_disconnected()

async def login_and_execute(api_id, api_hash, phone_number, session_name, option, rounds=None, delay_between_rounds=None):
    client = TelegramClient(session_name, api_id, api_hash)

    try:
        await client.start(phone=phone_number)

        if not await client.is_user_authorized():
            try:
                await client.send_code_request(phone_number)
                print(Fore.YELLOW + f"OTP sent to {phone_number}")
                otp = input(Fore.CYAN + f"Enter the OTP for {phone_number}: ")
                await client.sign_in(phone_number, otp)
            except SessionPasswordNeededError:
                password = input("Two-factor authentication enabled. Enter your password: ")
                await client.sign_in(password=password)

        print(Fore.GREEN + f"Logged in successfully for session {session_name}")

        # Load the last message from saved messages
        saved_messages_peer = await client.get_input_entity('me')
        history = await client(GetHistoryRequest(
            peer=saved_messages_peer,
            limit=1,
            offset_id=0,
            offset_date=None,
            add_offset=0,
            max_id=0,
            min_id=0,
            hash=0
        ))

        if not history.messages:
            print("No messages found in 'Saved Messages'")
            logging.warning(f"No messages found in 'Saved Messages' for session {session_name}")
            return

        last_message = history.messages[0]

        if option == 1:
            # Start both auto-reply and forward messages concurrently
            tasks = [
                asyncio.create_task(forward_messages_to_groups(client, last_message, session_name, rounds, delay_between_rounds)),
                asyncio.create_task(auto_reply(client, session_name))
            ]
            await asyncio.gather(*tasks)

        elif option == 2:
            await send_and_remove_groups(client, last_message, session_name)

    except UserDeactivatedBanError:
        print(Fore.RED + f"Account {session_name} is banned. Skipping this session.")
        logging.error(f"Account {session_name} is banned.")
    except Exception as e:
        print(Fore.RED + f"Unexpected error in session {session_name}: {str(e)}")
        logging.error(f"Unexpected error in session {session_name}: {str(e)}")
    finally:
        await client.disconnect()

async def send_and_remove_groups(client, last_message, session_name):
    async for dialog in client.iter_dialogs():
        if dialog.is_group:
            group = dialog.entity
            try:
                await client.forward_messages(group, last_message)
                print(Fore.GREEN + f"Message sent to {group.title} using {session_name}")
            except Exception as e:
                print(Fore.RED + f"Failed to send message to {group.title}. Removing group: {str(e)}")
                logging.info(f"Removing group {group.title} due to failure.")
                try:
                    await client(LeaveChannelRequest(group))
                except Exception as remove_error:
                    logging.error(f"Failed to remove group {group.title}: {str(remove_error)}")
            finally:
                await asyncio.sleep(random.randint(10, 20))

async def main():
    display_banner()

    try:
        num_sessions = int(input("Enter how many sessions you want to log in: "))
        active_sessions = []

        # Step 1: Login to all accounts one by one
        for i in range(1, num_sessions + 1):
            session_name = f'session{i}'
            credentials = load_credentials(session_name)

            if credentials:
                print(f"\nUsing saved credentials for session {i}.")
                active_sessions.append((credentials['api_id'], credentials['api_hash'], credentials['phone_number'], session_name))
            else:
                print(f"\nEnter details for account {i}:")
                api_id = int(input(f"Enter API ID for session {i}: "))
                api_hash = input(f"Enter API hash for session {i}: ")
                phone_number = input(f"Enter phone number for session {i} (with country code): ")

                credentials = {'api_id': api_id, 'api_hash': api_hash, 'phone_number': phone_number}
                save_credentials(session_name, credentials)
                active_sessions.append((api_id, api_hash, phone_number, session_name))

        # Step 2: Select the action to perform for all accounts
        print("\nSelect the action to perform for all accounts:")
        print("1. Forward last saved message to all groups (with rounds and delays)")
        print("2. Send last saved message to groups and remove failed ones")
        option = int(input("Enter your choice: "))

        # Ask rounds and delay only once for all sessions
        if option == 1:
            rounds = int(input("How many times do you want to forward messages for all sessions? "))
            delay_between_rounds = int(input("Enter delay (in seconds) between rounds for all sessions: "))

        # Step 3: Execute selected action for all sessions
        tasks = []
        for session in active_sessions:
            api_id, api_hash, phone_number, session_name = session
            tasks.append(login_and_execute(api_id, api_hash, phone_number, session_name, option, rounds, delay_between_rounds))

        await asyncio.gather(*tasks)

    except ValueError:
        print(Fore.RED + "Invalid input. Please enter a valid number.")
        logging.error("ValueError: Invalid input for number of sessions.")
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nProcess interrupted by the user.")
        logging.info("Process interrupted by the user.")
    except Exception as e:
        print(Fore.RED + f"Unexpected error in main(): {str(e)}")
        logging.error(f"Unexpected error in main(): {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())