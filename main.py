import asyncio
import os

import discord
import uvicorn
from discord.ext import tasks
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recipient = None
        self.queried_activities = []

    async def setup_hook(self) -> None:
        self.task_query_activities.start()

    async def on_ready(self):
        print(f"✅ Discord Bot Logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        print(f"📨 Message from {message.author}: {message.content}")

        if message.author != self.user:
            return

        if message.content == "ping":
            await message.channel.send("pong")

    @tasks.loop(seconds=5)
    async def task_query_activities(self):
        print("🛠️ Running background task...")

        if self.recipient is None:
            channelId = int(os.getenv("DISCORD_CHANNEL_ID"))
            channel = self.get_channel(channelId)
            if channel is not None:
                self.recipient = channel.recipient
                print(f"✅ Set recipient to {self.recipient}.")
            else:
                print(f"❌ No Discord channel found for channel ID {channelId}.")
                return

        await self.update_queried_activities()

    @task_query_activities.before_loop
    async def before_task_query_activities(self):
        await self.wait_until_ready()

    async def update_queried_activities(self):
        recipientId = self.recipient.id
        if recipientId is None:
            print("❌ No recipient ID found.")
            return

        relation = self.get_relationship(recipientId)
        if relation is not None:
            self.queried_activities = [
                activity.to_dict() for activity in relation.activities
            ]
            print(
                f"✅ Updated activities for user {self.recipient}: {self.queried_activities}"
            )
        else:
            print(f"❌ No relationship found for user {self.recipient}.")


client = MyClient()


async def run_discord_bot():
    await client.start(os.getenv("DISCORD_TOKEN"))


async def lifespan(app: FastAPI):
    print("🚀 Starting Discord Bot...")
    task = asyncio.create_task(run_discord_bot())
    yield

    print("🛑 Shutting down...")
    if not client.is_closed():
        await client.close()
        print("🌙 Discord bot connection was closed.")
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Server is running!"}


@app.get("/me")
def me():
    return {
        "bot": "online" if client.is_ready() else "offline",
        "user": str(client.user) if client.user else None,
    }


@app.get("/status")
def status():
    return client.queried_activities


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="127.0.0.1", port=int(os.getenv("PORT", 28800)), reload=True
    )
