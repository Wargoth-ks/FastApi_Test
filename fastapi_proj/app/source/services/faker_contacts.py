import sys
import os

# if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
#     sys.path.append(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, "app")

import asyncio
import time

from faker import Faker
from source.db.models import Contact
from source.db.connect_db import SessionLocal
from sqlalchemy import select, or_
from prompt_toolkit import PromptSession
from dotenv import load_dotenv

load_dotenv()


session = PromptSession()


async def prompt_for_input(prompt_message):
    """
    The prompt_for_input function is a coroutine that prompts the user for input.
    It will continue to prompt until it receives valid input,
    which is defined as an integer or &quot;exit&quot;.
    If the user enters &quot;exit&quot;, then the program exits with status code 0.
    If they enter anything else,
    the function returns their response as an int.

    :param prompt_message: Display a message to the user
    :return: An integer
    """
    while True:
        response = await session.prompt_async(prompt_message)
        if response == "exit":
            sys.exit(0)
        elif not response.isdigit():
            print("Invalid input. Please enter a number or exit.")
        else:
            return int(response)


async def generate_fake_contacts():
    """
    The generate_fake_contacts function generates fake contacts for a user.
        The function takes the following arguments:
            id (int): The ID of the user to generate fake contacts for.
            n (int): The number of fake contacts to generate.

    :return: A list of fake contacts
    """
    while True:
        try:
            id = await prompt_for_input("Enter contact ID: ")
            n = await prompt_for_input("Enter number of fake contacts: ")
            if n:
                start_time = time.time()
                fake = Faker()
                async with SessionLocal() as db:
                    for _ in range(n):
                        name = fake.first_name()
                        surname = fake.last_name()
                        email = fake.unique.email()
                        phone = fake.unique.numerify("380#########")
                        birthday = fake.date_of_birth()

                        stmt = select(Contact).where(
                            or_(Contact.email == email, Contact.phone == phone)
                        )
                        contact_exists = await db.execute(stmt)

                        if contact_exists.scalars().first():
                            continue

                        contact = Contact(
                            name=name,
                            surname=surname,
                            email=email,
                            phone=phone,
                            birthday=birthday,
                            user_id=id,
                        )

                        db.add(contact)
                        await db.commit()
                        await db.refresh(contact)

                    total_time = time.time() - start_time
                    print("\nDone!")
                    print(f"\nTotal time: {total_time:.2f} seconds\n")
                    sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
        break


asyncio.run(generate_fake_contacts())
