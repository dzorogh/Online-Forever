<div id="Phantom" align="center">
    <h1>Online Forever</h1>
    <p>Make Your Discord Account 24/7 Online!</p>
    <img src="https://i.imgur.com/N61T21L.png" height="210">
</div>

---

<p align="center">
<b>⭐ Feel free to star the repository if this helped you!</b>
</p>

## Disclaimer
By using this code, you are automating your Discord Account. This is against Discord's Terms of Service and Community Guidelines. If not used properly, your account(s) might get suspended or terminated by Discord. I, the developer, am not responsible for any consequences that may arise from the use of this code. Use this software at your own risk and responsibility. Learn more about <a href="https://discord.com/terms">Discord's Terms of Service</a> and <a href="https://discord.com/guidelines">Community Guidelines</a>.
#### This repository is in no way affiliated with, authorized, maintained, sponsored, or endorsed by Discord Inc. (discord.com) or any of its affiliates or subsidiaries.

## Warning
**DO <ins>NOT</ins> GIVE YOUR DISCORD TOKEN TO ANYONE.**
#### Giving your token to someone else will give them the ability to log into your account without the password or 2FA.

---

## ✨ Features
- Secure [🔒]
- Supports Custom Status
- Account will stay 24/7 online
- Supports all three status modes (Online, Idle, Do Not Disturb)
- Can be used on any platform that supports [Python](https://python.org)

---

## 🔎 Obtaining Your Token
You will need an user token inorder to use this code. You can obtain it by doing the following:
1. Logging in to your discord account
2. Pressing `Ctrl+Shift+I` to open Chrome Developer Tools
3. Go to the `Network` Tab
4. Keep it open and refresh the page
5. Type `/api` in the filter search box
6. Click the entry that has `science` as the `Name`
7. On the sub-menu, go to `Headers`
8. Scroll down till you see an entry named `Authorization`. Copy the line next to it.
9. This is your token. <ins>**DO NOT GIVE IT TO ANYONE**</ins>.

---

## 🛠️ Installation

1. Install [Python](https://python.org/downloads) on your machine (Make sure you add it to [PATH](https://i.imgur.com/Ukl6HdQ.png))
3. Download the repository and extract it
4. Open the `main.py` file and modify both the status mode and custom status, if you want to make any adjustments
5. Save the file
6. Open command prompt inside the folder and run `pip install -r requirements.txt`
7. Once the packages are downloaded, either double-click the `main.py` file in order to run it or open command prompt and run `python main.py`

## 🚀 Dokploy

Deploy this project as a background application/worker. It does not expose an HTTP port.

1. Create an application service in Dokploy from this Git repository.
2. Use Dockerfile build mode with `./Dockerfile`.
3. Do not configure a domain or app port for this service.
4. Add environment variables:

```env
DISCORD_TOKEN=your_token_here
STATUS=online
CUSTOM_STATUS=Hey!
USE_EMOJI=false
PYTHONUNBUFFERED=1
LOG_LEVEL=info
HEARTBEAT_LOG_INTERVAL=60
RECONNECT_DELAY=5
TIMEZONE=Europe/Moscow
ONLINE_START=09:30
ONLINE_END=22:30
```

Supported `STATUS` values: `online`, `idle`, `dnd`.
Set `LOG_LEVEL=debug` for heartbeat send/ack details. `HEARTBEAT_LOG_INTERVAL` controls how often the app writes an "alive" log line.
`ONLINE_START` and `ONLINE_END` define when the gateway connection should be active in the configured `TIMEZONE`. Outside that window, the app pauses its Discord Gateway connection instead of setting an invisible/offline presence, so your normal Discord client can control your real status.

If Dokploy health checks expect an HTTP port, disable them for this service. The container should be kept alive by the process and restarted with an `always` or `unless-stopped` restart policy.

---

<p align="center">Online Forever is licensed under <a href="https://github.com/SealedSaucer/Online-Forever/blob/main/LICENSE">GNU General Public License</a> ❤️</p>
