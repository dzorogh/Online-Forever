import asyncio
import json
import logging
import os
import requests
import time
import websockets

LOGGER = logging.getLogger("online_forever")


def env_bool(value):
    return str(value).lower() in {"1", "true", "yes", "on"}


def get_env_int(env, key, default):
    try:
        value = int(env.get(key, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class GatewayHealthLogger:
    def __init__(self, interval_seconds):
        self.interval_seconds = interval_seconds
        self.last_log_at = None

    def should_log(self, now, last_ack_at):
        if last_ack_at is None:
            return False
        return self.last_log_at is None or now - self.last_log_at >= self.interval_seconds

    def mark_logged(self, now):
        self.last_log_at = now


def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "info").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_activity(custom_status, use_emoji):
    activity = {
        "name": "Custom Status",
        "type": 4,
        "state": custom_status,
        "id": "custom",
    }

    if use_emoji:
        activity["emoji"] = {
            "name": "🔥",   # Unicode emoji or emoji name
            "id": None,     # Required only for custom emojis
            "animated": False,
        }

    return activity


def fetch_user(token):
    headers = {"Authorization": token}
    response = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=20)
    if response.status_code != 200:
        raise RuntimeError(f"Discord user API returned HTTP {response.status_code}")
    return response.json()


async def discord_gateway(token, status, activity, heartbeat_log_interval):
    uri = "wss://gateway.discord.gg/?v=10&encoding=json"
    LOGGER.info("Connecting to Discord Gateway")

    async with websockets.connect(uri) as ws:
        hello = json.loads(await ws.recv())
        heartbeat_interval = hello["d"]["heartbeat_interval"]
        LOGGER.info("Gateway connected, heartbeat interval %s ms", heartbeat_interval)

        last_ack_at = None
        health_logger = GatewayHealthLogger(heartbeat_log_interval)

        async def heartbeat():
            while True:
                await asyncio.sleep(heartbeat_interval / 1000)
                await ws.send(json.dumps({"op": 1, "d": None}))
                LOGGER.debug("Heartbeat sent")

        asyncio.create_task(heartbeat())

        identify = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {
                    "$os": "windows",
                    "$browser": "chrome",
                    "$device": "pc"
                },
                "presence": {
                    "status": status,
                    "afk": False,
                    "activities": [activity]
                }
            }
        }
        await ws.send(json.dumps(identify))
        LOGGER.info("Identify payload sent with status=%s", status)

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)

                if data.get("op") == 11:
                    last_ack_at = time.monotonic()
                    LOGGER.debug("Heartbeat ACK received")

                now = time.monotonic()
                if health_logger.should_log(now, last_ack_at):
                    LOGGER.info("Gateway alive, last heartbeat ACK %.0fs ago", now - last_ack_at)
                    health_logger.mark_logged(now)

            except Exception as e:
                LOGGER.warning("Connection lost, reconnecting: %s: %s", type(e).__name__, e)
                break


def main():
    configure_logging()

    token = os.environ["DISCORD_TOKEN"]
    status = os.getenv("STATUS", "online")  # online / dnd / idle
    custom_status = os.getenv("CUSTOM_STATUS", "Hey!")  # Leave empty if you don't want a custom status
    use_emoji = env_bool(os.getenv("USE_EMOJI", "false"))
    heartbeat_log_interval = get_env_int(os.environ, "HEARTBEAT_LOG_INTERVAL", 60)
    reconnect_delay = get_env_int(os.environ, "RECONNECT_DELAY", 5)

    LOGGER.info(
        "Starting with status=%s custom_status=%r use_emoji=%s heartbeat_log_interval=%ss",
        status,
        custom_status,
        use_emoji,
        heartbeat_log_interval,
    )

    user = fetch_user(token)
    LOGGER.info("Logged in as %s (%s)!", user["username"], user["id"])

    activity = build_activity(custom_status, use_emoji)
    reconnect_attempt = 0

    while True:
        reconnect_attempt += 1
        LOGGER.info("Gateway session attempt %s", reconnect_attempt)
        asyncio.run(discord_gateway(token, status, activity, heartbeat_log_interval))
        LOGGER.info("Waiting %ss before reconnect", reconnect_delay)
        time.sleep(reconnect_delay)


if __name__ == "__main__":
    main()
