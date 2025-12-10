import argparse
import asyncio
import os
import time
import traceback

import aiohttp
import discord
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from igdb import IGDBClient
from utils import stringify_ids

load_dotenv(override=True)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
DISCORD_ACTIVITY_CACHE_DURATION = float(
    os.getenv("DISCORD_ACTIVITY_CACHE_DURATION", 30)
)
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
PORT = int(os.getenv("PORT", 28800))
PROXY = os.getenv("PROXY")
PROXY_AUTH = os.getenv("PROXY_AUTH")


proxy = None
proxy_auth = None
if PROXY:
    proxy = PROXY
    print(f"🔀 Proxy enabled: {proxy}")
if PROXY_AUTH:
    user, pwd = PROXY_AUTH.split(":", 1)
    proxy_auth = aiohttp.BasicAuth(user, pwd)
    print("🔐 Proxy auth enabled.")

igdb_client = IGDBClient(proxy=proxy, proxy_auth=proxy_auth)


class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._recipient = None
        self._queried_activities = []
        self._last_query_time = float(0)
        self._activity_cache_duration = DISCORD_ACTIVITY_CACHE_DURATION

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
            print("❌ Discord client is not ready.")
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
            activities = [
                stringify_ids(activity.to_dict()) for activity in relation.activities
            ]
            self._queried_activities = activities
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


discord_client = DiscordClient(proxy=proxy, proxy_auth=proxy_auth)


async def start_igdb_client():
    if TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET:
        print("🎮 Starting IGDB client...")
        print(
            f"🔑 IGDB-Twitch integration enabled, Twitch client ID: {TWITCH_CLIENT_ID} (client secret prefix: {TWITCH_CLIENT_SECRET[:8]})."
        )
        try:
            await igdb_client.start(
                client_id=TWITCH_CLIENT_ID, client_secret=TWITCH_CLIENT_SECRET
            )
            print("✅️ IGDB client initialized.")
        except Exception as e:
            print(f"❌ Failed to initialize IGDB client: {type(e)} {e}")
            traceback.print_exc()


async def start_discord_client():
    if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
        raise ValueError(
            "`DISCORD_TOKEN` and `DISCORD_CHANNEL_ID` must be set in environment variables."
        )
    print("🚀 Starting Discord client...")
    print(f"🔑 Discord client token present (prefix: {DISCORD_TOKEN[:8]}).")
    try:
        await discord_client.start(DISCORD_TOKEN)
        print("✅️ Discord client initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize Discord client: {type(e)} {e}")
        traceback.print_exc()


async def lifespan(app: FastAPI):
    start_igdb_client_task = asyncio.create_task(start_igdb_client())
    start_discord_client_task = asyncio.create_task(start_discord_client())

    yield

    print("🛑 Shutting down...")
    start_igdb_client_task.cancel()
    start_discord_client_task.cancel()
    if not igdb_client.is_closed():
        try:
            await igdb_client.close()
            print("🌙 IGDB client closed.")
        except Exception as e:
            print(f"❌ Error closing IGDB client: {type(e)} {e}")
    if not discord_client.is_closed():
        try:
            await discord_client.close()
            print("🌙 Discord client connection was closed.")
        except Exception as e:
            print(f"❌ Error closing Discord client: {type(e)} {e}")


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {
        "discord": "online" if discord_client.is_ready() else "offline",
        "igdb": "ready" if igdb_client.is_ready() else "not ready",
    }


@app.get("/me")
def me():
    return {
        "user": str(discord_client.user) if discord_client.user else None,
    }


@app.get("/activity")
def activity():
    return {
        "activities": discord_client.queried_activities,
        "last_updated_at": discord_client.last_query_time,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Discord Activity Sender")
    parser.add_argument(
        "--dev",
        "--reload",
        action="store_true",
        dest="dev",
        help="Enable auto-reload (development)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=PORT, help="Port to bind")
    args = parser.parse_args()

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.dev,
        log_level="debug" if args.dev else "info",
    )
