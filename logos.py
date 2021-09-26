import re
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

cache_path: Path = Path(".")
whitelisted_invites = set()
cache_time_to_live = timedelta(hours=1)


def fetch_image(invite_id: str):
    response = requests.get(f"https://discord.com/api/v9/invites/{invite_id}")
    if response.status_code != 200:
        return "Error (invite): " + str(response.status_code)

    guild = response.json()["guild"]
    guild_id = guild["id"]
    icon_id = guild["icon"]

    response = requests.get(f"https://cdn.discordapp.com/icons/{guild_id}/{icon_id}.png?size=128")
    if response.status_code != 200:
        return "Error (image) : " + str(response.status_code)

    return response.content


def get_cached(invite_id: str):
    path = Path(cache_path / (invite_id + ".png"))
    if not path.exists():
        return None

    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    if mtime + cache_time_to_live < datetime.now():
        path.unlink()
        return None

    with open(path, "rb") as file:
        return file.read()


def write_to_cache(invite_id: str, image: bytes):
    with open(cache_path / (invite_id + ".png"), "wb") as file:
        file.write(image)


class Handler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "image/png")
        self.end_headers()

    def do_GET(self):
        invite_id = self.path.replace("/", "")

        if not re.match(r"^[a-zA-Z0-9]+$", invite_id):
            self.send_error(400, "That looks strange", "You sure that's an invite, buddy?")
            return

        if invite_id not in whitelisted_invites:
            self.send_error(400, "That invite looks strange", f"Invalid invite: '{invite_id}'")
            return

        image = get_cached(invite_id)
        if not image:
            image = fetch_image(invite_id)

            if isinstance(image, str):
                self.send_error(500, "Invalid image received", image)
                return

            write_to_cache(invite_id, image)

        self._set_headers()
        self.wfile.write(image)

    def do_HEAD(self):
        self._set_headers()


def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler, port=8080):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


def main(port):
    run(HTTPServer, Handler, port)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: <port> <cache path> <whitelisted invite link>...")
        cache_path = Path(sys.argv[2])

    cache_path.mkdir(parents=True, exist_ok=True)

    whitelisted_invites = whitelisted_invites.union(set(sys.argv[3:]))

    main(int(sys.argv[1]))
