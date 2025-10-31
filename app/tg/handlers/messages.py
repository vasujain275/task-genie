from app.main import router
from aiogram.filters import Command
from aiogram.types import Message
from app.utils.helpers import ensure_user

@router.message(Command("id"))
async def cmd_id(message: Message):
    if message.from_user:
        await message.answer(f"Your ID: {message.from_user.id}")
    else:
        await message.answer("Unable to retrieve user ID")

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user:
        user = await ensure_user(message.from_user)
        await message.answer(f"Welcome {user.name}!")
    else:
        await message.answer("Unable to retrieve user ID")
