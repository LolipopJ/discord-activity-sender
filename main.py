import asyncio
import os
import time

import discord
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
    raise ValueError(
        "❌ `DISCORD_TOKEN` and `DISCORD_CHANNEL_ID` must be set in environment variables."
    )


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._recipient = None
        self._queried_activities = []
        self._last_query_time = float(0)
        self._activity_cache_duration = float(
            os.getenv("DISCORD_ACTIVITY_CACHE_DURATION", 30)
        )

    async def on_ready(self):
        print(f"✅ Discord client Logged in as {self.user}")

    async def on_error(self, event_method, *args, **kwargs):
        print(f"❌ An error occurred in {event_method}: ", args, kwargs)

    async def on_message(self, message: discord.Message):
        print(f"📨 Message from {message.author}: {message.content}")

        if message.author != self.user:
            return

        if message.content == "ping":
            await message.channel.send("pong")

    @property
    def queried_activities(self):
        if time.time() - self._last_query_time < self._activity_cache_duration:
            print(
                f"ℹ️ Return cached activities for user {self._recipient}: {self._queried_activities}"
            )
            return self._queried_activities

        if self.is_ready() is False:
            print(
                "❌ Discord client is not ready. If long time waited, please check if the network was able to connect Discord server."
            )
            return []

        if self._recipient is None:
            channel = self.get_channel(int(DISCORD_CHANNEL_ID))
            if channel is not None:
                self._recipient = channel.recipient
                print(f"✅ Set recipient to {self._recipient}.")
            else:
                print(
                    f"❌ No Discord channel found for channel ID {DISCORD_CHANNEL_ID}."
                )
                return []

        recipientId = self._recipient.id
        if recipientId is None:
            print("❌ No recipient ID found.")
            return []

        relation = self.get_relationship(recipientId)
        if relation is not None:
            self._queried_activities = [
                activity.to_dict() for activity in relation.activities
            ]
            self._last_query_time = time.time()
            print(
                f"✅ Update activities for user {self._recipient}: {self._queried_activities}"
            )
        else:
            print(f"❌ No relationship found for user {self._recipient}.")
            return []

        return self._queried_activities

    @property
    def last_query_time(self):
        return int(self._last_query_time)


client = MyClient()


async def start_discord_client():
    await client.start(DISCORD_TOKEN)


async def lifespan(app: FastAPI):
    print("🚀 Starting Discord client...")
    task = asyncio.create_task(start_discord_client())
    yield

    print("🛑 Shutting down...")
    if not client.is_closed():
        await client.close()
        print("🌙 Discord client connection was closed.")
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Server is running!"}


@app.get("/me")
def me():
    return {
        "client": "online" if client.is_ready() else "offline",
        "user": str(client.user) if client.user else None,
    }


@app.get("/activity")
def activity():
    return {
        "activities": client.queried_activities,
        "last_updated_at": client.last_query_time,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=int(os.getenv("PORT", 28800)), reload=True
    )
