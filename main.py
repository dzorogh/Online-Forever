import asyncio
from datetime import datetime, time as datetime_time, timedelta
import json
import logging
import os
import requests
import time
from zoneinfo import ZoneInfo

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


def parse_clock(value):
    try:
        hour_text, minute_text = value.split(":", 1)
        parsed = datetime_time(hour=int(hour_text), minute=int(minute_text))
    except (AttributeError, TypeError, ValueError):
        raise ValueError(f"Expected HH:MM time value, got {value!r}")
    return parsed


def is_online_window(now, start, end):
    current = now.timetz().replace(tzinfo=None)
    if start < end:
        return start <= current < end
    if start > end:
        return current >= start or current < end
    return True


def seconds_until_next_transition(now, start, end):
    today_start = datetime.combine(now.date(), start, tzinfo=now.tzinfo)
    today_end = datetime.combine(now.date(), end, tzinfo=now.tzinfo)

    if is_online_window(now, start, end):
        target = today_end
        if target <= now:
            target += timedelta(days=1)
    else:
        target = today_start
        if target <= now:
            target += timedelta(days=1)

    return max(1, int((target - now).total_seconds()))


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


async def discord_gateway(token, status, activity, heartbeat_log_interval, timezone, online_start, online_end):
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

                schedule_now = datetime.now(timezone)
                if not is_online_window(schedule_now, online_start, online_end):
                    sleep_seconds = seconds_until_next_transition(schedule_now, online_start, online_end)
                    LOGGER.info(
                        "Online window ended at %s; pausing gateway until %s in %s",
                        schedule_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
                        (schedule_now + timedelta(seconds=sleep_seconds)).strftime("%Y-%m-%d %H:%M:%S %Z"),
                        timezone.key,
                    )
                    break

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
    timezone = ZoneInfo(os.getenv("TIMEZONE", "Europe/Moscow"))
    online_start = parse_clock(os.getenv("ONLINE_START", "09:30"))
    online_end = parse_clock(os.getenv("ONLINE_END", "22:30"))

    LOGGER.info(
        "Starting with status=%s custom_status=%r use_emoji=%s heartbeat_log_interval=%ss online_window=%s-%s timezone=%s",
        status,
        custom_status,
        use_emoji,
        heartbeat_log_interval,
        online_start.strftime("%H:%M"),
        online_end.strftime("%H:%M"),
        timezone.key,
    )

    user = fetch_user(token)
    LOGGER.info("Logged in as %s (%s)!", user["username"], user["id"])

    activity = build_activity(custom_status, use_emoji)
    reconnect_attempt = 0

    while True:
        now = datetime.now(timezone)
        if not is_online_window(now, online_start, online_end):
            sleep_seconds = seconds_until_next_transition(now, online_start, online_end)
            resume_at = now + timedelta(seconds=sleep_seconds)
            LOGGER.info(
                "Outside online window at %s; gateway paused until %s in %s",
                now.strftime("%Y-%m-%d %H:%M:%S %Z"),
                resume_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
                timezone.key,
            )
            time.sleep(sleep_seconds)
            continue

        reconnect_attempt += 1
        LOGGER.info("Gateway session attempt %s", reconnect_attempt)
        asyncio.run(discord_gateway(token, status, activity, heartbeat_log_interval, timezone, online_start, online_end))
        LOGGER.info("Waiting %ss before reconnect", reconnect_delay)
        time.sleep(reconnect_delay)


if __name__ == "__main__":
    main()
