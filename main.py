import os
import asyncio
import discord
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from typing import AsyncGenerator

load_dotenv()


class MyClient(discord.Client):
    async def on_ready(self):
        print(f"✅ Discord Bot Logged in as {self.user}")

    async def on_message(self, message):
        print(f"📨 Message from {message.author}: {message.content}")

        if message.author != self.user:
            return

        if message.content == "ping":
            await message.channel.send("pong")


client = MyClient()


async def run_discord_bot():
    await client.start(os.getenv("DISCORD_TOKEN"))


async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print("🚀 Starting Discord Bot...")
    task = asyncio.create_task(run_discord_bot())
    yield

    print("🛑 Shutting down...")
    if not client.is_closed():
        await client.close()
        print("🌙 Discord bot connection is closed.")
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Server is running!"}


@app.get("/status")
def status():
    return {
        "bot": "online" if client.is_ready() else "offline",
        "user": str(client.user) if client.user else None,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="127.0.0.1", port=int(os.getenv("PORT", 28800)), reload=True
    )
