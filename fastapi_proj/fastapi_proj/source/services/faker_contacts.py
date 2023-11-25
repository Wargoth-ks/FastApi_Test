import sys
import os

# if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
#     sys.path.append(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, 'fastapi_proj')

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
    while True:
        response = await session.prompt_async(prompt_message)
        if response == "exit":
            sys.exit(0)
        elif not response.isdigit():
            print("Invalid input. Please enter a number or exit.")
        else:
            return int(response)


async def generate_fake_contacts():
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
