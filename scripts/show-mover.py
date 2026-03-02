import os
import shutil
import json
import re
import unicodedata
import requests
from datetime import datetime

# ---------------- CONFIG ----------------

SOURCE_DIR = "/media-source"

DESTINATIONS = {
    "anime": "/anime-destination",
    "tv": "/tv-destination",
    "kidstv": "/kidstv-destination",
}

MAPPING_FILE = "/maps/show_map.json"
LOG_FILE = "/logs/show-mover.log"

SONARR_URL = os.getenv("SONARR_URL")
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
SONARR_HEADERS = {"X-Api-Key": SONARR_API_KEY}

VALID_TAGS = {"anime", "tv", "kids"}

# ----------------------------------------

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"

    # Always emit to container stdout
    print(line, flush=True)

    # Also persist to log file (best-effort)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[{ts}] ⚠️ Log file write failed: {e}", flush=True)


def normalize(text):
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return text.lower().strip()

# ----------------------------------------

def load_map():
    if not os.path.exists(MAPPING_FILE):
        return {}, {}

    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    active = {}
    ended = raw.get("_ended", {})

    for k, v in raw.items():
        if k == "_ended":
            continue
        active[k] = v

    return active, ended

def save_map(active, ended):
    data = dict(sorted(active.items()))
    if ended:
        data["_ended"] = dict(sorted(ended.items()))

    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ----------------------------------------

def fetch_sonarr_tags():
    r = requests.get(
        f"{SONARR_URL}/api/v3/tag",
        headers=SONARR_HEADERS,
        timeout=30
    )
    r.raise_for_status()

    # Returns {id: "tagname"}
    return {t["id"]: t["label"].lower() for t in r.json()}

def fetch_sonarr_series():
    r = requests.get(
        f"{SONARR_URL}/api/v3/series",
        headers=SONARR_HEADERS,
        timeout=30
    )
    r.raise_for_status()
    return r.json()

def sync_map_with_sonarr():
    log("🔄 Syncing map with Sonarr")

    active, ended = load_map()
    changed = False

    tag_lookup = fetch_sonarr_tags()

    for s in fetch_sonarr_series():
        title = s["title"]
        status = s["status"].lower()
        monitored = s.get("monitored", False)
        folder = os.path.basename(s["path"])

        # Convert tag IDs → tag names
        tags = {
            tag_lookup[t]
            for t in s.get("tags", [])
            if t in tag_lookup
        }

        norm = normalize(folder)


        # ----------------------------
        # Revival: ended → continuing
        # ----------------------------
        if status != "ended" and norm in ended:
            active[norm] = ended.pop(norm)
            log(f"♻️ Series revived → re-enabled: {title}")
            changed = True

        # ----------------------------
        # Series finale
        # ----------------------------
        if status == "ended" and norm in active:
            ended[norm] = active.pop(norm)
            log(f"🏁 Series ended → retired: {title}")
            changed = True
            continue

        # ----------------------------
        # Respect manual overrides
        # ----------------------------
        if norm in active or norm in ended:
            continue

        # ----------------------------
        # ONLY consider monitored items for tags
        # ----------------------------
        if not monitored:
            continue

        tag = next((t for t in tags if t in VALID_TAGS), None)
        if not tag:
            continue

        mapped = "kidstv" if tag == "kids" else tag
        active[norm] = mapped
        log(f"➕ Added (monitored): {title} → {mapped}")
        changed = True

    if changed:
        save_map(active, ended)
        log("💾 Map updated")
    else:
        log("✅ Map already up to date")

    return active

# ----------------------------------------

def verify(src, dst):
    return os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst)

def collect_moves(mapping):
    moves = []
    seen = set()

    for root, _, files in os.walk(SOURCE_DIR):
        if root == SOURCE_DIR:
            continue

        rel = os.path.relpath(root, SOURCE_DIR)
        series = rel.split(os.sep)[0]
        norm = normalize(series)

        tag = mapping.get(norm)
        dest = DESTINATIONS.get(tag)

        if series not in seen:
            if tag:
                log(f"🎯 Match: {series} → {tag}")
            else:
                log(f"❓ No map entry: {series}")
            seen.add(series)

        if not dest:
            continue

        for f in files:
            src = os.path.join(root, f)
            rel_path = os.path.relpath(src, SOURCE_DIR)
            moves.append((src, rel_path, dest))

    return moves

# ----------------------------------------

def move_files():
    log("-" * 60)
    log("🚀 Show mover started")

    mapping = sync_map_with_sonarr()
    if not mapping:
        log("⚠️ No active mappings")
        return

    moves = collect_moves(mapping)
    if not moves:
        log("✅ Nothing to move")
        return

    moved = []

    for src, rel, dest_root in moves:
        dst = os.path.join(dest_root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        try:
            shutil.copy2(src, dst)
            if verify(src, dst):
                moved.append(src)
        except Exception as e:
            log(f"❌ Failed: {rel} → {e}")

    for f in moved:
        try:
            os.remove(f)
        except:
            pass

    for root, _, _ in os.walk(SOURCE_DIR, topdown=False):
        if root != SOURCE_DIR and not os.listdir(root):
            try:
                os.rmdir(root)
                log(f"🗑️ Removed empty folder: {root}")
            except:
                pass

    log(f"🎉 Finished — moved {len(moved)} files")

# ----------------------------------------

if __name__ == "__main__":
    move_files()

