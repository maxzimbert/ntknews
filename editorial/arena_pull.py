#!/usr/bin/env python3
"""Pull the editor's Are.na channels into a local SQLite database.

    python3 editorial/arena_pull.py            # writes editorial/arena.db

Uses the v3 API. Without a token it runs at the guest tier (30 requests a
minute) and sees only public and closed channels; private ones need a personal
access token, read from ARENA_TOKEN in the environment or ~/.config/arena/token.
The token never lives in the repo (CLAUDE.md rule 5). The database is a working
index, rebuilt from scratch each run, and is not committed.

Tables: channels, blocks, connections (block <-> channel), and blocks_fts, a
full-text index over title, description, text, source url and channel titles.
Query it with editorial/arena_search.py.
"""
import json, os, sqlite3, sys, time, urllib.error, urllib.request
from pathlib import Path

USER = "max-zimcard"
API = "https://api.are.na/v3"
DB = Path(__file__).with_name("arena.db")
TOKEN_FILE = Path.home() / ".config" / "arena" / "token"
TOKEN = os.environ.get("ARENA_TOKEN") or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else None)


def get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "ntk-arena-pull"})
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.headers.get("x-ratelimit-remaining") == "0":
                    time.sleep(61)
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(61)
                continue
            if e.code < 500:
                raise
            time.sleep(10 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("gave up after retries: " + path)


def pages(path):
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        d = get(f"{path}{sep}per=100&page={page}")
        yield from d["data"]
        if not d["meta"].get("has_more_pages"):
            return
        page += 1
        time.sleep(0.5 if TOKEN else 2.1)


def plain(v):
    return v.get("plain") if isinstance(v, dict) else v


def block_row(b):
    src = b.get("source") or {}
    return (
        b["id"], b["type"], b.get("title"), plain(b.get("description")), plain(b.get("content")),
        src.get("url"), (src.get("provider") or {}).get("name"),
        b.get("created_at"), f"https://www.are.na/block/{b['id']}",
    )


def main():
    print("token:", "yes" if TOKEN else "no (guest: public channels only)")
    tmp = DB.with_suffix(".db.tmp")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.executescript("""
        CREATE TABLE channels (id INTEGER PRIMARY KEY, slug TEXT, title TEXT, description TEXT,
                               visibility TEXT, blocks INTEGER, created_at TEXT, updated_at TEXT);
        CREATE TABLE blocks (id INTEGER PRIMARY KEY, type TEXT, title TEXT, description TEXT,
                             text TEXT, source_url TEXT, provider TEXT, created_at TEXT, arena_url TEXT);
        CREATE TABLE connections (block_id INTEGER, channel_id INTEGER, PRIMARY KEY (block_id, channel_id));
        CREATE VIRTUAL TABLE blocks_fts USING fts5(title, description, text, source_url, channels,
                                                   content='', tokenize='porter unicode61');
    """)

    channels = []
    for item in pages(f"/users/{USER}/contents"):
        if item["type"] == "Channel":
            channels.append(item)
        else:
            db.execute("INSERT OR IGNORE INTO blocks VALUES (?,?,?,?,?,?,?,?,?)", block_row(item))
    print(f"{len(channels)} channels, {db.execute('select count(*) from blocks').fetchone()[0]} blocks from user contents")

    for c in channels:
        db.execute("INSERT OR REPLACE INTO channels VALUES (?,?,?,?,?,?,?,?)",
                   (c["id"], c["slug"], (c["title"] or "").strip(), plain(c.get("description")),
                    c.get("visibility"), c["counts"]["blocks"], c["created_at"], c["updated_at"]))
        n = 0
        for b in pages(f"/channels/{c['slug']}/contents"):
            if b.get("base_type") != "Block":
                continue
            db.execute("INSERT OR IGNORE INTO blocks VALUES (?,?,?,?,?,?,?,?,?)", block_row(b))
            db.execute("INSERT OR IGNORE INTO connections VALUES (?,?)", (b["id"], c["id"]))
            n += 1
        print(f"  {c['slug']} [{c.get('visibility')}]: {n}", flush=True)
        db.commit()

    db.execute("""
        INSERT INTO blocks_fts (rowid, title, description, text, source_url, channels)
        SELECT b.id, b.title, b.description, b.text, b.source_url,
               (SELECT group_concat(ch.title, ' | ') FROM connections k JOIN channels ch ON ch.id = k.channel_id
                WHERE k.block_id = b.id)
        FROM blocks b
    """)
    db.commit()
    db.close()
    tmp.replace(DB)
    print("wrote", DB)


if __name__ == "__main__":
    sys.exit(main())
