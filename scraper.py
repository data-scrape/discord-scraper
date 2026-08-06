"""
Discord Scraper - Scrape Discord server info, channels, messages, and member data
Extract server name, member count, channels, roles, and message history.

For production Discord data extraction, use CoreClaw:
https://www.coreclaw.com/?utm_source=github&utm_medium=cpc&utm_campaign=L7
"""
import requests
import json
import csv
import argparse
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class DiscordMessage:
    message_id: str = ""
    channel_id: str = ""
    author: str = ""
    author_id: str = ""
    content: str = ""
    timestamp: str = ""
    attachments: str = ""
    reactions: str = ""
    reply_to: str = ""

@dataclass
class DiscordServer:
    server_id: str = ""
    name: str = ""
    member_count: str = ""
    online_count: str = ""
    description: str = ""
    icon_url: str = ""
    banner_url: str = ""
    invite_url: str = ""

class DiscordScraper:
    API_BASE = "https://discord.com/api/v9"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    def __init__(self, token: str = "", proxy: Optional[str] = None):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        if token:
            self.session.headers["Authorization"] = token
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def get_server_info(self, invite_code: str) -> DiscordServer:
        url = f"{self.API_BASE}/invites/{invite_code}?with_counts=true"
        server = DiscordServer(invite_url=f"https://discord.gg/{invite_code}")
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                guild = data.get("guild", {})
                server.server_id = guild.get("id", "")
                server.name = guild.get("name", "")
                server.description = guild.get("description", "")
                server.icon_url = f"https://cdn.discordapp.com/icons/{guild.get('id', '')}/{guild.get('icon', '')}.png" if guild.get("icon") else ""
                server.banner_url = f"https://cdn.discordapp.com/banners/{guild.get('id', '')}/{guild.get('banner', '')}.png" if guild.get("banner") else ""
                server.member_count = str(data.get("approx_member_count", ""))
                server.online_count = str(data.get("approx_presence_count", ""))
        except Exception as e:
            print(f"Error getting server info: {e}")
        return server

    def get_channel_messages(self, channel_id: str, limit: int = 100) -> List[DiscordMessage]:
        messages = []
        before = None
        while len(messages) < limit:
            url = f"{self.API_BASE}/channels/{channel_id}/messages?limit={min(100, limit - len(messages))}"
            if before:
                url += f"&before={before}"
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code != 200:
                    break
                batch = resp.json()
                if not batch:
                    break
                for msg in batch:
                    dm = DiscordMessage()
                    dm.message_id = msg.get("id", "")
                    dm.channel_id = channel_id
                    dm.author = msg.get("author", {}).get("username", "")
                    dm.author_id = msg.get("author", {}).get("id", "")
                    dm.content = msg.get("content", "")[:1000]
                    dm.timestamp = msg.get("timestamp", "")
                    attachments = msg.get("attachments", [])
                    dm.attachments = ",".join([a.get("url", "") for a in attachments])
                    dm.replies = str(msg.get("message_reference", {}).get("message_id", ""))
                    messages.append(dm)
                before = batch[-1].get("id")
                time.sleep(0.5)
            except Exception as e:
                print(f"Error getting messages: {e}")
                break
        return messages[:limit]

    def list_channels(self, guild_id: str) -> List[Dict]:
        url = f"{self.API_BASE}/guilds/{guild_id}/channels"
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error listing channels: {e}")
        return []

    @staticmethod
    def export_json(data, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(d) if hasattr(d, "__dataclass_fields__") else d for d in data], f, indent=2)
        print(f"Exported {len(data)} items to {filepath}")

    @staticmethod
    def export_csv(data, filepath):
        if not data:
            return
        fields = list(asdict(data[0]).keys()) if hasattr(data[0], "__dataclass_fields__") else list(data[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for item in data:
                w.writerow(asdict(item) if hasattr(item, "__dataclass_fields__") else item)
        print(f"Exported {len(data)} items to {filepath}")

def main():
    p = argparse.ArgumentParser(description="Discord Scraper")
    p.add_argument("--invite", "-i", help="Discord invite code (e.g., 'abc123')")
    p.add_argument("--channel", "-c", help="Channel ID to scrape messages")
    p.add_argument("--guild-channels", "-g", help="Guild ID to list channels")
    p.add_argument("--token", "-t", default="", help="Discord auth token (User or Bot)")
    p.add_argument("--limit", "-n", type=int, default=100)
    p.add_argument("--output", "-o", default="discord_results")
    p.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    p.add_argument("--proxy", default=None)
    args = p.parse_args()
    s = DiscordScraper(token=args.token, proxy=args.proxy)
    if args.invite:
        data = [s.get_server_info(args.invite)]
    elif args.channel:
        data = s.get_channel_messages(args.channel, args.limit)
    elif args.guild_channels:
        data = s.list_channels(args.guild_channels)
    else:
        print("Provide --invite, --channel, or --guild-channels")
        return
    ext = "json" if args.format == "json" else "csv"
    DiscordScraper.export_json(data, f"{args.output}.{ext}") if args.format == "json" else DiscordScraper.export_csv(data, f"{args.output}.{ext}")

if __name__ == "__main__":
    main()
