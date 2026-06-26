#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk, Gio, GObject
import sqlite3
import os
import math
import re
import random
from datetime import date, datetime, timedelta
import colorsys

APP_ID = "io.github.emmastf.Projex"
VERSION = "0.1.32"

# ── Inspirational quotes, keyed by busyness level ───────────────────────
_QUOTES = {
    "heavy": [
        ("A river cuts through rock not by force, but by persistence.", "— proverb"),
        ("You don't have to see the whole staircase. Just take the first step.", "— Martin Luther King Jr."),
        ("It is not the mountain we conquer, but ourselves.", "— Edmund Hillary"),
        ("The work itself will teach you.", "— Estonian proverb"),
        ("Hard times arouse an instinctive desire for authenticity.", "— Coco Chanel"),
        ("I am not afraid of storms, for I am learning how to sail my ship.", "— Louisa May Alcott"),
        ("Doing a great right thing doesn't mean doing everything right.", "— adapted"),
        ("Bear in mind that you should conduct yourself in life as at a feast.", "— Epictetus"),
        ("Ichi-go ichi-e — this moment, once, never again.", "— Japanese concept"),
        ("Even the tallest oak began as a small acorn that held its ground.", "— proverb"),
    ],
    "medium": [
        ("Start where you are. Use what you have. Do what you can.", "— Arthur Ashe"),
        ("Well done is better than well said.", "— Benjamin Franklin"),
        ("Think of many things; do one.", "— Portuguese proverb"),
        ("Small deeds done are better than great deeds planned.", "— Peter Marshall"),
        ("Nothing great is created suddenly, any more than a bunch of grapes or a fig.", "— Epictetus"),
        ("The secret of success is constancy to purpose.", "— Benjamin Disraeli"),
        ("In the middle of every difficulty lies opportunity.", "— Albert Einstein"),
        ("What is not started today is never finished tomorrow.", "— Goethe"),
        ("Steady drops will bore through stone.", "— proverb"),
        ("To climb steep hills requires slow pace at first.", "— Shakespeare"),
    ],
    "light": [
        ("Almost everything will work again if you unplug it for a few minutes. Including you.", "— Anne Lamott"),
        ("The quieter you become, the more you can hear.", "— Ram Dass"),
        ("Creativity is a gift. It doesn't come through if the air is cluttered.", "— John Lennon"),
        ("A calm and modest life brings more happiness than the pursuit of success combined with restlessness.", "— Albert Einstein"),
        ("Rest is not idleness, and to lie sometimes on the grass on a summer day is by no means a waste of time.", "— John Lubbock"),
        ("It is a happy talent to know how to play.", "— Ralph Waldo Emerson"),
        ("Do a little more each day than you think you possibly can.", "— Lowell Thomas"),
        ("Let your plans be dark and impenetrable as night, and when you move, fall like a thunderbolt.", "— Sun Tzu"),
        ("The present moment always will have been.", "— proverb"),
        ("Not all those who wander are lost.", "— J. R. R. Tolkien"),
    ],
    "clear": [
        ("Rest and be thankful.", "— William Wordsworth"),
        ("It is good to have an end to journey toward; but it is the journey that matters, in the end.", "— Ursula K. Le Guin"),
        ("What you do today can improve all your tomorrows.", "— Ralph Marston"),
        ("The richness of life lies in memories we have forgotten.", "— Cesare Pavese"),
        ("Now is no time to think of what you do not have. Think of what you can do with what there is.", "— Ernest Hemingway"),
        ("In seed time learn, in harvest teach, in winter enjoy.", "— William Blake"),
        ("A good plan violently executed now is better than a perfect plan executed next week.", "— George Patton"),
        ("Beginnings are always messy.", "— John Galsworthy"),
    ],
}
_SESSION_QUOTE_IDX = random.randint(0, 9999)

def _pick_quote(level):
    pool = _QUOTES.get(level, _QUOTES["light"])
    return pool[_SESSION_QUOTE_IDX % len(pool)]
_CHANGELOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHANGELOG.md")
_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
_data_dir = os.path.join(_data_home, "projex")
os.makedirs(_data_dir, exist_ok=True)
DB_PATH = os.path.join(_data_dir, "tracker.db")

STATUSES = ["active", "paused", "done", "archived"]
PRIORITIES = ["normal", "high", "low"]
ENTRY_STATUSES = ["draft", "done"]
MSTATUSES = ["pending", "active", "done", "blocked"]
RECUR_OPTIONS = ["Don't repeat", "Every day", "Every 2 days", "Every weekday",
                 "Every week", "Every 2 weeks", "Every month", "Every year"]
RECUR_DAYS    = [0, 1, 2, 5, 7, 14, 30, 365]

APP_CSS = """
.priority-bar { border-radius: 3px; min-width: 4px; }
.priority-high { background-color: #e01b24; }
.priority-low  { background-color: #3584e4; }
.tag-chip {
    border-radius: 999px;
    padding: 1px 8px;
    font-size: 0.8em;
    background-color: alpha(currentColor, 0.12);
}
.task-row-high { background-color: rgba(224, 27, 36, 0.07); }
.group-header-row { font-weight: bold; opacity: 0.75; }
.overdue-project-row {
    background-color: rgba(224, 27, 36, 0.06);
    box-shadow: inset 2px 0 0 0 rgba(224, 27, 36, 0.7);
}
.overdue-project-row .title { color: #e01b24; }
.proj-bold-row .title { font-weight: bold; }
.priority-normal-lbl { color: #f5c211; }
.priority-low-lbl { color: #3584e4; }
.drag-target-row { margin-top: 44px; }
row { transition: margin-top 200ms ease; }
calendar .day-with-events indicator { background-color: #e01b24; border-radius: 999px; }
"""

COLOR_PALETTE = [
    "#e01b24", "#e66100", "#f5c211", "#57e389",
    "#33d17a", "#26a269", "#1c71d8", "#3584e4",
    "#613583", "#9141ac", "#986a44", "#77767b",
    "#4fa8c4", "#99c1f1", "#f66151", "#2ec27e",
]


def _load_css():
    provider = Gtk.CssProvider()
    provider.load_from_string(APP_CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def suggest_emoji(name):
    """Return a best-guess emoji for a project name based on keywords."""
    n = name.lower()
    rules = [
        (["journal", "diary", "daily", "log"],          "📔"),
        (["student", "school", "study", "class",
          "course", "lecture", "homework", "uni",
          "college", "university", "assignment"],        "🎓"),
        (["book", "read", "library", "novel",
          "fiction", "chapter"],                         "📚"),
        (["code", "software", "app", "dev", "program",
          "web", "website", "api", "hack", "repo"],      "💻"),
        (["design", "art", "creative", "ui", "ux",
          "graphic", "illustrat", "sketch"],             "🎨"),
        (["music", "song", "album", "band", "audio",
          "podcast", "record", "sound"],                 "🎵"),
        (["fitness", "gym", "health", "exercise",
          "workout", "run", "yoga", "sport", "swim"],    "💪"),
        (["travel", "trip", "vacation", "tour",
          "journey", "adventure"],                       "✈️"),
        (["food", "cook", "recipe", "meal",
          "restaurant", "bake", "kitchen"],              "🍳"),
        (["money", "finance", "budget", "tax",
          "invest", "saving", "expense"],                "💰"),
        (["home", "house", "garden", "renovation",
          "interior", "flat", "apartment"],              "🏡"),
        (["research", "science", "lab", "data",
          "analysis", "thesis", "paper"],                "🔬"),
        (["photo", "photography", "camera",
          "video", "film", "vlog"],                      "📷"),
        (["game", "gaming", "play", "rpg"],              "🎮"),
        (["write", "writing", "blog", "article",
          "essay", "draft", "novel", "story"],           "✍️"),
        (["personal", "self", "mindset",
          "growth", "goal", "habit"],                    "🌱"),
        (["work", "job", "client", "career",
          "office", "business", "startup"],              "💼"),
        (["plan", "strategy", "launch",
          "product", "manage", "sprint"],                "📋"),
        (["event", "wedding", "party",
          "conference", "meetup"],                       "🎉"),
        (["learn", "course", "tutorial",
          "skill", "training"],                          "🧠"),
    ]
    for words, emoji in rules:
        if any(w in n for w in words):
            return emoji
    return "📁"


def _progress_quip(pct, total):
    """Return a cheeky one-liner matching the completion percentage."""
    if total == 0:        return "No tasks yet — let's get planning! 🗺️"
    if pct == 0:          return "Ready for launch… countdown starting 🚀"
    if pct < 0.05:        return "Baby steps! 🐣"
    if pct < 0.10:        return "Off to the races! 🏇"
    if pct < 0.20:        return "Just warming up ☕"
    if pct < 0.30:        return "Finding the groove 🎸"
    if pct < 0.40:        return "Getting into it! 💪"
    if pct < 0.49:        return "Halfway is just ahead… 🌄"
    if pct < 0.52:        return "Glass half full! 🥛"
    if pct < 0.60:        return "Over the hill (the good kind) 🏔️"
    if pct < 0.70:        return "More done than not! ✅"
    if pct < 0.78:        return "Zooming along 🚄"
    if pct < 0.85:        return "Three-quarter legend 🏆"
    if pct < 0.90:        return "The finish line beckons 🏁"
    if pct < 0.95:        return "Almost there! 😤"
    if pct < 1.0:         return "One last push — you've got this! 🏋️"
    return "Absolutely crushed it! You legend 🎉"


def parse_natural_date(text):
    """
    Parse natural language date input → ISO date string, or return text unchanged.
    Handles:
      +7d / +2w / +1m  (existing shortcuts)
      today, tomorrow, yesterday
      monday/tuesday/... (next occurrence of that weekday)
      jan 5 / june 5 / 5 june / january 5
      2026-06-15  (already ISO — pass through)
      due monday / due june 5  (strip leading "due ")
    """
    import re, calendar as _cal

    raw = text.strip()
    if not raw:
        return raw

    # strip leading "due " (case-insensitive)
    s = re.sub(r'^due\s+', '', raw, flags=re.IGNORECASE).strip()

    today = date.today()

    # +Nd/+Nw/+Nm shortcuts
    m = re.fullmatch(r'\+(\d+)([dwm])', s, re.IGNORECASE)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        if unit == 'd':
            return (today + timedelta(days=n)).isoformat()
        elif unit == 'w':
            return (today + timedelta(weeks=n)).isoformat()
        else:
            y, mo = divmod(today.month - 1 + n, 12)
            mo += 1
            last_day = _cal.monthrange(today.year + y, mo)[1]
            return today.replace(year=today.year + y, month=mo,
                                 day=min(today.day, last_day)).isoformat()

    # relative words
    sl = s.lower()
    if sl in ("today",):
        return today.isoformat()
    if sl in ("tomorrow",):
        return (today + timedelta(days=1)).isoformat()
    if sl in ("yesterday",):
        return (today - timedelta(days=1)).isoformat()

    # weekday names
    WEEKDAYS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    if sl in WEEKDAYS:
        target_wd = WEEKDAYS.index(sl)
        days_ahead = (target_wd - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # next occurrence
        return (today + timedelta(days=days_ahead)).isoformat()

    # month name lookup
    MONTHS = {mn.lower(): i+1 for i, mn in enumerate(_cal.month_name) if mn}
    MONTHS_SHORT = {mn.lower(): i+1 for i, mn in enumerate(_cal.month_abbr) if mn}
    MONTHS.update(MONTHS_SHORT)

    # "june 5" or "jun 5"
    m2 = re.fullmatch(r'([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?', sl)
    if m2 and m2.group(1) in MONTHS:
        month = MONTHS[m2.group(1)]
        day = int(m2.group(2))
        year = today.year
        try:
            d = date(year, month, day)
            if d < today:
                d = date(year + 1, month, day)
            return d.isoformat()
        except ValueError:
            pass

    # "5 june" or "5th june"
    m3 = re.fullmatch(r'(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)', sl)
    if m3 and m3.group(2) in MONTHS:
        month = MONTHS[m3.group(2)]
        day = int(m3.group(1))
        year = today.year
        try:
            d = date(year, month, day)
            if d < today:
                d = date(year + 1, month, day)
            return d.isoformat()
        except ValueError:
            pass

    # already ISO format
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
        return s

    return raw  # unrecognised — return as-is


def expand_date_shortcut(text):
    """Thin wrapper around parse_natural_date for backwards compat."""
    return parse_natural_date(text)


def _wire_date_shortcut(entry_row):
    """Expand date on Enter; also expand on focus-out."""
    def _expand(row, *_):
        raw = row.get_text().strip()
        expanded = parse_natural_date(raw)
        if expanded != raw:
            row.set_text(expanded)
    entry_row.connect("entry-activated", _expand)
    entry_row.connect("notify::has-focus", lambda r, _: _expand(r) if not r.has_focus() else None)


def normalize_tag_input(raw):
    """
    Flexible tag parser for the tags field:
      'design, urgent, #meeting'  → '#design #urgent #meeting'
      '#design #urgent'           → '#design #urgent'
      'design urgent'             → '#design #urgent'
    """
    if not raw:
        return ""
    parts = re.split(r"[,\s]+", raw.strip())
    tags = [p.lstrip("#").strip().lower() for p in parts if p.strip().lstrip("#")]
    return " ".join(f"#{t}" for t in tags if t)


def parse_tags_from_text(raw):
    """
    Extract inline #tags from free text:
      'Buy milk #shopping #home' → ('Buy milk', '#shopping #home')
    Non-# words are never treated as tags in the text field.
    """
    words = raw.split()
    tag_words  = [w for w in words if w.startswith("#") and len(w) > 1]
    clean_words = [w for w in words if not w.startswith("#")]
    text = " ".join(clean_words).strip() or raw
    return text, normalize_tag_input(" ".join(tag_words))


def get_tags(tags_str):
    """'#shopping #home' → ['shopping', 'home']"""
    if not tags_str:
        return []
    return [t.lstrip("#") for t in tags_str.split() if t.startswith("#")]


def safe_col(row, col, default=""):
    try:
        v = row[col]
        return v if v is not None else default
    except (IndexError, KeyError):
        return default


# ══════════════════════════════════════════════════════
# Database
# ── MPRIS (D-Bus media player control) ─────────────────────────────────

def mpris_get_players():
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = bus.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "ListNames",
            None, GLib.VariantType.new("(as)"), Gio.DBusCallFlags.NONE, -1, None,
        )
        return [n for n in reply[0] if n.startswith("org.mpris.MediaPlayer2.")]
    except Exception:
        return []


def mpris_get_state(player_name):
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(       # 7 args — no trailing None
            bus, Gio.DBusProxyFlags.NONE, None,
            player_name, "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties", None,
        )
        pb_v = proxy.call_sync("Get",
            GLib.Variant("(ss)", ("org.mpris.MediaPlayer2.Player", "PlaybackStatus")),
            Gio.DBusCallFlags.NONE, -1, None)
        md_v = proxy.call_sync("Get",
            GLib.Variant("(ss)", ("org.mpris.MediaPlayer2.Player", "Metadata")),
            Gio.DBusCallFlags.NONE, -1, None)
        pb_status = str(pb_v[0])              # GI returns Python str directly
        md = md_v[0]                           # GI returns Python dict directly
        title = str(md.get("xesam:title", "") or "")
        album = str(md.get("xesam:album", "") or "")
        artists_raw = md.get("xesam:artist", []) or []
        if isinstance(artists_raw, str):
            artist = artists_raw
        else:
            artist = ", ".join(str(a) for a in artists_raw)
        return {"title": title, "artist": artist, "album": album, "status": pb_status}
    except Exception:
        return None


def mpris_action(player_name, action):
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            player_name, "/org/mpris/MediaPlayer2",
            "org.mpris.MediaPlayer2.Player", None,
        )
        proxy.call_sync(action, None, Gio.DBusCallFlags.NONE, -1, None)
    except Exception:
        pass


def mpris_raise(player_name):
    """Bring the media player window to the foreground via MPRIS Raise."""
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            player_name, "/org/mpris/MediaPlayer2",
            "org.mpris.MediaPlayer2", None,
        )
        proxy.call_sync("Raise", None, Gio.DBusCallFlags.NONE, -1, None)
    except Exception:
        pass

# ══════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                description TEXT,
                color TEXT DEFAULT '#4fa8c4'
            );
            CREATE TABLE IF NOT EXISTS milestone (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS todo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                priority TEXT DEFAULT 'normal',
                tags TEXT DEFAULT '',
                order_pos INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS goal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS writing_entry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                date TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS note (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                pinned INTEGER NOT NULL DEFAULT 0,
                created_date TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS file (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                description TEXT,
                added_date TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS template (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS template_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                day_offset INTEGER NOT NULL DEFAULT 0,
                duration_days INTEGER NOT NULL DEFAULT 7,
                FOREIGN KEY (template_id) REFERENCES template(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS project_template (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                color TEXT DEFAULT '#4fa8c4',
                emoji TEXT DEFAULT '',
                builtin INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS pt_todo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                tags TEXT DEFAULT '',
                recur_days INTEGER DEFAULT 0,
                FOREIGN KEY (template_id) REFERENCES project_template(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS pt_goal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                tags TEXT DEFAULT '',
                FOREIGN KEY (template_id) REFERENCES project_template(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS pt_milestone (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                day_offset INTEGER DEFAULT 0,
                duration_days INTEGER DEFAULT 7,
                FOREIGN KEY (template_id) REFERENCES project_template(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS project_group (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position INTEGER DEFAULT 0,
                collapsed INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS goal_todo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (goal_id) REFERENCES goal(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS pomodoro_session (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                completed_at  TEXT NOT NULL,
                duration_mins INTEGER DEFAULT 25
            );
            CREATE TABLE IF NOT EXISTS playlist_item (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title      TEXT NOT NULL,
                artist     TEXT DEFAULT '',
                album      TEXT DEFAULT '',
                url        TEXT DEFAULT '',
                position   INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            );
        """)


def migrate_db():
    """Add columns that didn't exist in earlier versions."""
    with get_db() as c:
        for sql in [
            "ALTER TABLE todo          ADD COLUMN tags      TEXT    DEFAULT ''",
            "ALTER TABLE todo          ADD COLUMN order_pos INTEGER DEFAULT 0",
            "ALTER TABLE milestone     ADD COLUMN priority TEXT DEFAULT 'normal'",
            "ALTER TABLE milestone     ADD COLUMN status   TEXT DEFAULT 'pending'",
            "ALTER TABLE milestone     ADD COLUMN notes    TEXT DEFAULT ''",
            "ALTER TABLE milestone     ADD COLUMN tags     TEXT DEFAULT ''",
            "ALTER TABLE goal          ADD COLUMN tags     TEXT DEFAULT ''",
            "ALTER TABLE goal          ADD COLUMN due_date TEXT DEFAULT ''",
            "ALTER TABLE project       ADD COLUMN emoji      TEXT    DEFAULT ''",
            "ALTER TABLE todo          ADD COLUMN completed_date TEXT DEFAULT ''",
            "ALTER TABLE milestone     ADD COLUMN completion     INTEGER DEFAULT 0",
            "ALTER TABLE writing_entry ADD COLUMN tags     TEXT DEFAULT ''",
            "ALTER TABLE note          ADD COLUMN tags     TEXT DEFAULT ''",
            "ALTER TABLE file          ADD COLUMN tags     TEXT DEFAULT ''",
            "ALTER TABLE todo          ADD COLUMN recur_days    INTEGER DEFAULT 0",
            "ALTER TABLE todo          ADD COLUMN estimate_mins INTEGER DEFAULT 0",
            "ALTER TABLE todo          ADD COLUMN blocked_by    INTEGER DEFAULT 0",
            "ALTER TABLE milestone     ADD COLUMN auto_tag      TEXT    DEFAULT ''",
            "ALTER TABLE milestone     ADD COLUMN blocked_by    INTEGER DEFAULT 0",
            "ALTER TABLE project       ADD COLUMN group_id      INTEGER DEFAULT 0",
            "ALTER TABLE writing_entry ADD COLUMN content_format TEXT DEFAULT 'plain'",
            "ALTER TABLE todo          ADD COLUMN due_date       TEXT DEFAULT ''",
            "ALTER TABLE goal ADD COLUMN start_date  TEXT    DEFAULT ''",
            "ALTER TABLE goal ADD COLUMN end_date    TEXT    DEFAULT ''",
            "ALTER TABLE goal ADD COLUMN status      TEXT    DEFAULT 'pending'",
            "ALTER TABLE goal ADD COLUMN priority    TEXT    DEFAULT 'normal'",
            "ALTER TABLE goal ADD COLUMN notes       TEXT    DEFAULT ''",
            "ALTER TABLE goal ADD COLUMN blocked_by  INTEGER DEFAULT 0",
            "ALTER TABLE todo ADD COLUMN goal_id         INTEGER DEFAULT NULL",
            "ALTER TABLE todo ADD COLUMN recur_end_date  TEXT    DEFAULT ''",
            "ALTER TABLE goal ADD COLUMN linked_note_id  INTEGER DEFAULT NULL",
            "ALTER TABLE playlist_item ADD COLUMN album TEXT DEFAULT ''",
            "ALTER TABLE project_template ADD COLUMN builtin INTEGER DEFAULT 0",
            "ALTER TABLE goal ADD COLUMN today_priority INTEGER DEFAULT 0",
            "ALTER TABLE project ADD COLUMN position INTEGER DEFAULT 0",
        ]:
            try:
                c.execute(sql)
            except Exception:
                pass
        # Populate NULLs left by previous migration runs
        c.execute("UPDATE milestone SET priority='normal' WHERE priority IS NULL")
        c.execute("UPDATE milestone SET status='pending'  WHERE status   IS NULL")

    try:
        with get_db() as c:
            ms = c.execute("SELECT * FROM milestone").fetchall()
            for m in ms:
                exists = c.execute(
                    "SELECT id FROM goal WHERE project_id=? AND text=?",
                    (m["project_id"], m["title"])
                ).fetchone()
                if not exists:
                    c.execute(
                        "INSERT INTO goal (project_id,text,done,tags,due_date,start_date,end_date,status,priority,notes,blocked_by)"
                        " VALUES (?,?,0,?,?,?,?,?,?,?,?)",
                        (m["project_id"], m["title"],
                         safe_col(m,"tags",""), safe_col(m,"end_date",""),
                         safe_col(m,"start_date",""), safe_col(m,"end_date",""),
                         safe_col(m,"status","pending"), safe_col(m,"priority","normal"),
                         safe_col(m,"notes",""), int(safe_col(m,"blocked_by") or 0))
                    )
    except Exception:
        pass
    seed_builtin_templates()


def get_setting(key, default=""):
    with get_db() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

def set_setting(key, value):
    with get_db() as c:
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))


def db_projects():
    with get_db() as c:
        return c.execute("SELECT * FROM project ORDER BY id").fetchall()

_SORT_MODES = ["manual", "alphabetical", "recently_active", "date_added",
               "most_goals", "most_outstanding"]

def db_projects_sorted(mode="manual"):
    """Non-archived projects in sidebar sort order."""
    with get_db() as c:
        if mode == "alphabetical":
            return c.execute(
                "SELECT * FROM project WHERE status!='archived' "
                "ORDER BY name COLLATE NOCASE ASC").fetchall()
        elif mode == "date_added":
            return c.execute(
                "SELECT * FROM project WHERE status!='archived' ORDER BY id ASC").fetchall()
        elif mode == "recently_active":
            return c.execute("""
                SELECT p.*,
                    COALESCE((SELECT MAX(id) FROM todo      WHERE project_id=p.id), 0) +
                    COALESCE((SELECT MAX(id) FROM milestone WHERE project_id=p.id), 0) +
                    COALESCE((SELECT MAX(id) FROM note      WHERE project_id=p.id), 0) AS _act
                FROM project p WHERE p.status!='archived'
                ORDER BY _act DESC, p.id DESC""").fetchall()
        elif mode == "most_goals":
            return c.execute("""
                SELECT p.*,
                    (SELECT COUNT(*) FROM goal WHERE project_id=p.id AND done=0) AS _gc
                FROM project p WHERE p.status!='archived'
                ORDER BY _gc DESC, p.name COLLATE NOCASE ASC""").fetchall()
        elif mode == "most_outstanding":
            return c.execute("""
                SELECT p.*,
                    (SELECT COUNT(*) FROM todo WHERE project_id=p.id AND done=0) +
                    (SELECT COUNT(*) FROM goal WHERE project_id=p.id AND done=0) AS _oc
                FROM project p WHERE p.status!='archived'
                ORDER BY _oc DESC, p.name COLLATE NOCASE ASC""").fetchall()
        else:  # manual
            return c.execute(
                "SELECT * FROM project WHERE status!='archived' "
                "ORDER BY COALESCE(position, id*10) ASC, id ASC").fetchall()

def db_reorder_project(pid, target_pid):
    """Move project pid to immediately before target_pid in manual order."""
    with get_db() as c:
        rows = c.execute(
            "SELECT id FROM project WHERE status!='archived' "
            "ORDER BY COALESCE(position, id*10) ASC, id ASC").fetchall()
        ids = [r["id"] for r in rows]
        if pid not in ids or target_pid not in ids:
            return
        ids.remove(pid)
        ids.insert(ids.index(target_pid), pid)
        for i, rid in enumerate(ids):
            c.execute("UPDATE project SET position=? WHERE id=?", (i * 10, rid))

def db_project(pid):
    with get_db() as c:
        return c.execute("SELECT * FROM project WHERE id=?", (pid,)).fetchone()

def db_todos(pid):
    with get_db() as c:
        return c.execute(
            "SELECT * FROM todo WHERE project_id=?"
            " ORDER BY done ASC, COALESCE(order_pos,0) ASC, id ASC",
            (pid,),
        ).fetchall()


def db_templates():
    with get_db() as c:
        return c.execute("SELECT * FROM template ORDER BY name").fetchall()


def db_template_items(tid):
    with get_db() as c:
        return c.execute(
            "SELECT * FROM template_item WHERE template_id=? ORDER BY day_offset",
            (tid,),
        ).fetchall()

def db_project_templates():
    with get_db() as c:
        return c.execute("SELECT * FROM project_template ORDER BY name").fetchall()

def db_pt_items(tid):
    with get_db() as c:
        todos = c.execute("SELECT * FROM pt_todo WHERE template_id=?", (tid,)).fetchall()
        goals = c.execute("SELECT * FROM pt_goal WHERE template_id=?", (tid,)).fetchall()
        ms    = c.execute("SELECT * FROM pt_milestone WHERE template_id=?", (tid,)).fetchall()
    return todos, goals, ms

def seed_builtin_templates():
    """Insert the five example templates on first run (idempotent)."""
    _BUILTIN = [
        {
            "name": "Academic Semester", "emoji": "🎓", "color": "#4fa8c4",
            "milestones": [
                ("Orientation", 0, 14),
                ("Midterm Prep", 45, 21),
                ("Final Exam Week", 90, 14),
                ("Grades Due", 110, 7),
            ],
            "tasks": [
                ("Register for courses", "high"),
                ("Buy textbooks", "normal"),
                ("Submit reading list", "normal"),
                ("Set weekly study schedule", "normal"),
                ("Form study group", "low"),
            ],
            "goals": [
                "Complete all assignments on time",
                "Attend all scheduled lectures",
                "Finish revision before exam week",
            ],
        },
        {
            "name": "Writing Project", "emoji": "✍️", "color": "#c47a4f",
            "milestones": [
                ("Research & Notes", 0, 14),
                ("Outline", 14, 7),
                ("First Draft", 21, 30),
                ("Revision", 51, 14),
                ("Final / Submission", 65, 7),
            ],
            "tasks": [
                ("Build reference / bibliography list", "high"),
                ("Set daily word count target", "normal"),
                ("Send draft to editor or peer reader", "normal"),
                ("Final proofread", "high"),
                ("Format for submission", "normal"),
            ],
            "goals": [
                "Complete first draft",
                "Hit target word count",
                "Submit by deadline",
            ],
        },
        {
            "name": "Conference / Talk", "emoji": "🎤", "color": "#7a4fc4",
            "milestones": [
                ("Submit Proposal", 0, 7),
                ("Proposal Accepted", 30, 1),
                ("Slides & Materials", 60, 14),
                ("Rehearsal Period", 80, 7),
                ("Event Day", 90, 1),
            ],
            "tasks": [
                ("Write abstract / proposal", "high"),
                ("Book travel and accommodation", "normal"),
                ("Prepare handout or takeaway", "normal"),
                ("Confirm A/V requirements", "normal"),
                ("Write bio for program", "low"),
                ("Send thank-you emails after event", "low"),
            ],
            "goals": [
                "Submit proposal on time",
                "Rehearse talk at least three times",
                "Receive audience feedback",
            ],
        },
        {
            "name": "Software Sprint", "emoji": "💻", "color": "#4fc47a",
            "milestones": [
                ("Sprint Planning", 0, 2),
                ("Development", 2, 10),
                ("Code Review", 12, 3),
                ("QA & Testing", 15, 3),
                ("Deploy", 18, 1),
            ],
            "tasks": [
                ("Write or update changelog", "normal"),
                ("Run full test suite", "high"),
                ("Write release notes", "normal"),
                ("Update documentation", "normal"),
                ("Tag release in version control", "high"),
            ],
            "goals": [
                "Ship on schedule",
                "Zero critical bugs at launch",
                "All tests passing before deploy",
            ],
        },
        {
            "name": "Event Planning", "emoji": "🎉", "color": "#c4a84f",
            "milestones": [
                ("Venue Booked", 0, 7),
                ("Invitations Sent", 7, 7),
                ("Catering Confirmed", 21, 7),
                ("Final Head Count", 35, 3),
                ("Event Day", 45, 1),
            ],
            "tasks": [
                ("Book venue", "high"),
                ("Design and send invitations", "high"),
                ("Arrange catering or food", "normal"),
                ("Confirm guest list and RSVPs", "normal"),
                ("Set up venue on the day", "normal"),
                ("Arrange post-event cleanup", "low"),
            ],
            "goals": [
                "Stay on budget",
                "All guests notified two weeks before",
                "Event runs to schedule",
            ],
        },
    ]
    with get_db() as c:
        existing = {r[0] for r in c.execute(
            "SELECT name FROM project_template WHERE builtin=1").fetchall()}
        for tmpl in _BUILTIN:
            if tmpl["name"] in existing:
                continue
            c.execute(
                "INSERT INTO project_template (name, description, color, emoji, builtin) "
                "VALUES (?,?,?,?,1)",
                (tmpl["name"], "", tmpl["color"], tmpl["emoji"]))
            tid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            for title, offset, dur in tmpl.get("milestones", []):
                c.execute(
                    "INSERT INTO pt_milestone (template_id, title, day_offset, duration_days) "
                    "VALUES (?,?,?,?)", (tid, title, offset, dur))
            for text, pri in tmpl.get("tasks", []):
                c.execute(
                    "INSERT INTO pt_todo (template_id, text, priority) VALUES (?,?,?)",
                    (tid, text, pri))
            for goal_text in tmpl.get("goals", []):
                c.execute(
                    "INSERT INTO pt_goal (template_id, text) VALUES (?,?)",
                    (tid, goal_text))


def db_goals(pid):
    with get_db() as c:
        return c.execute(
            "SELECT * FROM goal WHERE project_id=? "
            "ORDER BY CASE WHEN end_date='' THEN '9999-99-99' ELSE end_date END ASC, id ASC",
            (pid,)
        ).fetchall()


def db_all_goals_with_project():
    with get_db() as c:
        return c.execute(
            "SELECT g.*, p.name AS project_name, p.color AS project_color, p.id AS project_id "
            "FROM goal g JOIN project p ON g.project_id = p.id "
            "WHERE g.start_date != '' AND g.end_date != '' AND g.done = 0 "
            "AND p.status != 'archived' "
            "ORDER BY g.end_date"
        ).fetchall()

def db_goal_todos(goal_id):
    with get_db() as c:
        return c.execute(
            "SELECT * FROM goal_todo WHERE goal_id=? ORDER BY done ASC, id ASC", (goal_id,)
        ).fetchall()

def db_groups():
    with get_db() as c:
        return c.execute("SELECT * FROM project_group ORDER BY position, id").fetchall()

def db_create_group(name):
    with get_db() as c:
        c.execute("INSERT INTO project_group (name) VALUES (?)", (name,))

def _confirm_delete(parent, heading, body, on_confirm):
    dlg = Adw.AlertDialog(heading=heading, body=body)
    dlg.add_response("cancel", "Cancel")
    dlg.add_response("delete", "Delete")
    dlg.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    dlg.set_default_response("cancel")
    dlg.set_close_response("cancel")
    dlg.connect("response", lambda d, r: on_confirm() if r == "delete" else None)
    dlg.present(parent)

def db_delete_group(gid):
    with get_db() as c:
        c.execute("UPDATE project SET group_id=0 WHERE group_id=?", (gid,))
        c.execute("DELETE FROM project_group WHERE id=?", (gid,))

def db_set_project_group(pid, gid):
    with get_db() as c:
        c.execute("UPDATE project SET group_id=? WHERE id=?", (gid, pid))

def db_notes(pid):
    with get_db() as c:
        return c.execute("SELECT * FROM note WHERE project_id=? ORDER BY pinned DESC, id DESC", (pid,)).fetchall()

def db_files(pid):
    with get_db() as c:
        return c.execute("SELECT * FROM file WHERE project_id=? ORDER BY added_date DESC", (pid,)).fetchall()


def db_playlist_items(pid):
    with get_db() as c:
        return c.execute(
            "SELECT id, project_id, title, "
            "COALESCE(artist,'') AS artist, COALESCE(album,'') AS album, "
            "COALESCE(url,'') AS url, COALESCE(position,0) AS position "
            "FROM playlist_item WHERE project_id=? ORDER BY position, id", (pid,)
        ).fetchall()


def db_monthly_summary():
    """Return (due_count, high_priority_count, overdue_count) for the next 30 days."""
    today  = date.today().isoformat()
    cutoff = (date.today() + timedelta(days=30)).isoformat()
    with get_db() as c:
        due = c.execute(
            "SELECT priority FROM todo WHERE done=0 AND due_date!='' AND due_date>=? AND due_date<=?",
            (today, cutoff)).fetchall()
        overdue_count = c.execute(
            "SELECT COUNT(*) FROM todo WHERE done=0 AND due_date!='' AND due_date<?",
            (today,)).fetchone()[0]
    high = sum(1 for t in due if safe_col(t, "priority") == "high")
    return len(due), high, overdue_count


def db_today_tasks():
    """Tasks due today or overdue, sorted high→normal→low then by due_date."""
    today = date.today().isoformat()
    with get_db() as c:
        return c.execute("""
            SELECT t.*, p.name as project_name, p.color as project_color
            FROM todo t JOIN project p ON t.project_id = p.id
            WHERE t.done=0 AND t.due_date!='' AND t.due_date<=?
            ORDER BY CASE t.priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
                     t.due_date ASC
        """, (today,)).fetchall()


def db_today_goals():
    """Return (primary_goal, stretch_goal) — either can be None."""
    with get_db() as c:
        primary = c.execute(
            "SELECT g.*, p.name as project_name, p.emoji as project_emoji, p.id as project_id "
            "FROM goal g JOIN project p ON g.project_id=p.id "
            "WHERE g.today_priority=1 LIMIT 1").fetchone()
        stretch = c.execute(
            "SELECT g.*, p.name as project_name, p.emoji as project_emoji, p.id as project_id "
            "FROM goal g JOIN project p ON g.project_id=p.id "
            "WHERE g.today_priority=2 LIMIT 1").fetchone()
    return primary, stretch


def db_set_today_goal(gid, priority):
    """Set goal today_priority; clears any other goal already at that priority."""
    with get_db() as c:
        if priority > 0:
            c.execute("UPDATE goal SET today_priority=0 WHERE today_priority=?", (priority,))
        c.execute("UPDATE goal SET today_priority=? WHERE id=?", (priority, gid))


def db_due_days_this_month(year, month):
    """Return set of day-numbers (1-31) that have tasks or goals due in that month."""
    import calendar as _cal
    last = _cal.monthrange(year, month)[1]
    start = f"{year:04d}-{month:02d}-01"
    end   = f"{year:04d}-{month:02d}-{last:02d}"
    with get_db() as c:
        t_rows = c.execute(
            "SELECT due_date FROM todo WHERE done=0 AND due_date>=? AND due_date<=?",
            (start, end)).fetchall()
        g_rows = c.execute(
            "SELECT end_date FROM goal WHERE done=0 AND end_date>=? AND end_date<=?",
            (start, end)).fetchall()
    days = set()
    for row in t_rows + g_rows:
        val = row[0]
        try:
            days.add(int(val[8:10]))
        except (TypeError, ValueError, IndexError):
            pass
    return days


def db_record_pomodoro():
    with get_db() as c:
        c.execute("INSERT INTO pomodoro_session (completed_at, duration_mins) VALUES (?,25)",
                  (datetime.now().isoformat(),))


def db_pomodoro_week():
    """Return (session_count, total_minutes) for the current calendar week (Mon–Sun)."""
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    with get_db() as c:
        row = c.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(duration_mins),0) as total"
            " FROM pomodoro_session WHERE completed_at>=?",
            (week_start,)).fetchone()
    return (row["cnt"] or 0), (row["total"] or 0)


def db_playlist_name(pid, project_name):
    key = f"playlist_name_{pid}"
    with get_db() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else f"Focus playlist — {project_name}"


def db_playlist_set_name(pid, name):
    key = f"playlist_name_{pid}"
    with get_db() as c:
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, name))


def db_coming_up(days=90):
    today  = date.today().isoformat()
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    items = []
    with get_db() as c:
        gs = c.execute(
            "SELECT g.id, g.text AS title, g.end_date, "
            "g.status AS item_status, g.priority, 'Goal' AS kind, "
            "p.name AS project_name, p.color AS project_color, p.id AS project_id "
            "FROM goal g JOIN project p ON g.project_id = p.id "
            "WHERE g.end_date >= ? AND g.end_date <= ? AND g.done = 0 AND g.end_date != '' "
            "ORDER BY g.end_date",
            (today, cutoff),
        ).fetchall()
        ts = c.execute(
            "SELECT t.id, t.text AS title, t.due_date AS end_date, "
            "'' AS item_status, t.priority, 'Task' AS kind, "
            "p.name AS project_name, p.color AS project_color, p.id AS project_id "
            "FROM todo t JOIN project p ON t.project_id = p.id "
            "WHERE t.due_date >= ? AND t.due_date <= ? AND t.done = 0 "
            "ORDER BY t.due_date",
            (today, cutoff),
        ).fetchall()
    for row in gs: items.append({k: row[k] for k in row.keys()})
    for row in ts: items.append({k: row[k] for k in row.keys()})
    items.sort(key=lambda x: x["end_date"] or "")
    return items


def db_all_files_with_project():
    with get_db() as c:
        return c.execute(
            "SELECT f.*, p.name AS project_name, p.color AS project_color, p.id AS project_id "
            "FROM file f JOIN project p ON f.project_id = p.id "
            "ORDER BY p.name, f.added_date DESC"
        ).fetchall()


def db_search(query):
    """Full-text search across todos, goals, notes, files."""
    q = f"%{query.lower()}%"
    results = []
    with get_db() as c:
        rows = c.execute(
            "SELECT 'Task' AS kind, t.text AS title, t.done AS is_done, "
            "p.name AS project_name, p.id AS project_id "
            "FROM todo t JOIN project p ON t.project_id = p.id "
            "WHERE lower(t.text) LIKE ? OR lower(COALESCE(t.tags,'')) LIKE ?",
            (q, q),
        ).fetchall()
        results += [{k: r[k] for k in r.keys()} for r in rows]
        goals = c.execute(
            "SELECT 'Goal' AS kind, g.text AS title, g.done AS is_done, "
            "p.name AS project_name, p.id AS project_id "
            "FROM goal g JOIN project p ON g.project_id=p.id "
            "WHERE g.text LIKE ? OR g.notes LIKE ?",
            (q, q)
        ).fetchall()
        results += [{k: r[k] for k in r.keys()} for r in goals]
        rows = c.execute(
            "SELECT 'Note' AS kind, n.content AS title, 0 AS is_done, "
            "p.name AS project_name, p.id AS project_id "
            "FROM note n JOIN project p ON n.project_id = p.id "
            "WHERE lower(n.content) LIKE ?",
            (q,),
        ).fetchall()
        results += [{k: r[k] for k in r.keys()} for r in rows]
        rows = c.execute(
            "SELECT 'File' AS kind, f.name AS title, 0 AS is_done, "
            "p.name AS project_name, p.id AS project_id "
            "FROM file f JOIN project p ON f.project_id = p.id "
            "WHERE lower(f.name) LIKE ? OR lower(f.path) LIKE ?",
            (q, q),
        ).fetchall()
        results += [{k: r[k] for k in r.keys()} for r in rows]
    return results[:60]


def compute_goal_status(g, linked_tasks=None):
    """Return 'done'|'active'|'future'|'overdue' by inspecting dates and tasks."""
    if g["done"]:
        return "done"
    today_s = date.today().isoformat()
    start = safe_col(g, "start_date") or ""
    end   = safe_col(g, "end_date") or ""
    if end and end < today_s:
        if linked_tasks is None:
            with get_db() as c:
                linked_tasks = c.execute(
                    "SELECT done FROM todo WHERE goal_id=?", (g["id"],)
                ).fetchall()
        if any(not t["done"] for t in linked_tasks):
            return "overdue"
        return "done"  # all tasks done even if end passed
    if start and start > today_s:
        return "future"
    return "active"


def project_health(pid):
    """Return ('green'|'yellow'|'red', reason_string) for a project."""
    today = date.today()
    goals = db_goals(pid)
    todos = db_todos(pid)

    overdue_goals = []
    for g in goals:
        if compute_goal_status(g) == "overdue":
            overdue_goals.append(g["text"])

    overdue_tasks = [t for t in todos if not t["done"] and safe_col(t, "due_date")
                     and safe_col(t, "due_date") < today.isoformat()]

    undone = [t for t in todos if not t["done"]]
    done_ct = sum(1 for t in todos if t["done"])
    pct = done_ct / len(todos) if todos else 1.0

    if overdue_goals:
        return "red", f"{len(overdue_goals)} overdue goal{'s' if len(overdue_goals)>1 else ''}"
    if overdue_tasks:
        return "red", f"{len(overdue_tasks)} overdue task{'s' if len(overdue_tasks)>1 else ''}"
    if undone and pct < 0.1 and len(todos) > 3:
        return "yellow", "Getting started"
    if undone:
        return "yellow", "No recent activity"
    return "green", "On track"


def _generate_markdown(pid):
    """Produce a Markdown report for a project."""
    p       = db_project(pid)
    todos   = db_todos(pid)
    goals   = db_goals(pid)

    done_t = sum(1 for t in todos if t["done"])
    pct    = int(done_t / len(todos) * 100) if todos else 0

    lines = [f"# {p['name']}\n"]
    lines.append(f"**Status:** {p['status']}  |  **Progress:** {pct}% ({done_t}/{len(todos)} tasks)\n")
    if safe_col(p, "description"):
        lines.append(f"> {p['description']}\n")
    lines.append("")

    undone_t = [t for t in todos if not t["done"]]
    if undone_t:
        lines.append("## Open Tasks\n")
        for t in undone_t:
            pri = t["priority"] or "normal"
            pri_s = f" `{pri}`" if pri != "normal" else ""
            lines.append(f"- [ ] {t['text']}{pri_s}")
        lines.append("")

    done_tasks = [t for t in todos if t["done"]]
    if done_tasks:
        lines.append("## Completed Tasks\n")
        for t in done_tasks:
            lines.append(f"- [x] {t['text']}")
        lines.append("")

    if goals:
        lines.append("\n## Goals\n")
        for g in goals:
            status = safe_col(g, "status") or ("done" if g["done"] else "pending")
            end = safe_col(g, "end_date")
            lines.append(f"- {'✓' if g['done'] else '○'} **{g['text']}**" +
                         (f" (due {end})" if end else "") + f" [{status}]")

    return "\n".join(lines)


def all_tagged_items(pid):
    """Return a flat list of dicts: {kind, label, tags, done} for every item in the project."""
    items = []

    def _collect(rows, kind, label_fn, done_fn):
        for row in rows:
            tags = safe_col(row, "tags")
            if tags:
                items.append({
                    "kind":  kind,
                    "label": label_fn(row),
                    "tags":  tags,
                    "done":  done_fn(row),
                })

    _collect(db_todos(pid),      "Task",      lambda r: r["text"],
             lambda r: bool(r["done"]))
    _collect(db_goals(pid),      "Goal",      lambda r: r["text"],
             lambda r: bool(r["done"]))
    _collect(db_notes(pid),      "Note",
             lambda r: r["content"][:60].replace("\n", " "),
             lambda r: False)
    _collect(db_files(pid),      "File",      lambda r: r["name"],
             lambda r: False)
    return items


def _months_later(dt, n):
    """Return datetime approximately n calendar months after dt."""
    m = dt.month + n
    y = dt.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return dt.replace(year=y, month=m)


# ══════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════

def parse_rgba(hex_str):
    rgba = Gdk.RGBA()
    if not rgba.parse(hex_str or "#4fa8c4"):
        rgba.parse("#4fa8c4")
    return rgba


def rgba_to_hex(rgba):
    return "#{:02x}{:02x}{:02x}".format(
        int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
    )


def tip_banner(key, text):
    """Return an Adw.Banner that dismisses permanently when the user clicks 'Got it'."""
    if get_setting(f"tip_{key}") == "1":
        return None
    banner = Adw.Banner(title=text, button_label="Got it", revealed=True)
    def _dismiss(_):
        set_setting(f"tip_{key}", "1")
        banner.set_revealed(False)
    banner.connect("button-clicked", _dismiss)
    return banner


def color_dot(hex_color, size=14):
    da = Gtk.DrawingArea()
    da.set_content_width(size)
    da.set_content_height(size)
    da.set_can_target(False)
    da.set_focusable(False)
    rgba = parse_rgba(hex_color)

    def draw(area, cr, w, h):
        r = min(w, h) / 2 - 1
        cr.arc(w / 2, h / 2, r, 0, 2 * math.pi)
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 1.0)
        cr.fill()

    da.set_draw_func(draw)
    return da


def _refresh_calendar_marks(cal):
    """Mark days that have tasks or goals due in the currently displayed month."""
    cal.clear_marks()
    gdt = cal.get_date()
    days = db_due_days_this_month(gdt.get_year(), gdt.get_month())
    for d in days:
        cal.mark_day(d)


def clear_box(box):
    child = box.get_first_child()
    while child:
        nxt = child.get_next_sibling()
        box.remove(child)
        child = nxt

def add_dblclick(widget, callback):
    """Attach a double-click gesture that calls callback() on double left-click."""
    gc = Gtk.GestureClick.new()
    gc.set_button(1)
    gc.connect("pressed", lambda g, n, x, y: callback() if n == 2 else None)
    widget.add_controller(gc)


def section_page(title, content_widget, extra_header_widgets=None):
    """Wrap a section view in an Adw.NavigationPage with ToolbarView."""
    page = Adw.NavigationPage(title=title)
    tv = Adw.ToolbarView()
    hdr = Adw.HeaderBar()
    if extra_header_widgets:
        for w in extra_header_widgets:
            hdr.pack_end(w)
    tv.add_top_bar(hdr)
    scroll = Gtk.ScrolledWindow(vexpand=True)
    scroll.set_child(content_widget)
    tv.set_content(scroll)
    page.set_child(tv)
    return page


# ══════════════════════════════════════════════════════
# Gantt chart
# ══════════════════════════════════════════════════════

# Jewel-tone palette that pops on the dark Gantt background
GANTT_PALETTE = [
    (0.31, 0.76, 0.97, 0.88),  # sky blue        (cool)
    (0.98, 0.61, 0.35, 0.88),  # coral-orange    (warm)
    (0.40, 0.82, 0.67, 0.88),  # emerald         (cool)
    (0.94, 0.43, 0.63, 0.88),  # rose-pink       (warm)
    (0.35, 0.81, 0.77, 0.88),  # teal            (cool)
    (0.97, 0.79, 0.28, 0.88),  # golden amber    (warm)
    (0.60, 0.85, 0.40, 0.88),  # lime green      (cool)
    (0.71, 0.50, 0.92, 0.88),  # soft violet     (cool-ish, last so never adjacent to teal)
]

class _GanttDrawArea(Gtk.DrawingArea):
    """Internal drawing widget for the Gantt chart."""

    def __init__(self, items, accent, view_start=None, view_end=None, show_project_label=False, tasks=None, show_tasks=True, zoom=1.0, label_w_base=170, on_label_resize=None, use_palette=True, color_mode="palette", on_bar_activated=None):
        super().__init__()
        self._items = items
        self._accent = accent
        self._view_start = view_start
        self._view_end = view_end
        self._show_project_label = show_project_label
        self._tasks = tasks or []
        self._show_tasks = show_tasks
        self._zoom = max(0.5, min(4.0, zoom))
        self._label_w_base = label_w_base
        self._on_label_resize = on_label_resize
        self._use_palette = use_palette
        self._color_mode = color_mode
        self._on_bar_activated = on_bar_activated
        self._drag_active = False
        self._drag_start_lw = label_w_base
        row_h = int(36 * self._zoom)
        self.set_content_height(max(80, len(items) * row_h + int(48 * self._zoom)))
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

        drag = Gtk.GestureDrag.new()
        drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect("drag-begin", self._on_divider_drag_begin)
        drag.connect("drag-update", self._on_divider_drag_update)
        drag.connect("drag-end", self._on_divider_drag_end)
        self.add_controller(drag)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_divider_motion)
        self.add_controller(motion)

        gc = Gtk.GestureClick.new()
        gc.set_button(1)
        gc.connect("pressed", self._on_bar_click)
        self.add_controller(gc)

    def _on_bar_click(self, gesture, n_press, x, y):
        if n_press != 2 or not self._on_bar_activated:
            return
        z = self._zoom
        HDR_H = int(28 * z)
        ROW_H = int(36 * z)
        if y < HDR_H:
            return
        idx = int((y - HDR_H) / ROW_H)
        if 0 <= idx < len(self._items):
            self._on_bar_activated(self._items[idx])

    def _bar_color(self, item, idx=0):
        status = compute_goal_status(item)
        if status == "overdue":
            return (0.88, 0.11, 0.14, 0.92)

        mode = self._color_mode
        if mode == "palette":
            r, g, b, a = GANTT_PALETTE[idx % len(GANTT_PALETTE)]
        elif mode == "project":
            # Use each item's own project colour exactly; fall back to accent
            pc_hex = item.get("_project_color") or ""
            if pc_hex:
                pc = parse_rgba(pc_hex)
                r, g, b, a = pc.red, pc.green, pc.blue, 0.88
            else:
                r, g, b, a = self._accent.red, self._accent.green, self._accent.blue, 0.88
        else:
            # System-theme mode: generate tonal variants from the project accent
            ar, ag, ab = self._accent.red, self._accent.green, self._accent.blue
            h, s, v = colorsys.rgb_to_hsv(ar, ag, ab)
            VARIANTS = [
                (h,                  s,            min(1.0, v * 1.00)),
                ((h + 0.08) % 1.0,  s * 0.85,     min(1.0, v * 1.15)),
                ((h - 0.08) % 1.0,  min(1.0, s * 1.10), min(1.0, v * 0.90)),
                (h,                  s * 0.65,     min(1.0, v * 1.25)),
                ((h + 0.15) % 1.0,  s * 0.90,     min(1.0, v * 1.05)),
                ((h - 0.15) % 1.0,  s * 0.80,     min(1.0, v * 1.10)),
                (h,                  min(1.0, s * 1.15), min(1.0, v * 0.85)),
                ((h + 0.05) % 1.0,  s * 0.75,     min(1.0, v * 1.20)),
            ]
            hv, sv, vv = VARIANTS[idx % len(VARIANTS)]
            r, g, b = colorsys.hsv_to_rgb(hv, sv, vv)
            a = 0.88

        if status == "done":
            avg = (r + g + b) / 3
            f = 0.45
            return (r * f + avg * (1 - f), g * f + avg * (1 - f), b * f + avg * (1 - f), 0.60)
        return (r, g, b, a)

    def _at_divider(self, x):
        return abs(x - int(self._label_w_base * min(self._zoom, 1.5))) <= 8

    def _on_divider_drag_begin(self, gesture, sx, sy):
        if self._at_divider(sx):
            self._drag_active = True
            self._drag_start_lw = self._label_w_base
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        else:
            self._drag_active = False

    def _on_divider_drag_update(self, gesture, ox, oy):
        if not self._drag_active: return
        z = min(self._zoom, 1.5)
        new_lw = max(80, min(500, self._drag_start_lw + int(ox / z)))
        if new_lw != self._label_w_base:
            self._label_w_base = new_lw
            self.queue_draw()  # redraw in-place; no rebuild during drag

    def _on_divider_drag_end(self, gesture, ox, oy):
        if self._drag_active and self._on_label_resize:
            self._on_label_resize(self._label_w_base)  # trigger rebuild only on release
        self._drag_active = False

    def _on_divider_motion(self, ctrl, x, y):
        name = "col-resize" if self._at_divider(x) else "default"
        self.set_cursor(Gdk.Cursor.new_from_name(name))

    def _draw(self, area, cr, width, height):
        items = self._items
        if not items:
            return
        z = self._zoom
        ROW_H  = int(36 * z)
        HDR_H  = int(28 * z)
        LABEL_W = int(self._label_w_base * min(z, 1.5))  # label column grows a bit with zoom but caps
        PAD = 10

        if self._view_start and self._view_end:
            min_d, max_d = self._view_start, self._view_end
        else:
            dates = []
            for it in items:
                try:
                    dates.append(datetime.strptime(it["start_date"], "%Y-%m-%d"))
                    dates.append(datetime.strptime(it["end_date"], "%Y-%m-%d"))
                except (ValueError, KeyError):
                    pass
            if not dates:
                return
            min_d = min(dates) - timedelta(days=3)
            max_d = max(dates) + timedelta(days=3)

        total_days = max(1, (max_d - min_d).days)
        BAR_W = width - LABEL_W - PAD * 2

        def x_of(d):
            frac = (d - min_d).days / total_days
            return LABEL_W + PAD + max(0.0, min(1.0, frac)) * BAR_W

        # Background
        cr.set_source_rgba(0.10, 0.12, 0.17, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cr.select_font_face("Sans", 0, 0)
        use_months = total_days <= 800

        if use_months:
            cur = datetime(min_d.year, min_d.month, 1)
            while cur <= max_d:
                x = x_of(cur)
                is_jan = (cur.month == 1)
                cr.set_source_rgba(0.48, 0.52, 0.60, 0.40 if is_jan else 0.18)
                cr.move_to(x, 0); cr.line_to(x, height); cr.stroke()
                cr.set_source_rgba(0.78, 0.82, 0.88, 1.0 if is_jan else 0.65)
                cr.set_font_size((13 if not is_jan else 14) * z)
                cr.move_to(x + 3, HDR_H * 0.65)
                cr.show_text(cur.strftime("%Y" if is_jan else "%b"))
                cur = datetime(cur.year + (cur.month == 12), (cur.month % 12) + 1, 1)
        else:
            for yr in range(min_d.year, max_d.year + 1):
                for qm, qlbl in [(1, str(yr)), (4, "Q2"), (7, "Q3"), (10, "Q4")]:
                    try:
                        cur = datetime(yr, qm, 1)
                    except ValueError:
                        continue
                    if cur > max_d:
                        break
                    x = x_of(cur)
                    is_q1 = (qm == 1)
                    cr.set_source_rgba(0.48, 0.52, 0.60, 0.40 if is_q1 else 0.15)
                    cr.move_to(x, 0); cr.line_to(x, height); cr.stroke()
                    cr.set_source_rgba(0.78, 0.82, 0.88, 1.0 if is_q1 else 0.55)
                    cr.set_font_size((13 if is_q1 else 11) * z)
                    cr.move_to(x + 3, HDR_H * 0.65)
                    cr.show_text(qlbl)

        # Today marker
        today_dt = datetime.combine(date.today(), datetime.min.time())
        if min_d <= today_dt <= max_d:
            tx = x_of(today_dt)
            cr.set_source_rgba(0.93, 0.34, 0.20, 0.90)
            cr.set_line_width(1.5)
            cr.move_to(tx, 0); cr.line_to(tx, height); cr.stroke()
            cr.set_font_size(11 * z)
            cr.move_to(tx + 3, HDR_H * 0.40); cr.show_text("today")

        bar_pos = {}
        for i, item in enumerate(items):
            y = HDR_H + i * ROW_H
            is_overdue = (compute_goal_status(item) == "overdue")

            if is_overdue:
                cr.set_source_rgba(0.88, 0.11, 0.14, 0.09)
                cr.rectangle(0, y, width, ROW_H); cr.fill()
            elif i % 2 == 0:
                cr.set_source_rgba(1, 1, 1, 0.025)
                cr.rectangle(0, y, width, ROW_H); cr.fill()

            strip_w = 0
            if self._show_project_label and item.get("_project_color"):
                pc = parse_rgba(item["_project_color"])
                cr.set_source_rgba(pc.red, pc.green, pc.blue, 0.88)
                cr.rectangle(2, y + 5, 5, ROW_H - 10)
                cr.fill()
                strip_w = 9

            label_text = item.get("text") or item.get("title") or ""
            cr.set_font_size(14 * z)
            if is_overdue:
                cr.set_source_rgba(0.88, 0.11, 0.14, 1.0)
            else:
                cr.set_source_rgba(0.78, 0.80, 0.87, 1.0)
            cr.save()
            cr.rectangle(strip_w, y, LABEL_W - strip_w - 6, ROW_H)
            cr.clip()
            cr.move_to(strip_w + 4, y + ROW_H / 2 + 4 * z)
            cr.show_text(label_text)
            cr.restore()

            try:
                d1 = datetime.strptime(item["start_date"], "%Y-%m-%d")
                d2 = datetime.strptime(item["end_date"], "%Y-%m-%d")
            except (ValueError, KeyError):
                continue

            d1c = max(d1, min_d)
            d2c = min(d2, max_d)
            if d1c > d2c:
                continue

            x1, x2 = x_of(d1c), x_of(d2c)
            bw = max(5.0, x2 - x1)
            bx, by, bh, r = x1, y + int(7 * z), ROW_H - int(14 * z), 4.0

            mid = y + ROW_H / 2
            item_id = item.get("id")
            if item_id:
                bar_pos[item_id] = (x_of(d1), x_of(d2), mid)

            bar_rgba = self._bar_color(item, i)

            def _rounded_rect(cx, cy, cw, ch, cr_r):
                cr.move_to(cx + cr_r, cy)
                cr.line_to(cx + cw - cr_r, cy)
                cr.arc(cx + cw - cr_r, cy + cr_r, cr_r, -math.pi/2, 0)
                cr.line_to(cx + cw, cy + ch - cr_r)
                cr.arc(cx + cw - cr_r, cy + ch - cr_r, cr_r, 0, math.pi/2)
                cr.line_to(cx + cr_r, cy + ch)
                cr.arc(cx + cr_r, cy + ch - cr_r, cr_r, math.pi/2, math.pi)
                cr.line_to(cx, cy + cr_r)
                cr.arc(cx + cr_r, cy + cr_r, cr_r, math.pi, 3 * math.pi / 2)
                cr.close_path()

            cr.set_source_rgba(*bar_rgba)
            _rounded_rect(bx, by, bw, bh, r)
            cr.fill()

            priority = safe_col(item, "priority") or "normal"
            _prio_stroke = {
                "high":   (0.88, 0.11, 0.14, 0.90),
                "low":    (0.21, 0.52, 0.89, 0.90),
                "normal": (0.95, 0.80, 0.05, 0.00),  # transparent for normal
            }
            stroke_rgba = _prio_stroke.get(priority, (0, 0, 0, 0))
            if stroke_rgba[3] > 0:
                cr.set_source_rgba(*stroke_rgba)
                cr.set_line_width(1.5)
                _rounded_rect(bx, by, bw, bh, r)
                cr.stroke()

            if d1 < min_d or d2 > max_d:
                cr.set_source_rgba(1, 1, 1, 0.55)
                cr.set_font_size(9 * z)
                if d1 < min_d:
                    cr.move_to(bx + 2, by + bh - 2); cr.show_text("◀")
                if d2 > max_d:
                    cr.move_to(bx + bw - 10 * z, by + bh - 2); cr.show_text("▶")




class GanttChart(Gtk.Box):
    """Gantt chart widget showing goals for a project (or all projects if pid=None)."""

    def __init__(self, pid, project, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._pid = pid
        self._project = project
        self._win = win

        today = date.today()
        self._year_opts = (
            ["All", "3 months", "6 months"] +
            [str(y) for y in range(today.year - 1, today.year + 9)]
        )
        self._year_drop = Gtk.DropDown.new_from_strings(self._year_opts)
        self._year_drop.set_selected(0)  # default: All (show every goal regardless of year)
        self._year_drop.connect("notify::selected", lambda d, _: GLib.idle_add(self._rebuild))

        self._zoom = 1.0
        self._zoom_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.5, 3.0, 0.25)
        self._zoom_scale.set_value(1.0)
        self._zoom_scale.set_size_request(120, -1)
        self._zoom_scale.set_draw_value(False)
        self._zoom_scale.set_valign(Gtk.Align.CENTER)
        self._zoom_scale.connect("value-changed", self._on_zoom)
        zoom_lbl = Gtk.Label(label="Zoom", valign=Gtk.Align.CENTER)
        zoom_lbl.add_css_class("caption")

        self._label_w = 170
        self._color_mode = "palette"

        color_lbl = Gtk.Label(label="Colors:", valign=Gtk.Align.CENTER)
        color_lbl.add_css_class("caption")
        self._color_drop = Gtk.DropDown.new_from_strings(["Palette", "System theme", "Project colour"])
        self._color_drop.set_valign(Gtk.Align.CENTER)
        self._color_drop.set_tooltip_text("Bar colour scheme")
        self._color_drop.connect("notify::selected", self._on_color_mode)

        hdr = Gtk.Box(spacing=10, margin_bottom=2)
        hdr.append(Gtk.Label(label="View:"))
        hdr.append(self._year_drop)
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep1.set_margin_start(4); sep1.set_margin_end(4)
        hdr.append(sep1)
        hdr.append(color_lbl)
        hdr.append(self._color_drop)
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep2.set_margin_start(4); sep2.set_margin_end(4)
        hdr.append(sep2)
        hdr.append(zoom_lbl)
        hdr.append(self._zoom_scale)
        self.append(hdr)

        self._chart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.append(self._chart_box)
        self._rebuild()

    def _view_range(self):
        opt = self._year_opts[self._year_drop.get_selected()]
        if opt == "All":
            return None, None
        today = date.today()
        start = datetime(today.year, today.month, today.day)
        if opt == "3 months":
            return start, _months_later(start, 3)
        if opt == "6 months":
            return start, _months_later(start, 6)
        y = int(opt)
        return datetime(y, 1, 1), datetime(y, 12, 31)

    def _on_zoom(self, scale):
        self._zoom = scale.get_value()
        GLib.idle_add(self._rebuild)

    def _on_color_mode(self, drop, _):
        self._color_mode = ["palette", "system", "project"][drop.get_selected()]
        GLib.idle_add(self._rebuild)

    def _on_label_resize_cb(self, new_lw):
        self._label_w = new_lw
        GLib.idle_add(self._rebuild)

    def _rebuild(self):
        clear_box(self._chart_box)
        if self._pid is None:
            goals = db_all_goals_with_project()
            # convert Row to dict and map project_color
            items = []
            for g in goals:
                d = {k: g[k] for k in g.keys()}
                d["_project_color"] = d.get("project_color") or ""
                items.append(d)
        else:
            raw_goals = db_goals(self._pid)
            project_color = self._project["color"] if self._project else "#4fa8c4"
            items = []
            for g in raw_goals:
                if not safe_col(g, "start_date") or not safe_col(g, "end_date"):
                    continue
                d = {k: g[k] for k in g.keys()}
                d["_project_color"] = ""
                items.append(d)

        vstart, vend = self._view_range()
        if vstart:
            items = [it for it in items if self._in_range(it, vstart, vend)]

        if not items:
            lbl = Gtk.Label(label="No goals with dates in this period")
            lbl.add_css_class("dim-label")
            lbl.set_margin_top(8)
            self._chart_box.append(lbl)
            return

        project_color = "#4fa8c4"
        if self._project:
            project_color = safe_col(self._project, "color") or "#4fa8c4"
        accent = parse_rgba(project_color)

        da = _GanttDrawArea(items, accent, vstart, vend, show_project_label=(self._pid is None), zoom=self._zoom, label_w_base=self._label_w, on_label_resize=self._on_label_resize_cb, color_mode=self._color_mode, on_bar_activated=self._on_bar_activated_cb)
        da.set_hexpand(False)
        # Base content width on date range (3 px/day at 1× zoom) for natural scaling
        try:
            all_dates = []
            for it in items:
                if it.get("start_date"): all_dates.append(datetime.strptime(it["start_date"], "%Y-%m-%d"))
                if it.get("end_date"):   all_dates.append(datetime.strptime(it["end_date"],   "%Y-%m-%d"))
            if vstart: all_dates.append(vstart)
            if vend:   all_dates.append(vend)
            if all_dates:
                span_days = max(1, (max(all_dates) - min(all_dates)).days + 6)
            else:
                span_days = 365
        except Exception:
            span_days = 365
        LABEL_W = int(self._label_w * min(self._zoom, 1.5))
        base_w = LABEL_W + 20 + int(span_days * 3 * self._zoom)
        da.set_content_width(max(900, base_w))

        h_scroll = Gtk.ScrolledWindow()
        h_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        h_scroll.set_hexpand(True)
        h_scroll.set_child(da)
        self._chart_box.append(h_scroll)

    def _in_range(self, item, vstart, vend):
        try:
            s = datetime.strptime(item["start_date"], "%Y-%m-%d")
            e = datetime.strptime(item["end_date"], "%Y-%m-%d")
            return e >= vstart and s <= vend
        except (ValueError, KeyError):
            return False

    def _on_bar_activated_cb(self, item):
        pid = item.get("project_id") or self._pid
        if pid and self._win:
            self._win._open_project(int(pid), section="goals")


# ══════════════════════════════════════════════════════
# Dialogs
# ══════════════════════════════════════════════════════

class ProjectDialog(Adw.Window):
    def __init__(self, parent, project=None, on_save=None):
        super().__init__(
            title="Edit Project" if project else "New Project",
            modal=True, transient_for=parent,
            default_width=460, default_height=620, resizable=True,
        )
        self._project = project
        self._on_save = on_save

        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)
        grp = Adw.PreferencesGroup()

        self._name = Adw.EntryRow(title="Name")
        if project:
            self._name.set_text(project["name"])
        grp.add(self._name)

        self._emoji = Adw.EntryRow(title="Emoji")
        if project:
            self._emoji.set_text(safe_col(project, "emoji") or suggest_emoji(project["name"]))
        self._name.connect("notify::text", self._on_name_changed)
        # Emoji chooser button
        try:
            chooser = Gtk.EmojiChooser.new()
            chooser.connect("emoji-picked", lambda _c, e: self._emoji.set_text(e))
            emoji_btn = Gtk.MenuButton()
            emoji_btn.set_icon_name("face-smile-symbolic")
            emoji_btn.set_valign(Gtk.Align.CENTER)
            emoji_btn.add_css_class("flat")
            emoji_btn.set_tooltip_text("Pick emoji")
            emoji_btn.set_popover(chooser)
            self._emoji.add_suffix(emoji_btn)
        except Exception:
            pass
        grp.add(self._emoji)

        self._desc = Adw.EntryRow(title="Description")
        if project and project["description"]:
            self._desc.set_text(project["description"])
        grp.add(self._desc)

        for er in (self._name, self._emoji, self._desc):
            er.connect("entry-activated", self._save)

        status_row = Adw.ActionRow(title="Status")
        self._status = Gtk.DropDown.new_from_strings(STATUSES)
        self._status.set_valign(Gtk.Align.CENTER)
        if project and project["status"] in STATUSES:
            self._status.set_selected(STATUSES.index(project["status"]))
        status_row.add_suffix(self._status)
        grp.add(status_row)

        color_row = Adw.ActionRow(title="Color")
        self._selected_color = project["color"] if project else "#4fa8c4"
        self._swatch_das = {}

        swatch_flow = Gtk.FlowBox(max_children_per_line=8,
                                   selection_mode=Gtk.SelectionMode.NONE,
                                   column_spacing=4, row_spacing=4,
                                   valign=Gtk.Align.CENTER)

        for clr in COLOR_PALETTE:
            rgba = parse_rgba(clr)
            da = Gtk.DrawingArea()
            da.set_size_request(22, 22)

            def _draw_swatch(w, cr, width, height, rgba=rgba, c=clr):
                cr.arc(width / 2, height / 2, min(width, height) / 2 - 1.5, 0, 6.2832)
                cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 1.0)
                cr.fill()
                if self._selected_color == c:
                    cr.arc(width / 2, height / 2, min(width, height) / 2 - 3, 0, 6.2832)
                    cr.set_source_rgba(1, 1, 1, 0.9)
                    cr.set_line_width(2.5)
                    cr.stroke()

            da.set_draw_func(_draw_swatch)
            self._swatch_das[clr] = da

            btn = Gtk.Button()
            btn.add_css_class("flat")
            btn.set_child(da)
            btn.set_tooltip_text(clr)

            def _pick(b, c=clr):
                self._selected_color = c
                for d in self._swatch_das.values():
                    d.queue_draw()

            btn.connect("clicked", _pick)
            swatch_flow.append(btn)

        # Custom colour via system picker
        self._custom_btn = Gtk.ColorButton()
        self._custom_btn.set_valign(Gtk.Align.CENTER)
        self._custom_btn.set_rgba(parse_rgba(self._selected_color))
        self._custom_btn.set_tooltip_text("Custom color…")

        def _on_custom(b):
            self._selected_color = rgba_to_hex(b.get_rgba())
            for d in self._swatch_das.values():
                d.queue_draw()

        self._custom_btn.connect("color-set", _on_custom)

        suffix_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        suffix_box.append(swatch_flow)
        suffix_box.append(self._custom_btn)
        color_row.add_suffix(suffix_box)
        grp.add(color_row)

        box.append(grp)
        btn = Gtk.Button(label="Save", margin_top=18)
        btn.add_css_class("suggested-action"); btn.add_css_class("pill")
        btn.connect("clicked", self._save)
        box.append(btn)
        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.LOCAL)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: (self._save(None), True)[1]),
        ))
        self.add_controller(sc)
        tv.set_content(box)
        self.set_content(tv)

    def _on_name_changed(self, entry, _):
        name = entry.get_text()
        cur_emoji = self._emoji.get_text()
        suggested = suggest_emoji(name) if name else "📁"
        # Only auto-update if emoji is empty or still looks like a default
        if not cur_emoji or cur_emoji in ("📁",):
            self._emoji.set_text(suggested)

    def _save(self, _):
        name = self._name.get_text().strip()
        if not name:
            return
        desc  = self._desc.get_text().strip() or None
        status = STATUSES[self._status.get_selected()]
        color  = self._selected_color
        emoji  = self._emoji.get_text().strip() or suggest_emoji(name)
        new_pid = None
        with get_db() as c:
            if self._project:
                c.execute(
                    "UPDATE project SET name=?,status=?,description=?,color=?,emoji=? WHERE id=?",
                    (name, status, desc, color, emoji, self._project["id"]),
                )
            else:
                cur = c.execute(
                    "INSERT INTO project (name,status,description,color,emoji) VALUES (?,?,?,?,?)",
                    (name, status, desc, color, emoji),
                )
                new_pid = cur.lastrowid
        if self._on_save:
            self._on_save(new_pid)
        self.close()


class NoteDialog(Adw.Window):
    def __init__(self, parent, pid, note=None, on_save=None):
        super().__init__(
            title="Edit Note" if note else "New Note",
            modal=True, transient_for=parent,
            default_width=540, default_height=480, resizable=True,
        )
        self._pid = pid; self._note = note; self._on_save = on_save
        tv = Adw.ToolbarView()
        hdr = Adw.HeaderBar()
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._save)
        hdr.pack_end(save_btn)
        expand_btn = Gtk.Button(icon_name="view-fullscreen-symbolic")
        expand_btn.add_css_class("flat")
        expand_btn.set_tooltip_text("Expand to full screen")
        self._normal_size = (540, 480)

        def _toggle_expand(_):
            if self.is_maximized():
                self.unmaximize()
                self.set_default_size(*self._normal_size)
                expand_btn.set_icon_name("view-fullscreen-symbolic")
                expand_btn.set_tooltip_text("Expand to full screen")
            else:
                self.maximize()
                expand_btn.set_icon_name("view-restore-symbolic")
                expand_btn.set_tooltip_text("Restore original size")

        expand_btn.connect("clicked", _toggle_expand)
        self.connect("notify::maximized", lambda w, _:
            expand_btn.set_icon_name(
                "view-restore-symbolic" if w.is_maximized() else "view-fullscreen-symbolic"))
        hdr.pack_end(expand_btn)
        tv.add_top_bar(hdr)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.add_css_class("card")
        self._text = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD,
                                  top_margin=10, bottom_margin=10,
                                  left_margin=10, right_margin=10)
        if note and note["content"]:
            self._text.get_buffer().set_text(note["content"])
        # Ctrl+Enter saves from the text area
        key_ctrl = Gtk.EventControllerKey.new()
        def _key_press(ctrl, keyval, keycode, state):
            if (keyval == 65293 and  # Enter
                    state & Gtk.accelerator_parse("<Control>Enter")[1]):
                self._save(None); return True
        key_ctrl.connect("key-pressed", _key_press)
        self._text.add_controller(key_ctrl)
        scroll.set_child(self._text)
        box.append(scroll)
        tags_grp = Adw.PreferencesGroup()
        self._tags_row = Adw.EntryRow(title="Labels")
        self._tags_row.set_text(safe_col(note, "tags") if note else "")
        self._tags_row.connect("entry-activated", self._save)
        tags_grp.add(self._tags_row)
        box.append(tags_grp)
        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.LOCAL)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: (self._save(None), True)[1]),
        ))
        self.add_controller(sc)
        tv.set_content(box); self.set_content(tv)

    def _save(self, _):
        buf = self._text.get_buffer()
        content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        tags = normalize_tag_input(self._tags_row.get_text())
        with get_db() as c:
            if self._note:
                c.execute("UPDATE note SET content=?, tags=? WHERE id=?",
                          (content, tags, self._note["id"]))
            else:
                if not content.strip(): return  # don't create blank notes
                c.execute("INSERT INTO note (project_id,content,tags,created_date) VALUES (?,?,?,?)",
                          (self._pid, content, tags, date.today().isoformat()))
        self.close()
        if self._on_save: self._on_save()


class GoalEditDialog(Adw.Window):
    def __init__(self, parent, pid, goal=None, on_save=None):
        super().__init__(
            title="Edit Goal" if goal else "New Goal",
            modal=True, transient_for=parent,
            default_width=460, default_height=720, resizable=True,
        )
        self._pid = pid; self._goal = goal; self._on_save = on_save
        self._cal_target = "end"
        self._guard = False

        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)

        fields = Adw.PreferencesGroup()

        self._name = Adw.EntryRow(title="Goal name")
        if goal: self._name.set_text(goal["text"])
        fields.add(self._name)

        self._notes_row = Adw.EntryRow(title="Notes")
        self._notes_row.set_text(safe_col(goal, "notes") if goal else "")
        fields.add(self._notes_row)

        self._tags_row = Adw.EntryRow(title="Labels")
        self._tags_row.set_text(safe_col(goal, "tags") if goal else "")
        fields.add(self._tags_row)

        pri_row = Adw.ActionRow(title="Priority")
        self._pri = Gtk.DropDown.new_from_strings(PRIORITIES)
        self._pri.set_valign(Gtk.Align.CENTER)
        cur_pri = safe_col(goal, "priority") if goal else "normal"
        self._pri.set_selected(PRIORITIES.index(cur_pri) if cur_pri in PRIORITIES else 0)
        pri_row.add_suffix(self._pri)
        fields.add(pri_row)

        box.append(fields)

        date_grp = Adw.PreferencesGroup(title="Dates")
        self._start = Adw.EntryRow(title="Start date  (+Nd / +Nw / +Nm)")
        self._start.set_text(safe_col(goal, "start_date") if goal else "")
        self._start.connect("notify::text", lambda e, _: self._entry_changed("start"))
        _wire_date_shortcut(self._start)
        date_grp.add(self._start)

        self._end = Adw.EntryRow(title="End date  (+Nd / +Nw / +Nm)")
        self._end.set_text(safe_col(goal, "end_date") if goal else "")
        self._end.connect("notify::text", lambda e, _: self._entry_changed("end"))
        _wire_date_shortcut(self._end)
        date_grp.add(self._end)
        box.append(date_grp)

        cal_label = Gtk.Label(label="Calendar sets:", xalign=0)
        cal_label.add_css_class("caption"); cal_label.add_css_class("dim-label")
        box.append(cal_label)

        radio_box = Gtk.Box(spacing=24)
        self._r_start = Gtk.CheckButton(label="Start date")
        self._r_end   = Gtk.CheckButton(label="End date", active=True)
        self._r_end.set_group(self._r_start)
        self._r_start.connect("toggled", self._on_radio)
        self._r_end.connect("toggled", self._on_radio)
        radio_box.append(self._r_start); radio_box.append(self._r_end)
        box.append(radio_box)

        self._cal = Gtk.Calendar()
        self._cal.add_css_class("card")
        _no_scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.HORIZONTAL)
        _no_scroll.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        _no_scroll.connect("scroll", lambda _c, _dx, _dy: True)
        self._cal.add_controller(_no_scroll)
        self._cal.connect("day-selected", self._on_day_selected)
        box.append(self._cal)

        for er in (self._name, self._notes_row, self._tags_row, self._start, self._end):
            er.connect("entry-activated", self._save)

        # ── Linked / inline note ───────────────────────────────────
        note_grp = Adw.PreferencesGroup(title="Note")
        note_grp.set_description("Write a note for this goal, or link an existing one")

        # Existing notes dropdown (all projects)
        with get_db() as _c:
            _all_notes = _c.execute(
                "SELECT n.id, n.content, n.project_id, p.name AS proj_name "
                "FROM note n JOIN project p ON n.project_id=p.id "
                "ORDER BY n.created_date DESC LIMIT 60"
            ).fetchall()
        _note_labels = ["— no linked note —"] + [
            f"{n['proj_name']}: {(n['content'] or '')[:40].replace(chr(10),' ')}"
            for n in _all_notes
        ]
        _note_ids = [None] + [n["id"] for n in _all_notes]
        link_row = Adw.ActionRow(title="Link existing note")
        self._note_drop = Gtk.DropDown.new_from_strings(_note_labels)
        self._note_drop.set_valign(Gtk.Align.CENTER)
        cur_linked = int(safe_col(goal, "linked_note_id") or 0) if goal else 0
        if cur_linked and cur_linked in _note_ids:
            self._note_drop.set_selected(_note_ids.index(cur_linked))
        self._note_ids = _note_ids
        link_row.add_suffix(self._note_drop)
        note_grp.add(link_row)

        # Inline note text area
        inline_lbl = Adw.ActionRow(title="Or write a new note")
        note_grp.add(inline_lbl)
        note_scroll = Gtk.ScrolledWindow()
        note_scroll.add_css_class("card")
        note_scroll.set_size_request(-1, 90)
        self._inline_note = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD,
                                         top_margin=8, bottom_margin=8,
                                         left_margin=8, right_margin=8)
        note_scroll.set_child(self._inline_note)
        box.append(note_grp)
        box.append(note_scroll)

        # ── Linked tasks (read-only) ──────────────────────────
        if goal:
            with get_db() as c:
                linked_tasks = c.execute(
                    "SELECT text, done, due_date, priority FROM todo WHERE goal_id=? ORDER BY done, due_date",
                    (safe_col(goal, "id"),)
                ).fetchall()
            if linked_tasks:
                tasks_grp = Adw.PreferencesGroup(title="Linked tasks")
                tasks_grp.set_description(f"{sum(1 for t in linked_tasks if not t['done'])} open · {sum(1 for t in linked_tasks if t['done'])} done")
                for lt in linked_tasks:
                    lt_row = Adw.ActionRow(title=lt["text"])
                    if lt["done"]:
                        lt_row.add_css_class("dim-label")
                        lt_row.set_title(f"<s>{GLib.markup_escape_text(lt['text'])}</s>")
                        try: lt_row.set_use_markup(True)
                        except AttributeError: pass
                    dd = lt["due_date"] or ""
                    if dd:
                        try:
                            delta = (datetime.strptime(dd, "%Y-%m-%d").date() - date.today()).days
                            dd_lbl = f"Due today" if delta == 0 else (f"Overdue {-delta}d" if delta < 0 else f"Due in {delta}d")
                        except ValueError:
                            dd_lbl = dd
                        lt_row.set_subtitle(dd_lbl)
                    check_icon = Gtk.Image(icon_name="object-select-symbolic" if lt["done"] else "radio-symbolic")
                    check_icon.set_valign(Gtk.Align.CENTER)
                    check_icon.add_css_class("success" if lt["done"] else "dim-label")
                    lt_row.add_prefix(check_icon)
                    tasks_grp.add(lt_row)
                box.append(tasks_grp)

        btn = Gtk.Button(label="Save")
        btn.add_css_class("suggested-action"); btn.add_css_class("pill")
        btn.connect("clicked", self._save)
        box.append(btn)

        if self._goal:
            conv_btn = Gtk.Button(label="Convert to task")
            conv_btn.add_css_class("flat")
            conv_btn.set_margin_top(4)
            conv_btn.connect("clicked", self._convert_to_task)
            box.append(conv_btn)

            del_btn = Gtk.Button(label="Delete goal")
            del_btn.add_css_class("destructive-action")
            del_btn.set_margin_top(4)
            del_btn.connect("clicked", self._delete_goal)
            box.append(del_btn)

        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.LOCAL)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: (self._save(None), True)[1]),
        ))
        self.add_controller(sc)
        scroll.set_child(box)
        tv.set_content(scroll)
        self.set_content(tv)

    def _cal_set(self, date_str):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            self._cal.select_day(GLib.DateTime.new_local(dt.year, dt.month, dt.day, 0, 0, 0.0))
        except Exception:
            pass

    def _on_radio(self, btn):
        if not btn.get_active(): return
        self._cal_target = "start" if btn is self._r_start else "end"
        val = self._start.get_text() if self._cal_target == "start" else self._end.get_text()
        self._guard = True; self._cal_set(val); self._guard = False

    def _on_day_selected(self, cal):
        if self._guard: return
        gdt = cal.get_date()
        ds = f"{gdt.get_year():04d}-{gdt.get_month():02d}-{gdt.get_day_of_month():02d}"
        self._guard = True
        (self._start if self._cal_target == "start" else self._end).set_text(ds)
        self._guard = False

    def _entry_changed(self, which):
        if self._guard: return
        if which != self._cal_target:
            # Auto-fill start_date from end_date when start is empty
            if which == "end" and not self._start.get_text().strip():
                self._guard = True
                self._start.set_text(self._end.get_text())
                self._guard = False
            return
        val = self._start.get_text() if which == "start" else self._end.get_text()
        self._guard = True; self._cal_set(val); self._guard = False

    def _save(self, *_):
        name = self._name.get_text().strip()
        if not name: return
        priority = PRIORITIES[self._pri.get_selected()]
        tags     = normalize_tag_input(self._tags_row.get_text())
        notes    = self._notes_row.get_text().strip()
        start    = expand_date_shortcut(self._start.get_text().strip()) or ""
        end      = expand_date_shortcut(self._end.get_text().strip()) or ""
        done_flag = 1 if (self._goal and self._goal["done"]) else 0
        gid_for_status = self._goal["id"] if self._goal else -1
        status   = compute_goal_status({"done": done_flag, "start_date": start,
                                        "end_date": end, "id": gid_for_status})
        done     = 1 if (done_flag or status == "done") else 0
        due_date = end
        linked_note = self._note_ids[self._note_drop.get_selected()]

        # Save inline note to the project's Notes section (independent of linked_note)
        buf = self._inline_note.get_buffer()
        inline_text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()

        with get_db() as c:
            if inline_text:
                c.execute(
                    "INSERT INTO note (project_id,content,tags,created_date) VALUES (?,?,?,?)",
                    (self._pid, inline_text, "", date.today().isoformat())
                )

            if self._goal:
                c.execute(
                    "UPDATE goal SET text=?,status=?,priority=?,tags=?,notes=?,"
                    "start_date=?,end_date=?,done=?,due_date=?,linked_note_id=? WHERE id=?",
                    (name, status, priority, tags, notes, start, end, done, due_date,
                     linked_note, self._goal["id"])
                )
            else:
                c.execute(
                    "INSERT INTO goal (project_id,text,status,priority,tags,notes,"
                    "start_date,end_date,done,due_date,linked_note_id)"
                    " VALUES (?,?,?,?,?,?,?,?,0,?,?)",
                    (self._pid, name, status, priority, tags, notes, start, end,
                     due_date, linked_note)
                )
        if self._on_save: self._on_save()
        self.close()

    def _convert_to_task(self, _):
        if not self._goal: return
        g = self._goal
        with get_db() as c:
            new_pos = c.execute(
                "SELECT COALESCE(MAX(order_pos)+1,0) FROM todo WHERE project_id=? AND done=0",
                (self._pid,)).fetchone()[0]
            c.execute(
                "INSERT INTO todo (project_id,text,priority,tags,order_pos,due_date,done)"
                " VALUES (?,?,?,?,?,?,?)",
                (self._pid, safe_col(g,"text") or "", safe_col(g,"priority") or "normal",
                 safe_col(g,"tags") or "", new_pos, safe_col(g,"end_date") or "", 1 if g["done"] else 0)
            )
            c.execute("DELETE FROM goal WHERE id=?", (g["id"],))
        if self._on_save: self._on_save()
        self.close()

    def _delete_goal(self, _):
        if not self._goal: return
        def _do():
            with get_db() as c:
                c.execute("DELETE FROM goal WHERE id=?", (self._goal["id"],))
            if self._on_save: self._on_save()
            self.close()
        _confirm_delete(self, "Delete goal?",
                        "\"" + safe_col(self._goal, "text") + "\" will be permanently removed.", _do)


class FileEditDialog(Adw.Window):
    def __init__(self, parent, file_row, on_save=None):
        super().__init__(title="Edit File", modal=True, transient_for=parent,
                         default_width=420, default_height=280, resizable=True)
        self._file = file_row; self._on_save = on_save
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)
        grp = Adw.PreferencesGroup()
        self._name = Adw.EntryRow(title="Display name")
        self._name.set_text(file_row["name"])
        grp.add(self._name)
        self._tags = Adw.EntryRow(title="Labels")
        self._tags.set_text(safe_col(file_row, "tags"))
        grp.add(self._tags)
        for er in (self._name, self._tags):
            er.connect("entry-activated", self._save)
        box.append(grp)
        btn = Gtk.Button(label="Save", margin_top=18)
        btn.add_css_class("suggested-action"); btn.add_css_class("pill")
        btn.connect("clicked", self._save)
        box.append(btn)
        tv.set_content(box); self.set_content(tv)

    def _save(self, _):
        name = self._name.get_text().strip() or self._file["name"]
        tags = normalize_tag_input(self._tags.get_text())
        with get_db() as c:
            c.execute("UPDATE file SET name=?, tags=? WHERE id=?",
                      (name, tags, self._file["id"]))
        if self._on_save: self._on_save()
        self.close()


class QuickTaskDialog(Adw.Window):
    """Compact task-add dialog accessible from the home overview."""
    def __init__(self, parent, pid, project_name, on_save=None, goal_id=None, goal_name=None):
        super().__init__(
            title=f"Quick task — {project_name}",
            modal=True, transient_for=parent,
            default_width=400, resizable=False,
        )
        self._pid = pid; self._on_save = on_save; self._goal_id = goal_id
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)
        grp = Adw.PreferencesGroup()
        if goal_name:
            grp.set_description(f"Will be linked to goal: {goal_name}")
        self._entry = Adw.EntryRow(title="Task  (type #tag to label, press Enter)")
        self._entry.connect("entry-activated", self._save)
        grp.add(self._entry)
        pri_row = Adw.ActionRow(title="Priority")
        self._pri = Gtk.DropDown.new_from_strings(PRIORITIES)
        self._pri.set_valign(Gtk.Align.CENTER)
        pri_row.add_suffix(self._pri)
        grp.add(pri_row)
        self._entry_due = Adw.EntryRow(title="Due date (e.g. monday, june 5, +7d)")
        _wire_date_shortcut(self._entry_due)
        grp.add(self._entry_due)
        box.append(grp)
        btn = Gtk.Button(label="Add task", margin_top=18)
        btn.add_css_class("suggested-action"); btn.add_css_class("pill")
        btn.connect("clicked", self._save)
        box.append(btn)
        tv.set_content(box); self.set_content(tv)
        GLib.idle_add(self._entry.grab_focus)

    def _save(self, *_):
        raw = self._entry.get_text().strip()
        if not raw: return
        text, tags = parse_tags_from_text(raw)
        priority = PRIORITIES[self._pri.get_selected()]
        due_date = parse_natural_date(self._entry_due.get_text().strip()) or None
        with get_db() as c:
            new_pos = (c.execute(
                "SELECT COALESCE(MAX(order_pos)+1,0) FROM todo WHERE project_id=? AND done=0",
                (self._pid,)).fetchone()[0])
            c.execute(
                "INSERT INTO todo (project_id,text,priority,tags,order_pos,due_date,goal_id) VALUES (?,?,?,?,?,?,?)",
                (self._pid, text, priority, tags, new_pos, due_date, self._goal_id),
            )
        if self._on_save: self._on_save()
        self.close()


class TodoEditDialog(Adw.Window):
    def __init__(self, parent, todo, on_save=None):
        super().__init__(
            title="New Task" if "id" not in todo else "Edit Task",
            modal=True, transient_for=parent,
            default_width=420, default_height=580, resizable=True,
        )
        self._todo = todo
        self._on_save = on_save

        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)

        grp = Adw.PreferencesGroup()

        self._text = Adw.EntryRow(title="Task")
        self._text.set_text(safe_col(todo, "text") or "")
        grp.add(self._text)

        self._tags = Adw.EntryRow(title="Labels (e.g. #design #urgent)")
        self._tags.set_text(safe_col(todo, "tags"))
        grp.add(self._tags)

        pri_row = Adw.ActionRow(title="Priority")
        self._pri = Gtk.DropDown.new_from_strings(PRIORITIES)
        self._pri.set_valign(Gtk.Align.CENTER)
        cur = safe_col(todo, "priority") or "normal"
        cur = cur if cur in PRIORITIES else "normal"
        self._pri.set_selected(PRIORITIES.index(cur))
        pri_row.add_suffix(self._pri)
        grp.add(pri_row)

        recur_row = Adw.ActionRow(title="Repeat")
        self._recur_drop = Gtk.DropDown.new_from_strings(RECUR_OPTIONS)
        self._recur_drop.set_valign(Gtk.Align.CENTER)
        # Set current value
        cur_recur = int(safe_col(todo, "recur_days") or 0)
        sel = 0
        for i, d in enumerate(RECUR_DAYS):
            if d == cur_recur:
                sel = i; break
            if d > cur_recur and i > 0:  # pick closest
                sel = i - 1; break
        self._recur_drop.set_selected(sel)
        recur_row.add_suffix(self._recur_drop)
        grp.add(recur_row)

        self._recur_end = Adw.EntryRow(title="Stop repeating after (date, optional)")
        self._recur_end.set_text(safe_col(todo, "recur_end_date") or "")
        _wire_date_shortcut(self._recur_end)
        grp.add(self._recur_end)

        # Goal assignment
        with get_db() as c:
            _goals = c.execute(
                "SELECT id, text FROM goal WHERE project_id=? AND done=0 ORDER BY id",
                (todo["project_id"],)
            ).fetchall()
        _goal_labels = ["— none —"] + [g["text"] for g in _goals]
        _goal_ids    = [None] + [g["id"] for g in _goals]
        goal_row = Adw.ActionRow(title="Assign to goal", subtitle="Optional — groups this task under a goal")
        self._goal_drop = Gtk.DropDown.new_from_strings(_goal_labels)
        self._goal_drop.set_valign(Gtk.Align.CENTER)
        cur_goal = safe_col(todo, "goal_id")
        if cur_goal and int(cur_goal or 0) in _goal_ids:
            self._goal_drop.set_selected(_goal_ids.index(int(cur_goal)))
        self._goal_ids = _goal_ids
        goal_row.add_suffix(self._goal_drop)
        grp.add(goal_row)

        for er in (self._text, self._tags):
            er.connect("entry-activated", self._save)

        # ── Due date group with calendar ──────────────────────
        due_grp = Adw.PreferencesGroup(title="Due date")
        self._due = Adw.EntryRow(title="Date (e.g. monday, june 5, +7d, or YYYY-MM-DD)")
        self._due.set_text(safe_col(todo, "due_date") or "")
        _wire_date_shortcut(self._due)
        due_grp.add(self._due)

        self._due_cal = Gtk.Calendar()
        self._due_cal.add_css_class("card")
        _cal_guard = [False]
        _no_scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.HORIZONTAL)
        _no_scroll.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        _no_scroll.connect("scroll", lambda _c, _dx, _dy: True)
        self._due_cal.add_controller(_no_scroll)

        def _cal_set_due(date_str):
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                _cal_guard[0] = True
                self._due_cal.select_day(GLib.DateTime.new_local(dt.year, dt.month, dt.day, 0, 0, 0.0))
                _cal_guard[0] = False
            except Exception:
                pass

        def _on_due_cal(cal):
            if _cal_guard[0]: return
            gdt = cal.get_date()
            ds = f"{gdt.get_year():04d}-{gdt.get_month():02d}-{gdt.get_day_of_month():02d}"
            _cal_guard[0] = True
            self._due.set_text(ds)
            _cal_guard[0] = False

        def _on_due_text_changed(*_):
            if _cal_guard[0]: return
            val = parse_natural_date(self._due.get_text().strip())
            _cal_set_due(val)

        self._due_cal.connect("day-selected", _on_due_cal)
        self._due.connect("notify::text", _on_due_text_changed)
        if safe_col(todo, "due_date"):
            _cal_set_due(safe_col(todo, "due_date"))

        # ── Stop repeating calendar ───────────────────────────
        recur_end_grp = Adw.PreferencesGroup(title="Stop repeating after")
        recur_end_grp.set_description("Optional — leave blank to repeat forever")
        recur_end_grp.add(self._recur_end)

        self._recur_end_cal = Gtk.Calendar()
        self._recur_end_cal.add_css_class("card")
        _rcal_guard = [False]
        _no_scroll2 = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.HORIZONTAL)
        _no_scroll2.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        _no_scroll2.connect("scroll", lambda _c, _dx, _dy: True)
        self._recur_end_cal.add_controller(_no_scroll2)

        def _rcal_set(date_str):
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                _rcal_guard[0] = True
                self._recur_end_cal.select_day(GLib.DateTime.new_local(dt.year, dt.month, dt.day, 0, 0, 0.0))
                _rcal_guard[0] = False
            except Exception:
                pass

        def _on_rcal(cal):
            if _rcal_guard[0]: return
            gdt = cal.get_date()
            ds = f"{gdt.get_year():04d}-{gdt.get_month():02d}-{gdt.get_day_of_month():02d}"
            _rcal_guard[0] = True
            self._recur_end.set_text(ds)
            _rcal_guard[0] = False

        def _on_recur_end_text(*_):
            if _rcal_guard[0]: return
            _rcal_set(parse_natural_date(self._recur_end.get_text().strip()) or "")

        self._recur_end_cal.connect("day-selected", _on_rcal)
        self._recur_end.connect("notify::text", _on_recur_end_text)
        if safe_col(todo, "recur_end_date"):
            _rcal_set(safe_col(todo, "recur_end_date"))

        box.append(grp)
        box.append(due_grp)
        box.append(self._due_cal)
        box.append(recur_end_grp)
        box.append(self._recur_end_cal)
        btn = Gtk.Button(label="Save", margin_top=6)
        btn.add_css_class("suggested-action"); btn.add_css_class("pill")
        btn.connect("clicked", self._save)
        box.append(btn)

        if "id" in self._todo:
            conv_btn = Gtk.Button(label="Convert to goal")
            conv_btn.add_css_class("flat")
            conv_btn.set_margin_top(4)
            conv_btn.connect("clicked", self._convert_to_goal)
            box.append(conv_btn)

            del_btn = Gtk.Button(label="Delete task")
            del_btn.add_css_class("destructive-action")
            del_btn.set_margin_top(4)
            del_btn.connect("clicked", self._delete_task)
            box.append(del_btn)

        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.LOCAL)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: (self._save(None), True)[1]),
        ))
        self.add_controller(sc)
        scroll.set_child(box)
        tv.set_content(scroll)
        self.set_content(tv)

    def _save(self, _):
        text = self._text.get_text().strip()
        if not text:
            return
        tags       = normalize_tag_input(self._tags.get_text())
        priority   = PRIORITIES[self._pri.get_selected()]
        recur_days = RECUR_DAYS[self._recur_drop.get_selected()]
        recur_end_date = parse_natural_date(self._recur_end.get_text().strip()) if self._recur_end.get_text().strip() else ""
        due_date   = parse_natural_date(self._due.get_text().strip()) or None
        goal_id = self._goal_ids[self._goal_drop.get_selected()]
        with get_db() as c:
            if "id" in self._todo:
                c.execute(
                    "UPDATE todo SET text=?, tags=?, priority=?, recur_days=?, recur_end_date=?, due_date=?, goal_id=? WHERE id=?",
                    (text, tags, priority, recur_days, recur_end_date, due_date, goal_id, self._todo["id"]),
                )
            else:
                new_pos = c.execute(
                    "SELECT COALESCE(MAX(order_pos)+1,0) FROM todo WHERE project_id=? AND done=0",
                    (self._todo["project_id"],)).fetchone()[0]
                c.execute(
                    "INSERT INTO todo (project_id,text,priority,tags,order_pos,recur_days,recur_end_date,due_date,goal_id)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (self._todo["project_id"], text, priority, tags, new_pos, recur_days, recur_end_date, due_date, goal_id),
                )
        if self._on_save:
            self._on_save()
        self.close()

    def _convert_to_goal(self, _):
        t = self._todo
        with get_db() as c:
            c.execute(
                "INSERT INTO goal (project_id,text,priority,tags,end_date,done,status)"
                " VALUES (?,?,?,?,?,?,?)",
                (t["project_id"], safe_col(t,"text") or "", safe_col(t,"priority") or "normal",
                 safe_col(t,"tags") or "", safe_col(t,"due_date") or "",
                 1 if t["done"] else 0, "done" if t["done"] else "active")
            )
            c.execute("DELETE FROM todo WHERE id=?", (t["id"],))
        if self._on_save: self._on_save()
        self.close()

    def _delete_task(self, _):
        def _do():
            with get_db() as c:
                c.execute("DELETE FROM todo WHERE id=?", (self._todo["id"],))
            if self._on_save: self._on_save()
            self.close()
        _confirm_delete(self, "Delete task?",
                        "\"" + safe_col(self._todo, "text") + "\" will be permanently removed.", _do)


class ChangelogDialog(Adw.Window):
    def __init__(self, parent):
        super().__init__(title="Changelog", modal=True, transient_for=parent,
                         default_width=520, default_height=540)
        try:
            with open(_CHANGELOG) as f:
                text = f.read()
        except FileNotFoundError:
            text = "CHANGELOG.md not found."
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        scroll = Gtk.ScrolledWindow(vexpand=True,
                                    margin_top=12, margin_bottom=12,
                                    margin_start=18, margin_end=18)
        label = Gtk.Label(label=text, xalign=0, yalign=0, wrap=True, selectable=False)
        label.add_css_class("monospace")
        scroll.set_child(label)
        tv.set_content(scroll)
        self.set_content(tv)


# ══════════════════════════════════════════════════════
# Section views
# ══════════════════════════════════════════════════════

class TodosView(Gtk.Box):
    def __init__(self, pid, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=12, margin_start=18, margin_end=18)
        self._pid = pid; self._win = win
        self._bulk_mode    = False
        self._selected_ids = set()
        self._row_checks   = {}
        self._filter_tags  = set()
        self._drag_rows    = {}
        self._sort_by      = "order" # options: "order", "alpha", "priority", "due", "overdue"

        tb = tip_banner("tasks",
            "Type #tag in a task name to label it. Use Select for bulk actions. "
            "Drag the ⠿ handle to reorder. Click any tag chip above to filter.")
        if tb: self.append(tb)

        # ── "Pick for me" banner ──────────────────────────────
        self._pick_rev = Gtk.Revealer(reveal_child=False)
        self._pick_rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        pick_box = Gtk.Box(spacing=8, margin_start=4, margin_end=4,
                           margin_top=4, margin_bottom=4)
        pick_box.add_css_class("card")
        dice_img = Gtk.Image(icon_name="media-playlist-shuffle-symbolic")
        dice_img.add_css_class("accent"); pick_box.append(dice_img)
        self._pick_lbl = Gtk.Label(xalign=0, hexpand=True)
        self._pick_lbl.add_css_class("accent")
        pick_box.append(self._pick_lbl)
        dismiss_btn = Gtk.Button(icon_name="window-close-symbolic")
        dismiss_btn.add_css_class("flat")
        dismiss_btn.connect("clicked", lambda _: self._pick_rev.set_reveal_child(False))
        pick_box.append(dismiss_btn)
        self._pick_rev.set_child(pick_box)
        self.append(self._pick_rev)

        # ── Due-date calendar + add button ────────────────────
        cal_hdr = Gtk.Box(spacing=8, margin_bottom=4)
        add_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add task (Ctrl+N)")
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("circular")
        add_btn.set_valign(Gtk.Align.CENTER)
        add_btn.connect("clicked", lambda _: self._new_task_dialog())
        cal_title = Gtk.Label(label="Due dates", xalign=0, hexpand=True)
        cal_title.add_css_class("heading")
        cal_hdr.append(cal_title)
        cal_hdr.append(add_btn)
        self.append(cal_hdr)

        self._due_cal = Gtk.Calendar()
        self._due_cal.add_css_class("card")
        # Block scroll from accidentally changing the month
        _no_sc = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.HORIZONTAL)
        _no_sc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        _no_sc.connect("scroll", lambda _c, _dx, _dy: True)
        self._due_cal.add_controller(_no_sc)
        self._due_cal.connect("next-month", lambda _: self._mark_due_days())
        self._due_cal.connect("prev-month", lambda _: self._mark_due_days())
        self._due_cal.connect("next-year",  lambda _: self._mark_due_days())
        self._due_cal.connect("prev-year",  lambda _: self._mark_due_days())
        self.append(self._due_cal)

        # ── Tag filter chips (rebuilt each time) ─────────────
        self._chips_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                  spacing=6, margin_start=2, margin_end=2)
        self._chips_bar.set_wrap_policy if hasattr(Gtk.Box, "set_wrap_policy") else None
        self.append(self._chips_bar)

        # ── Rebuilt list below ────────────────────────────────
        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.append(self._content)

        # ── Bulk action bar (hidden until bulk mode + selection) ──
        self._bulk_bar_rev = Gtk.Revealer(reveal_child=False)
        bulk_bar = Gtk.Box(spacing=8, margin_start=4, margin_end=4,
                           margin_top=6, margin_bottom=6)
        self._done_btn = Gtk.Button(label="Mark done")
        self._done_btn.add_css_class("suggested-action")
        self._done_btn.connect("clicked", self._bulk_done)
        self._del_btn = Gtk.Button(label="Delete")
        self._del_btn.add_css_class("destructive-action")
        self._del_btn.connect("clicked", self._bulk_delete)
        self._move_btn = Gtk.Button(label="Move to…")
        self._move_btn.add_css_class("flat")
        self._move_btn.connect("clicked", self._bulk_move)
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.add_css_class("flat")
        cancel_btn.connect("clicked", lambda _: self._exit_bulk_mode())
        bulk_bar.append(self._done_btn); bulk_bar.append(self._del_btn)
        bulk_bar.append(self._move_btn)
        bulk_bar.append(Gtk.Box(hexpand=True)); bulk_bar.append(cancel_btn)
        self._bulk_bar_rev.set_child(bulk_bar)
        self.append(self._bulk_bar_rev)

        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.MANAGED)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_n, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: self._new_task_dialog() or True),
        ))
        self.add_controller(sc)

        self._build_content()

    def _new_task_dialog(self):
        TodoEditDialog(self._win, {"text": "", "priority": "normal", "project_id": self._pid},
                       on_save=self._build_content).present()

    def _mark_due_days(self):
        self._due_cal.clear_marks()
        gdt = self._due_cal.get_date()
        yr, mo = gdt.get_year(), gdt.get_month()
        with get_db() as c:
            rows = c.execute(
                "SELECT due_date FROM todo WHERE project_id=? AND done=0 AND due_date!=''",
                (self._pid,)
            ).fetchall()
        for row in rows:
            try:
                d = datetime.strptime(row["due_date"], "%Y-%m-%d").date()
                if d.year == yr and d.month == mo:
                    self._due_cal.mark_day(d.day)
            except ValueError:
                pass

    # ── Build ──────────────────────────────────────────────────

    def _on_tag_filter(self, tag, active):
        if active:
            self._filter_tags.add(tag)
        else:
            self._filter_tags.discard(tag)
        GLib.idle_add(self._build_content)

    def _on_sort_changed(self):
        self._sort_by = self._sort_keys[self._sort_drop.get_selected()]
        GLib.idle_add(self._build_content)

    def _build_content(self):
        clear_box(self._content)
        self._row_checks.clear()
        self._drag_rows = {}
        todos  = db_todos(self._pid)
        undone = [t for t in todos if not t["done"]]
        done   = [t for t in todos if t["done"]]

        # ── Sort undone tasks ──────────────────────────────────
        today_iso = date.today().isoformat()
        if self._sort_by == "alpha":
            undone.sort(key=lambda t: t["text"].lower())
        elif self._sort_by == "priority":
            _pri_order = {"high": 0, "normal": 1, "low": 2}
            undone.sort(key=lambda t: _pri_order.get(safe_col(t, "priority") or "normal", 1))
        elif self._sort_by == "due":
            undone.sort(key=lambda t: safe_col(t, "due_date") or "9999-99-99")
        elif self._sort_by == "overdue":
            def _overdue_key(t):
                dd = safe_col(t, "due_date")
                if dd and dd < today_iso:
                    return (0, dd)
                return (1, dd or "9999-99-99")
            undone.sort(key=_overdue_key)
        # else: keep DB order (order_pos)

        # ── Rebuild tag chips ──────────────────────────────────
        clear_box(self._chips_bar)
        all_tags = sorted({tag for t in todos for tag in get_tags(safe_col(t, "tags"))})
        _building = [True]
        for tag in all_tags:
            chip = Gtk.ToggleButton(label=f"#{tag}")
            chip.add_css_class("pill"); chip.add_css_class("flat")
            chip.set_active(tag in self._filter_tags)
            def _on_chip_toggled(btn, tg=tag):
                if _building[0]:
                    return
                if btn.get_active():
                    self._filter_tags.add(tg)
                else:
                    self._filter_tags.discard(tg)
                GLib.idle_add(self._build_content)
            chip.connect("toggled", _on_chip_toggled)
            self._chips_bar.append(chip)
        if self._filter_tags:
            clear_chip = Gtk.Button(label="✕ Clear")
            clear_chip.add_css_class("pill"); clear_chip.add_css_class("flat")
            clear_chip.add_css_class("error")
            clear_chip.connect("clicked", lambda _: (self._filter_tags.clear(), GLib.idle_add(self._build_content)))
            self._chips_bar.append(clear_chip)
        _building[0] = False
        self._chips_bar.set_visible(bool(all_tags))

        # ── Apply active tag filter ────────────────────────────
        if self._filter_tags:
            undone = [t for t in undone if any(
                tag in get_tags(safe_col(t, "tags")) for tag in self._filter_tags
            )]
            done = [t for t in done if any(
                tag in get_tags(safe_col(t, "tags")) for tag in self._filter_tags
            )]

        active_grp = Adw.PreferencesGroup(title="Tasks")

        # ── Sort bar ───────────────────────────────────────────
        sort_bar = Gtk.Box(spacing=6, margin_top=4, margin_bottom=2)
        sort_lbl = Gtk.Label(label="Sort:")
        sort_lbl.add_css_class("caption"); sort_lbl.add_css_class("dim-label")
        sort_bar.append(sort_lbl)
        SORT_OPTS = [("order", "Default"), ("alpha", "A-Z"), ("priority", "Priority"),
                     ("due", "Due date"), ("overdue", "Overdue first")]
        self._sort_drop = Gtk.DropDown.new_from_strings([label for _, label in SORT_OPTS])
        self._sort_keys = [key for key, _ in SORT_OPTS]
        self._sort_drop.set_valign(Gtk.Align.CENTER)
        cur_sort_idx = self._sort_keys.index(self._sort_by) if self._sort_by in self._sort_keys else 0
        self._sort_drop.set_selected(cur_sort_idx)
        self._sort_drop.connect("notify::selected", lambda d, _: self._on_sort_changed())
        sort_bar.append(self._sort_drop)
        self._content.append(sort_bar)

        # Header suffix buttons: pick + bulk select
        hdr_box = Gtk.Box(spacing=4)
        pick_btn = Gtk.Button(icon_name="media-playlist-shuffle-symbolic")
        pick_btn.add_css_class("flat"); pick_btn.set_tooltip_text("Pick a task for me")
        pick_btn.connect("clicked", self._pick_random)
        hdr_box.append(pick_btn)
        self._bulk_select_btn = Gtk.ToggleButton(label="Select")
        self._bulk_select_btn.add_css_class("flat")
        self._bulk_select_btn.set_active(self._bulk_mode)
        self._bulk_select_btn.connect("toggled", self._on_bulk_toggle)
        hdr_box.append(self._bulk_select_btn)
        active_grp.set_header_suffix(hdr_box)

        if not todos:
            active_grp.add(Adw.ActionRow(title="No tasks yet"))
        for t in undone:
            active_grp.add(self._make_row(t, is_done=False))
        self._content.append(active_grp)

        if done:
            n = len(done)
            toggle_state = [False]
            toggle_btn = Gtk.Button()
            toggle_btn.add_css_class("flat")
            lbl = Gtk.Label()
            lbl.set_markup(f"<small>▶  {n} completed task{'s' if n != 1 else ''}</small>")
            lbl.add_css_class("dim-label")
            toggle_btn.set_child(lbl)
            toggle_btn.set_halign(Gtk.Align.START)
            toggle_btn.set_margin_top(6)
            self._content.append(toggle_btn)

            done_rev = Gtk.Revealer(reveal_child=False)
            done_grp = Adw.PreferencesGroup()
            for t in done:
                done_grp.add(self._make_row(t, is_done=True))
            done_rev.set_child(done_grp)
            self._content.append(done_rev)

            def on_toggle(_btn, _lbl=lbl, _rev=done_rev, _state=toggle_state, _n=n):
                _state[0] = not _state[0]
                _rev.set_reveal_child(_state[0])
                arrow = "▼" if _state[0] else "▶"
                _lbl.set_markup(f"<small>{arrow}  {_n} completed task{'s' if _n != 1 else ''}</small>")

            toggle_btn.connect("clicked", on_toggle)

        self._mark_due_days()

    def _make_row(self, t, is_done):
        row = Adw.ActionRow()
        tid = t["id"]
        self._drag_rows[tid] = row

        # ── Bulk selection checkbox (bulk mode, active tasks only) ──
        if not is_done and self._bulk_mode:
            sel_cb = Gtk.CheckButton(active=(tid in self._selected_ids))
            sel_cb.set_valign(Gtk.Align.CENTER)
            sel_cb.connect("toggled", lambda c, i=tid: self._on_select(i, c.get_active()))
            row.add_prefix(sel_cb)
            self._row_checks[tid] = sel_cb

        # ── Drag handle (active tasks only, non-bulk) ──────────
        if not is_done and not self._bulk_mode:
            handle = Gtk.Image(icon_name="format-justify-fill-symbolic")
            handle.set_valign(Gtk.Align.CENTER)
            handle.add_css_class("dim-label")
            try:
                handle.set_cursor(Gdk.Cursor.new_from_name("grab", None))
            except Exception:
                pass

            drag = Gtk.DragSource.new()
            drag.set_actions(Gdk.DragAction.MOVE)
            drag.connect("prepare", lambda src, x, y, i=tid:
                Gdk.ContentProvider.new_for_value(str(i)))
            drag.connect("drag-begin", lambda src, data, r=row: src.set_icon(
                Gtk.WidgetPaintable.new(r), 0, 0))
            handle.add_controller(drag)
            row.add_prefix(handle)

            drop = Gtk.DropTarget.new(str, Gdk.DragAction.MOVE)

            def _on_drag_motion(tgt, x, y, hov_tid=tid):
                if getattr(self, '_drag_hover_tid', None) != hov_tid:
                    prev = getattr(self, '_drag_hover_tid', None)
                    if prev and prev in self._drag_rows:
                        self._drag_rows[prev].remove_css_class("drag-target-row")
                    self._drag_hover_tid = hov_tid
                    row.add_css_class("drag-target-row")
                return Gdk.DragAction.MOVE

            def _on_drag_leave(tgt, hov_tid=tid):
                if getattr(self, '_drag_hover_tid', None) == hov_tid:
                    row.remove_css_class("drag-target-row")
                    self._drag_hover_tid = None

            drop.connect("motion", _on_drag_motion)
            drop.connect("leave", _on_drag_leave)
            drop.connect("drop", lambda tgt, val, x, y, i=tid: (
                self._drag_rows.get(i, None) and self._drag_rows[i].remove_css_class("drag-target-row"),
                setattr(self, '_drag_hover_tid', None),
                self._reorder_todo(int(val), i),
                True
            )[-1])
            row.add_controller(drop)

        # ── Title (strikethrough when done) ───────────────────
        escaped = GLib.markup_escape_text(t["text"])
        row.set_use_markup(True)
        if is_done:
            row.set_title(f"<s>{escaped}</s>")
            row.add_css_class("dim-label")
        else:
            row.set_title(escaped)

        # ── Tags + recur + due date in subtitle ───────────────
        tags = get_tags(safe_col(t, "tags"))
        tags_str = "  ".join(f"#{GLib.markup_escape_text(tag)}" for tag in tags) if tags else ""
        recur = int(safe_col(t, "recur_days") or 0)
        due_str = safe_col(t, "due_date")
        due_part = ""
        if due_str and not is_done:
            try:
                due_d = datetime.strptime(due_str, "%Y-%m-%d").date()
                delta = (due_d - date.today()).days
                if delta < 0:
                    due_part = f"Overdue by {-delta}d"
                elif delta == 0:
                    due_part = "Due today"
                elif delta <= 3:
                    due_part = f"Due in {delta}d"
                else:
                    due_part = f"Due {due_d.strftime('%a %-d %b')}"
            except ValueError:
                due_part = f"Due {due_str}"
        sub_parts = []
        if due_part:
            if due_part == "Due today":
                sub_parts.append('<b><span foreground="#e01b24">Due today</span></b>')
                row.add_css_class("task-row-high")
            else:
                sub_parts.append(f"<i>{GLib.markup_escape_text(due_part)}</i>")
        if recur and not is_done:
            sub_parts.append(f"Repeats every {recur}d")
        if tags_str:
            sub_parts.append(tags_str)
        if sub_parts:
            row.set_subtitle("  ·  ".join(sub_parts))
        if due_str and not is_done:
            try:
                due_d = datetime.strptime(due_str, "%Y-%m-%d").date()
                if due_d < date.today():
                    row.add_css_class("task-row-high")
            except ValueError:
                pass

        # ── Priority indicator bar (left edge, active only) ───
        if not is_done:
            pri = t["priority"] or "normal"
            if pri == "high":
                row.add_css_class("task-row-high")
            if pri in ("high", "low"):
                bar = Gtk.Box()
                bar.set_size_request(4, -1)
                bar.set_valign(Gtk.Align.FILL)
                bar.add_css_class("priority-bar")
                bar.add_css_class(f"priority-{pri}")
                row.add_prefix(bar)

        # ── Checkbox ──────────────────────────────────────────
        check = Gtk.CheckButton(active=is_done)
        check.set_valign(Gtk.Align.CENTER)
        check.connect("toggled", lambda _b, i=tid: self._toggle(i))
        row.add_prefix(check)

        # ── Suffix: priority drop (active), edit, delete ──────
        if not is_done:
            pri_drop = Gtk.DropDown.new_from_strings(PRIORITIES)
            pri_drop.set_valign(Gtk.Align.CENTER)
            pri_drop.set_tooltip_text("Priority")
            cur = t["priority"] if t["priority"] in PRIORITIES else "normal"
            pri_drop.set_selected(PRIORITIES.index(cur))
            pri_drop.connect("notify::selected",
                lambda d, _p, i=tid: self._update_priority(i, PRIORITIES[d.get_selected()]))
            row.add_suffix(pri_drop)

        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.add_css_class("flat"); edit_btn.set_valign(Gtk.Align.CENTER)
        edit_btn.set_tooltip_text("Edit task (or double-click row)")
        td_snap = dict(t)
        edit_btn.connect("clicked",
            lambda _, td=td_snap: TodoEditDialog(self._win, td, on_save=self._build_content).present())
        add_dblclick(row, lambda td=td_snap: TodoEditDialog(self._win, td, on_save=self._build_content).present())
        row.add_suffix(edit_btn)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat"); del_btn.add_css_class("destructive-action")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.connect("clicked", lambda _, i=tid: self._delete(i))
        row.add_suffix(del_btn)

        return row

    # ── Actions ────────────────────────────────────────────────

    def _reorder_todo(self, drag_id, drop_id):
        if drag_id == drop_id:
            return
        undone_ids = [
            t["id"] for t in db_todos(self._pid) if not t["done"]
        ]
        if drag_id not in undone_ids or drop_id not in undone_ids:
            return
        undone_ids.remove(drag_id)
        pos = undone_ids.index(drop_id)
        undone_ids.insert(pos, drag_id)
        with get_db() as c:
            for new_pos, tid in enumerate(undone_ids):
                c.execute("UPDATE todo SET order_pos=? WHERE id=?", (new_pos, tid))
        GLib.idle_add(self._build_content)

    def _pick_random(self, _):
        undone = [t for t in db_todos(self._pid) if not t["done"]]
        if not undone:
            return
        task = random.choice(undone)
        self._pick_lbl.set_text(f"Focus on: {task['text']}")
        self._pick_rev.set_reveal_child(True)

    def _on_bulk_toggle(self, btn):
        self._bulk_mode = btn.get_active()
        if not self._bulk_mode:
            self._selected_ids.clear()
            self._bulk_bar_rev.set_reveal_child(False)
        GLib.idle_add(self._build_content)

    def _on_select(self, tid, selected):
        if selected:
            self._selected_ids.add(tid)
        else:
            self._selected_ids.discard(tid)
        n = len(self._selected_ids)
        self._bulk_bar_rev.set_reveal_child(n > 0)
        self._done_btn.set_label(f"Mark done ({n})" if n else "Mark done")
        self._del_btn.set_label(f"Delete ({n})" if n else "Delete")
        self._move_btn.set_label(f"Move to… ({n})" if n else "Move to…")

    def _bulk_move(self, btn):
        if not self._selected_ids:
            return
        other = [p for p in db_projects() if p["id"] != self._pid]
        if not other:
            return
        popover = Gtk.Popover()
        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                          margin_top=8, margin_bottom=8, margin_start=8, margin_end=8)
        hdr = Gtk.Label(label="Move tasks to:", xalign=0)
        hdr.add_css_class("caption"); hdr.add_css_class("dim-label")
        pop_box.append(hdr)
        lb = Gtk.ListBox(); lb.add_css_class("boxed-list")
        for p in other:
            emoji = safe_col(p, "emoji") or ""
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(
                label=f"{emoji}  {p['name']}" if emoji else p["name"],
                xalign=0, margin_start=12, margin_end=12,
                margin_top=8, margin_bottom=8,
            )
            row.set_child(lbl)
            row._target_pid = p["id"]
            lb.append(row)
        def _on_row_activated(lb, row):
            with get_db() as c:
                for tid in self._selected_ids:
                    c.execute("UPDATE todo SET project_id=? WHERE id=?", (row._target_pid, tid))
            popover.popdown()
            self._exit_bulk_mode()
        lb.connect("row-activated", _on_row_activated)
        pop_box.append(lb)
        popover.set_child(pop_box)
        popover.set_parent(btn)
        popover.popup()

    def _bulk_done(self, _):
        today = date.today().isoformat()
        with get_db() as c:
            for tid in self._selected_ids:
                c.execute("UPDATE todo SET done=1, completed_date=? WHERE id=?", (today, tid))
        self._exit_bulk_mode()

    def _bulk_delete(self, _):
        n = len(self._selected_ids)
        ids = list(self._selected_ids)
        def _do():
            with get_db() as c:
                for tid in ids:
                    c.execute("DELETE FROM todo WHERE id=?", (tid,))
            self._exit_bulk_mode()
        _confirm_delete(self._win, "Delete tasks?",
                        f"{n} task{'s' if n != 1 else ''} will be permanently removed.", _do)

    def _exit_bulk_mode(self):
        self._bulk_mode = False
        self._selected_ids.clear()
        self._bulk_bar_rev.set_reveal_child(False)
        GLib.idle_add(self._build_content)

    def _toggle(self, tid):
        today = date.today().isoformat()
        with get_db() as c:
            r = c.execute("SELECT * FROM todo WHERE id=?", (tid,)).fetchone()
            if r["done"]:
                c.execute("UPDATE todo SET done=0, completed_date='' WHERE id=?", (tid,))
            else:
                c.execute("UPDATE todo SET done=1, completed_date=? WHERE id=?", (today, tid))
                recur = int(safe_col(r, "recur_days") or 0)
                if recur > 0:
                    recur_end = safe_col(r, "recur_end_date") or ""
                    if recur_end and date.today().isoformat() >= recur_end:
                        pass  # past end date, don't recreate
                    else:
                        due_back = (date.today() + timedelta(days=recur)).isoformat()
                        c.execute(
                            "INSERT INTO todo (project_id, text, done, priority, tags, "
                            "order_pos, completed_date, recur_days, recur_end_date, estimate_mins, blocked_by) "
                            "VALUES (?,?,0,?,?,0,?,?,?,?,0)",
                            (r["project_id"], r["text"], safe_col(r,"priority") or "normal",
                             safe_col(r,"tags") or "", due_back, recur, recur_end,
                             int(safe_col(r,"estimate_mins") or 0)),
                        )
        GLib.idle_add(self._build_content)

    def _update_priority(self, tid, priority):
        with get_db() as c:
            c.execute("UPDATE todo SET priority=? WHERE id=?", (priority, tid))

    def _delete(self, tid):
        def _do():
            with get_db() as c:
                c.execute("DELETE FROM todo WHERE id=?", (tid,))
            GLib.idle_add(self._build_content)
        _confirm_delete(self._win, "Delete task?", "This task will be permanently removed.", _do)

    def _refresh(self):
        self._build_content()


class GoalDetailView(Gtk.Box):
    def __init__(self, pid, goal_dict, win, push_fn=None, on_refresh=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                         margin_top=12, margin_bottom=12, margin_start=18, margin_end=18)
        self._pid = pid; self._win = win; self._push_fn = push_fn
        self._goal = goal_dict; self._on_refresh = on_refresh
        self._build()

    def _build(self):
        clear_box(self)
        g = self._goal
        # Reload from DB for freshness
        with get_db() as c:
            fresh = c.execute("SELECT * FROM goal WHERE id=?", (g["id"],)).fetchone()
        if fresh:
            g = {k: fresh[k] for k in fresh.keys()}
            self._goal = g

        # Info group
        info_grp = Adw.PreferencesGroup()
        start = safe_col(g, "start_date"); end = safe_col(g, "end_date")
        date_row = Adw.ActionRow(title="Timeline",
                                 subtitle=f"{start} → {end}" if start and end else (end or start or "No dates"))
        info_grp.add(date_row)
        notes = safe_col(g, "notes")
        if notes:
            notes_row = Adw.ActionRow(title="Notes", subtitle=notes)
            notes_row.set_subtitle_lines(3)
            info_grp.add(notes_row)
        self.append(info_grp)

        # Edit button
        edit_btn = Gtk.Button(label="Edit goal")
        edit_btn.add_css_class("suggested-action"); edit_btn.add_css_class("pill")
        edit_btn.set_halign(Gtk.Align.CENTER)
        edit_btn.connect("clicked", lambda _: GoalEditDialog(
            self._win, self._pid, goal=self._goal,
            on_save=lambda: (self._build(), self._on_refresh() if self._on_refresh else None)
        ).present())
        self.append(edit_btn)

        # Linked tasks
        with get_db() as c:
            linked = c.execute(
                "SELECT * FROM todo WHERE goal_id=? ORDER BY done, due_date",
                (g["id"],)
            ).fetchall()
        if linked:
            task_grp = Adw.PreferencesGroup(title="Tasks")
            open_n = sum(1 for t in linked if not t["done"])
            done_n = sum(1 for t in linked if t["done"])
            task_grp.set_description(f"{open_n} open · {done_n} done")
            for t in linked:
                trow = Adw.ActionRow(title=t["text"])
                if t["done"]:
                    trow.add_css_class("dim-label")
                    escaped = GLib.markup_escape_text(t["text"])
                    trow.set_use_markup(True)
                    trow.set_title(f"<s>{escaped}</s>")
                due = t["due_date"] or ""
                if due:
                    try:
                        delta = (datetime.strptime(due, "%Y-%m-%d").date() - date.today()).days
                        dl = "Due today" if delta == 0 else (f"Overdue {-delta}d" if delta < 0 else f"Due in {delta}d")
                    except ValueError:
                        dl = due
                    trow.set_subtitle(dl)
                check = Gtk.CheckButton(active=bool(t["done"]))
                check.set_valign(Gtk.Align.CENTER)
                tid = t["id"]
                def _on_toggle(b, _tid=tid):
                    today_s = date.today().isoformat()
                    with get_db() as c2:
                        if b.get_active():
                            c2.execute("UPDATE todo SET done=1, completed_date=? WHERE id=?", (today_s, _tid))
                        else:
                            c2.execute("UPDATE todo SET done=0, completed_date='' WHERE id=?", (_tid,))
                    GLib.idle_add(self._build)
                    if self._on_refresh: GLib.idle_add(self._on_refresh)
                check.connect("toggled", _on_toggle)
                trow.add_prefix(check)
                task_grp.add(trow)
            self.append(task_grp)
        else:
            empty = Adw.StatusPage(title="No tasks linked",
                                   description="Add tasks and assign them to this goal from the Tasks section",
                                   icon_name="checkbox-checked-symbolic")
            empty.set_vexpand(False)
            self.append(empty)


class GoalsView(Gtk.Box):
    def __init__(self, pid, win, push_fn=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=12, margin_start=18, margin_end=18)
        self._pid = pid; self._win = win; self._push_fn = push_fn

        tb = tip_banner("goals_v2",
            "Goals act as milestones on the Gantt chart — set a start and end date to see them plotted. "
            "Assign tasks to a goal to group them. Use +7d / +2w in date fields as shortcuts.")
        if tb: self.append(tb)

        # Gantt chart below the tip
        project = db_project(self._pid)
        gantt_lbl = Gtk.Label(label="Timeline", xalign=0)
        gantt_lbl.add_css_class("heading")
        self.append(gantt_lbl)
        hint = Gtk.Label()
        hint.set_markup("<i><span size='small'>Overdue items shown in red</span></i>")
        hint.set_halign(Gtk.Align.START)
        hint.add_css_class("dim-label")
        hint.set_margin_bottom(2)
        self.append(hint)
        self._gantt = GanttChart(self._pid, project, self._win)
        self.append(self._gantt)

        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.MANAGED)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_n, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: (
                GoalEditDialog(self._win, self._pid, on_save=self._refresh).present(), True)[1]),
        ))
        self.add_controller(sc)

        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.append(self._content)
        self._refresh()

    def _refresh(self):
        try:
            self._do_refresh()
            self._gantt._rebuild()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            lbl = Gtk.Label(label=f"Goals view error: {exc}", wrap=True)
            lbl.add_css_class("error")
            self._content.append(lbl)

    def _do_refresh(self):
        clear_box(self._content)
        goals = db_goals(self._pid)

        active_goals = [g for g in goals if not g["done"]]
        done_goals   = [g for g in goals if g["done"]]

        grp = Adw.PreferencesGroup(title="Goals")
        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("circular")
        add_btn.set_tooltip_text("New goal (Ctrl+N)")
        add_btn.connect("clicked", lambda _: GoalEditDialog(self._win, self._pid, on_save=self._refresh).present())
        grp.set_header_suffix(add_btn)

        if not goals:
            grp.add(Adw.ActionRow(title="No goals yet — press + to add one"))

        def _make_goal_row(g):
            g_snap = dict(g)
            priority = safe_col(g, "priority") or "normal"
            status   = compute_goal_status(g)
            start    = safe_col(g, "start_date")
            end      = safe_col(g, "end_date")

            # Task completion progress for this goal
            with get_db() as c:
                goal_tasks = c.execute(
                    "SELECT done FROM todo WHERE goal_id=?", (g["id"],)
                ).fetchall()
            task_total = len(goal_tasks)
            task_done  = sum(1 for t in goal_tasks if t["done"])

            row = Adw.ActionRow(title=g["text"])
            sub_parts = []
            if start and end:
                sub_parts.append(f"{start} → {end}")
            elif end:
                sub_parts.append(end)
            if task_total:
                sub_parts.append(f"{task_done}/{task_total} tasks done")
            notes = safe_col(g, "notes")
            if notes: sub_parts.append(notes)
            row.set_subtitle("  ·  ".join(sub_parts) if sub_parts else "No dates set")

            pri_lbl = Gtk.Label(label=priority.upper())
            pri_lbl.add_css_class("caption")
            _pri_css = {"high": "error", "low": "priority-low-lbl", "normal": "priority-normal-lbl"}
            pri_lbl.add_css_class(_pri_css.get(priority, "dim-label"))
            pri_lbl.set_valign(Gtk.Align.CENTER)
            pri_lbl.set_size_request(52, -1)
            pri_lbl.set_xalign(0.5)
            row.add_prefix(pri_lbl)

            badge = Gtk.Label(label=status)
            badge.add_css_class("caption")
            badge.add_css_class({"done": "success", "active": "accent", "future": "dim-label", "overdue": "error"}.get(status, "dim-label"))
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

            # Task progress bar if tasks are linked
            if task_total:
                pbar = Gtk.ProgressBar()
                pbar.set_fraction(task_done / task_total)
                pbar.set_size_request(60, -1)
                pbar.set_valign(Gtk.Align.CENTER)
                row.add_suffix(pbar)

            # Quick-add task linked to this goal
            quick_btn = Gtk.Button(icon_name="list-add-symbolic")
            quick_btn.add_css_class("flat"); quick_btn.set_valign(Gtk.Align.CENTER)
            quick_btn.set_tooltip_text("Add task to this goal")
            quick_btn.connect(
                "clicked",
                lambda _, gid=g["id"], gname=g["text"]:
                    QuickTaskDialog(self._win, self._pid, gname, on_save=self._refresh,
                                    goal_id=gid, goal_name=gname).present()
            )
            row.add_suffix(quick_btn)

            # Today / Stretch cycle button
            _tp = int(safe_col(g, "today_priority") or 0)
            _TODAY_STATES = [
                ("Today?",   ["dim-label"],           "Set as today's primary goal"),
                ("● Today",  ["accent"],              "Promote to stretch goal"),
                ("✦ Stretch", ["warning-label"],      "Clear today assignment"),
            ]
            _ts_lbl_txt, _ts_css, _ts_tip = _TODAY_STATES[_tp]
            today_lbl = Gtk.Label(label=_ts_lbl_txt)
            for _c in _ts_css: today_lbl.add_css_class(_c)
            today_lbl.add_css_class("caption")
            today_btn = Gtk.Button()
            today_btn.set_child(today_lbl)
            today_btn.add_css_class("flat")
            today_btn.set_valign(Gtk.Align.CENTER)
            today_btn.set_tooltip_text(_ts_tip)
            today_btn.connect("clicked", lambda _, gid=g["id"], cur=_tp: (
                db_set_today_goal(gid, (cur + 1) % 3), self._refresh()))
            row.add_suffix(today_btn)

            eb = Gtk.Button(icon_name="document-edit-symbolic")
            eb.add_css_class("flat"); eb.set_valign(Gtk.Align.CENTER)
            eb.connect("clicked", lambda _, gs=g_snap: GoalEditDialog(self._win, self._pid, goal=gs, on_save=self._refresh).present())
            row.add_suffix(eb)

            done_cb = Gtk.CheckButton(active=bool(g["done"]))
            done_cb.set_valign(Gtk.Align.CENTER)
            done_cb.set_tooltip_text("Mark done")
            done_cb.connect("toggled", lambda b, gid=g["id"]: self._toggle_done(gid, b.get_active()))
            row.add_suffix(done_cb)

            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.add_css_class("flat"); del_btn.add_css_class("destructive-action")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect("clicked", lambda _, gid=g["id"]: self._delete(gid))
            row.add_suffix(del_btn)

            if g["done"]:
                row.add_css_class("dim-label")

            # Single-click activatable → push GoalDetailView
            row.set_activatable(True)
            row.connect("activated", lambda _, gs=g_snap: self._push_fn and self._push_fn(
                gs["text"][:40],
                GoalDetailView(self._pid, gs, self._win,
                               push_fn=self._push_fn, on_refresh=self._refresh)
            ))
            # Double-click also pushes GoalDetailView
            add_dblclick(row, lambda gs=g_snap: self._push_fn and self._push_fn(
                gs["text"][:40],
                GoalDetailView(self._pid, gs, self._win,
                               push_fn=self._push_fn, on_refresh=self._refresh)
            ))

            return row

        for g in active_goals:
            grp.add(_make_goal_row(g))

        self._content.append(grp)

        # ── Completed goals (collapsible) ─────────────────────
        if done_goals:
            done_state = [False]
            n_done = len(done_goals)
            done_toggle_lbl = Gtk.Label(css_classes=["caption"])
            done_toggle_lbl.set_markup(f"<small>▶  {n_done} completed goal{'s' if n_done != 1 else ''}</small>")
            done_toggle_lbl.set_xalign(0)
            done_toggle_btn = Gtk.Button()
            done_toggle_btn.set_child(done_toggle_lbl)
            done_toggle_btn.add_css_class("flat")
            done_toggle_btn.set_margin_top(4)

            done_rev = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN, reveal_child=False)
            done_inner_grp = Adw.PreferencesGroup()
            for g in done_goals:
                done_inner_grp.add(_make_goal_row(g))
            done_rev.set_child(done_inner_grp)

            def _on_done_toggle(_btn):
                done_state[0] = not done_state[0]
                done_rev.set_reveal_child(done_state[0])
                arrow = "▼" if done_state[0] else "▶"
                done_toggle_lbl.set_markup(f"<small>{arrow}  {n_done} completed goal{'s' if n_done != 1 else ''}</small>")
            done_toggle_btn.connect("clicked", _on_done_toggle)

            self._content.append(done_toggle_btn)
            self._content.append(done_rev)


    def _toggle_done(self, gid, done):
        with get_db() as c:
            c.execute("UPDATE goal SET done=? WHERE id=?", (int(done), gid))
        self._refresh()

    def _delete(self, gid):
        def _do():
            with get_db() as c:
                c.execute("DELETE FROM goal WHERE id=?", (gid,))
            self._refresh()
        _confirm_delete(self._win, "Delete goal?", "This goal will be permanently removed.", _do)


class TagsView(Gtk.Box):
    def __init__(self, pid, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=12, margin_start=18, margin_end=18)
        self._pid = pid; self._win = win
        self._build()

    _KIND_LABEL = {
        "Task": "accent", "Goal": "success",
        "Note": "dim-label", "File": "dim-label",
    }

    def _build(self):
        items = all_tagged_items(self._pid)

        # Aggregate: tag → {total, done, items: [(kind, label, done)]}
        tag_data = {}
        for it in items:
            for tag in get_tags(it["tags"]):
                if tag not in tag_data:
                    tag_data[tag] = {"total": 0, "done": 0, "items": []}
                tag_data[tag]["total"] += 1
                if it["done"]:
                    tag_data[tag]["done"] += 1
                tag_data[tag]["items"].append(it)

        # ── Summary ───────────────────────────────────────────
        summary_grp = Adw.PreferencesGroup(title="Label overview")
        if not tag_data:
            summary_grp.add(Adw.ActionRow(
                title="No labels yet",
                subtitle="Add #tags to tasks, goals, notes, or files",
            ))
        else:
            for tag, data in sorted(tag_data.items(), key=lambda x: -x[1]["total"]):
                total = data["total"]
                done  = data["done"]
                pct   = int(done / total * 100) if total else 0

                kinds = {}
                for it in data["items"]:
                    kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
                kind_str = "  ".join(
                    f"{v} {k}{'s' if v>1 else ''}" for k, v in sorted(kinds.items()))

                row = Adw.ActionRow(title=f"#{tag}")
                row.set_subtitle(f"{total} items · {done} done · {pct}% · {kind_str}")

                bar = Gtk.ProgressBar()
                bar.set_fraction(pct / 100)
                bar.set_valign(Gtk.Align.CENTER)
                bar.set_size_request(80, -1)
                row.add_suffix(bar)

                badge = Gtk.Label(label=str(total))
                badge.add_css_class("caption"); badge.add_css_class("accent")
                badge.set_valign(Gtk.Align.CENTER)
                row.add_suffix(badge)

                summary_grp.add(row)
        self.append(summary_grp)

        # ── Per-tag item lists ────────────────────────────────
        if tag_data:
            for tag, data in sorted(tag_data.items(), key=lambda x: -x[1]["total"]):
                detail_grp = Adw.PreferencesGroup(title=f"#{tag}")
                for it in data["items"]:
                    escaped = GLib.markup_escape_text(it["label"])
                    title   = f"<s>{escaped}</s>" if it["done"] else it["label"]
                    drow = Adw.ActionRow(title=title)
                    try:
                        drow.set_use_markup(True)
                    except AttributeError:
                        pass
                    if it["done"]:
                        drow.add_css_class("dim-label")
                    kind_lbl = Gtk.Label(label=it["kind"])
                    kind_lbl.add_css_class("caption")
                    kind_lbl.add_css_class(self._KIND_LABEL.get(it["kind"], "dim-label"))
                    kind_lbl.set_valign(Gtk.Align.CENTER)
                    drow.add_suffix(kind_lbl)
                    detail_grp.add(drow)
                self.append(detail_grp)

    def _refresh(self):
        clear_box(self); self._build()


class ArchivedProjectsView(Gtk.Box):
    """All archived projects — browsable from the hamburger menu."""
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=24,
                         margin_start=18, margin_end=18)
        self._win = win
        self._build()

    def _build(self):
        clear_box(self)
        archived = [p for p in db_projects() if p["status"] == "archived"]
        if not archived:
            sp = Adw.StatusPage(
                title="No archived projects",
                description="Archive a project via Edit project → Status: archived",
                icon_name="folder-symbolic",
            )
            sp.set_vexpand(True); self.append(sp); return
        grp = Adw.PreferencesGroup(title=f"Archived  ({len(archived)})")
        for p in archived:
            todos = db_todos(p["id"])
            total = len(todos); done = sum(1 for t in todos if t["done"])
            emoji = safe_col(p, "emoji") or suggest_emoji(p["name"])
            row = Adw.ActionRow(title=f"{emoji}  {p['name']}")
            sub = f"{done}/{total} tasks done" if total else "No tasks"
            row.set_subtitle(sub)
            dot = color_dot(p["color"] or "#4fa8c4", size=12)
            dot.set_valign(Gtk.Align.CENTER)
            row.add_prefix(dot)
            chev = Gtk.Image(icon_name="go-next-symbolic")
            chev.add_css_class("dim-label"); row.add_suffix(chev)
            row.set_activatable(True)
            row.add_css_class("dim-label")
            row.connect("activated", lambda _, pid=p["id"]: self._win._open_project(
                pid, on_back=self._win.show_archived_projects))
            grp.add(row)
        self.append(grp)


class AllPinnedNotesView(Gtk.Box):
    """Global pinboard — all pinned notes across every project, in a card grid."""
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                         margin_top=16, margin_bottom=24,
                         margin_start=18, margin_end=18)
        self._win = win
        self._build()

    def _build(self):
        clear_box(self)
        pinned_all = []
        for p in db_projects():
            for n in db_notes(p["id"]):
                if n["pinned"]:
                    pinned_all.append((n, p))
        if not pinned_all:
            sp = Adw.StatusPage(
                title="No pinned notes",
                description="Pin a note inside any project to see it here",
                icon_name="starred-symbolic",
            )
            sp.set_vexpand(True); self.append(sp); return

        # Group by project
        from collections import defaultdict
        by_project = defaultdict(list)
        proj_map = {}
        for n, p in pinned_all:
            by_project[p["id"]].append(n)
            proj_map[p["id"]] = p

        for pid, notes in by_project.items():
            p = proj_map[pid]
            emoji = safe_col(p, "emoji") or suggest_emoji(p["name"])
            grp = Adw.PreferencesGroup(title=f"{emoji}  {p['name']}")
            open_btn = Gtk.Button(label="Open project")
            open_btn.add_css_class("flat")
            open_btn.connect("clicked", lambda _, pid=pid: self._win._open_project(pid, on_back=self._win.show_pinned_notes))
            grp.set_header_suffix(open_btn)
            for n in notes:
                snippet = (n["content"] or "").replace("\n", "  ")
                if len(snippet) > 140:
                    snippet = snippet[:140] + "…"
                row = Adw.ActionRow(title=snippet or "(empty note)")
                row.set_title_lines(3)
                row.set_subtitle(n["created_date"])
                star = Gtk.Image(icon_name="starred-symbolic")
                star.add_css_class("accent"); star.set_valign(Gtk.Align.CENTER)
                row.add_prefix(star)
                edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
                edit_btn.add_css_class("flat"); edit_btn.set_valign(Gtk.Align.CENTER)
                n_snap = dict(n)
                edit_btn.connect("clicked", lambda _, ns=n_snap, ppid=pid:
                    NoteDialog(self._win, ppid, note=ns, on_save=self._build).present())
                row.add_suffix(edit_btn)
                row.set_activatable(True)
                row.connect("activated", lambda _, ns=n_snap, ppid=pid:
                    NoteDialog(self._win, ppid, note=ns, on_save=self._build).present())
                grp.add(row)
            self.append(grp)


class NoteEditView(Gtk.Box):
    """Full-screen note editor pushed onto the navigation stack."""
    def __init__(self, pid, win, note=None, on_save=None, pop_fn=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._pid = pid; self._win = win; self._note = note; self._on_save = on_save
        self._pop_fn = pop_fn

        toolbar = Gtk.Box(spacing=8,
                          margin_top=8, margin_bottom=8,
                          margin_start=12, margin_end=12)

        pin_icon = "starred-symbolic" if (note and safe_col(note, "pinned")) else "non-starred-symbolic"
        self._pin_btn = Gtk.ToggleButton(icon_name=pin_icon, active=bool(note and safe_col(note, "pinned")))
        self._pin_btn.add_css_class("flat")
        self._pin_btn.set_tooltip_text("Pin to dashboard")
        self._pin_btn.connect("toggled", lambda btn: btn.set_icon_name(
            "starred-symbolic" if btn.get_active() else "non-starred-symbolic"
        ))
        toolbar.append(self._pin_btn)

        self._tags_entry = Gtk.Entry(placeholder_text="Labels (e.g. #idea #todo)",
                                     hexpand=True)
        self._tags_entry.set_text(safe_col(note, "tags") if note else "")
        toolbar.append(self._tags_entry)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._save)
        toolbar.append(save_btn)

        self.append(toolbar)

        sep = Gtk.Separator()
        self.append(sep)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        self._tv = Gtk.TextView(vexpand=True, hexpand=True,
                                top_margin=12, bottom_margin=12,
                                left_margin=18, right_margin=18,
                                wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self._tv.add_css_class("monospace")
        if note:
            self._tv.get_buffer().set_text(note["content"])
        scroll.set_child(self._tv)
        self.append(scroll)

        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.MANAGED)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: (self._save(None), self._pop_fn() if self._pop_fn else None) or True),
        ))
        self.add_controller(sc)

    def _save(self, _):
        buf = self._tv.get_buffer()
        content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        if not content.strip(): return
        tags    = normalize_tag_input(self._tags_entry.get_text())
        pinned  = 1 if self._pin_btn.get_active() else 0
        today   = date.today().isoformat()
        with get_db() as c:
            if self._note:
                c.execute(
                    "UPDATE note SET content=?,tags=?,pinned=? WHERE id=?",
                    (content, tags, pinned, self._note["id"]),
                )
            else:
                c.execute(
                    "INSERT INTO note (project_id,content,tags,pinned,created_date) VALUES (?,?,?,?,?)",
                    (self._pid, content, tags, pinned, today),
                )
        if self._on_save: self._on_save()


class NotesView(Gtk.Box):
    def __init__(self, pid, win, push_fn=None, pop_fn=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=12, margin_start=18, margin_end=18)
        self._pid = pid; self._win = win; self._push_fn = push_fn; self._pop_fn = pop_fn
        self._search_text = ""

        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.MANAGED)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_n, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: self._open_new() or True),
        ))
        self.add_controller(sc)

        search_entry = Gtk.SearchEntry(placeholder_text="Search notes…")
        search_entry.connect("search-changed", self._on_search)
        self.append(search_entry)

        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.append(self._content)
        self._refresh()

    def _on_search(self, entry):
        self._search_text = entry.get_text().strip().lower()
        self._refresh()

    def _open_new(self):
        if self._push_fn:
            view = NoteEditView(self._pid, self._win, on_save=self._refresh, pop_fn=self._pop_fn)
            self._push_fn("New Note", view)
        else:
            NoteDialog(self._win, self._pid, on_save=self._refresh).present()

    def _open_edit(self, note):
        if self._push_fn:
            view = NoteEditView(self._pid, self._win, note=note, on_save=self._refresh, pop_fn=self._pop_fn)
            self._push_fn(note["content"][:30].replace("\n", " "), view)
        else:
            NoteDialog(self._win, self._pid, note=note, on_save=self._refresh).present()

    def _refresh(self):
        clear_box(self._content)
        all_notes = db_notes(self._pid)
        q = self._search_text
        notes = [n for n in all_notes
                 if not q or q in n["content"].lower() or q in (safe_col(n, "tags") or "").lower()]
        title = "Notes" if not q else f"Notes — {len(notes)} match{'es' if len(notes) != 1 else ''}"
        grp = Adw.PreferencesGroup(title=title)
        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("circular")
        add_btn.set_tooltip_text("New note")
        add_btn.connect("clicked", lambda _: self._open_new())
        grp.set_header_suffix(add_btn)
        if not notes:
            grp.add(Adw.ActionRow(title="No notes yet — press + or Ctrl+N to add one"))
        for n in notes:
            snippet = n["content"][:80].replace("\n", " ")
            if len(n["content"]) > 80: snippet += "…"
            tags = get_tags(safe_col(n, "tags"))
            sub_parts = [n["created_date"]]
            if tags: sub_parts.append("  ".join(f"#{t}" for t in tags))
            row = Adw.ActionRow(title=snippet, subtitle="  ·  ".join(sub_parts))
            row.set_title_lines(2)

            if n["pinned"]:
                star = Gtk.Image(icon_name="starred-symbolic")
                star.add_css_class("accent"); star.set_valign(Gtk.Align.CENTER)
                row.add_prefix(star)

            pin_icon = "starred-symbolic" if n["pinned"] else "non-starred-symbolic"
            pin_btn = Gtk.Button(icon_name=pin_icon)
            pin_btn.add_css_class("flat")
            if n["pinned"]: pin_btn.add_css_class("accent")
            pin_btn.set_valign(Gtk.Align.CENTER)
            pin_btn.set_tooltip_text("Unpin from dashboard" if n["pinned"] else "Pin to dashboard")
            pin_btn.connect("clicked", lambda _, nid=n["id"], p=n["pinned"]: self._toggle_pin(nid, p))

            n_snap = dict(n)
            eb = Gtk.Button(icon_name="document-edit-symbolic")
            eb.add_css_class("flat"); eb.set_valign(Gtk.Align.CENTER)
            eb.connect("clicked", lambda _, nt=n_snap: self._open_edit(nt))
            add_dblclick(row, lambda nt=n_snap: self._open_edit(nt))

            db_btn = Gtk.Button(icon_name="user-trash-symbolic")
            db_btn.add_css_class("flat"); db_btn.add_css_class("destructive-action")
            db_btn.set_valign(Gtk.Align.CENTER)
            db_btn.connect("clicked", lambda _, nid=n["id"]: self._delete(nid))

            row.add_suffix(pin_btn); row.add_suffix(eb); row.add_suffix(db_btn)
            grp.add(row)
        self._content.append(grp)

    def _toggle_pin(self, nid, currently_pinned):
        with get_db() as c:
            c.execute("UPDATE note SET pinned=? WHERE id=?", (0 if currently_pinned else 1, nid))
        self._refresh()

    def _delete(self, nid):
        def _do():
            with get_db() as c:
                c.execute("DELETE FROM note WHERE id=?", (nid,))
            self._refresh()
        _confirm_delete(self._win, "Delete note?", "This note will be permanently removed.", _do)


class FilesView(Gtk.Box):
    def __init__(self, pid, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=12, margin_start=18, margin_end=18)
        self._pid = pid; self._win = win
        self._build()

    def _build(self):
        files = db_files(self._pid)
        grp = Adw.PreferencesGroup(title="Linked files")
        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("circular")
        add_btn.set_tooltip_text("Link a file")
        add_btn.connect("clicked", self._pick_file)
        grp.set_header_suffix(add_btn)
        if not files:
            grp.add(Adw.ActionRow(title="No files linked — press + to link one"))
        for f in files:
            tags = get_tags(safe_col(f, "tags"))
            sub = f["path"]
            if tags:
                sub += "  " + "  ".join(f"#{t}" for t in tags)
            row = Adw.ActionRow(title=f["name"], subtitle=sub)
            row.set_subtitle_lines(1)
            open_btn = Gtk.Button(icon_name="document-open-symbolic")
            open_btn.add_css_class("flat"); open_btn.set_valign(Gtk.Align.CENTER)
            open_btn.set_tooltip_text("Open with default app")
            open_btn.connect("clicked", lambda _, p=f["path"]: self._open_file(p))
            f_snap = dict(f)
            eb = Gtk.Button(icon_name="document-edit-symbolic")
            eb.add_css_class("flat"); eb.set_valign(Gtk.Align.CENTER)
            eb.connect("clicked", lambda _, fr=f_snap: FileEditDialog(
                self._win, fr, on_save=self._refresh).present())
            add_dblclick(row, lambda fr=f_snap: FileEditDialog(
                self._win, fr, on_save=self._refresh).present())
            db_btn = Gtk.Button(icon_name="user-trash-symbolic")
            db_btn.add_css_class("flat"); db_btn.add_css_class("destructive-action")
            db_btn.set_valign(Gtk.Align.CENTER)
            db_btn.connect("clicked", lambda _, fid=f["id"]: self._delete(fid))
            row.add_suffix(open_btn); row.add_suffix(eb); row.add_suffix(db_btn)
            grp.add(row)
        self.append(grp)

    def _refresh(self):
        clear_box(self); self._build()

    def _pick_file(self, _):
        chooser = Gtk.FileChooserNative(
            title="Link a file",
            transient_for=self._win,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Link",
            cancel_label="Cancel",
        )
        chooser.connect("response", self._on_file_chosen)
        chooser.show()
        self._chooser = chooser  # keep reference

    def _on_file_chosen(self, chooser, response):
        if response == Gtk.ResponseType.ACCEPT:
            gfile = chooser.get_file()
            if gfile:
                path = gfile.get_path()
                name = os.path.basename(path)
                with get_db() as c:
                    c.execute(
                        "INSERT INTO file (project_id,name,path,added_date) VALUES (?,?,?,?)",
                        (self._pid, name, path, date.today().isoformat()),
                    )
                GLib.idle_add(self._refresh)

    def _open_file(self, path):
        uri = GLib.filename_to_uri(path, None)
        Gio.AppInfo.launch_default_for_uri(uri, None)

    def _delete(self, fid):
        def _do():
            with get_db() as c:
                c.execute("DELETE FROM file WHERE id=?", (fid,))
            GLib.idle_add(self._refresh)
        _confirm_delete(self._win, "Delete file link?",
                        "The link will be removed. The file on disk is not affected.", _do)


# ══════════════════════════════════════════════════════
# Home / overview dashboard
# ══════════════════════════════════════════════════════

class GlobalSearchView(Gtk.Box):
    def __init__(self, query, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=24,
                         margin_start=18, margin_end=18)
        self._win = win
        results = db_search(query)
        if not results:
            sp = Adw.StatusPage(
                title=f'No results for "{query}"',
                description="Try a different search term",
                icon_name="system-search-symbolic",
            )
            sp.set_vexpand(True)
            self.append(sp)
            return
        n = len(results)
        grp = Adw.PreferencesGroup(
            title=f'{n} result{"s" if n != 1 else ""} for "{query}"'
        )
        for r in results:
            title = r["title"][:80].replace("\n", " ")
            escaped = GLib.markup_escape_text(title)
            if safe_col(r, "is_done"):
                escaped = f"<s>{escaped}</s>"
            row = Adw.ActionRow(title=escaped, subtitle=f"{r['kind']}  ·  {r['project_name']}")
            row.set_use_markup(True)
            row.set_activatable(True)
            row.connect("activated", lambda _, pid=r["project_id"]: win._open_project(pid))
            grp.add(row)
        self.append(grp)


class AllTasksGoalsView(Gtk.Box):
    """Undone todos + goals across every project — one scrollable list."""
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=24,
                         margin_start=18, margin_end=18)
        self._win = win
        any_shown = False
        for p in db_projects():
            todos = db_todos(p["id"])
            goals = db_goals(p["id"])
            undone_t = [t for t in todos if not t["done"]]
            undone_g = [g for g in goals if not g["done"]]
            if not undone_t and not undone_g:
                continue
            any_shown = True
            grp = Adw.PreferencesGroup(title=p["name"])
            for t in undone_t:
                row = Adw.ActionRow(title=GLib.markup_escape_text(t["text"]), subtitle="Task")
                row.set_use_markup(True)
                grp.add(row)
            for g in undone_g:
                row = Adw.ActionRow(title=GLib.markup_escape_text(g["text"]))
                row.set_use_markup(True)
                status   = safe_col(g, "status") or "pending"
                end_date = safe_col(g, "end_date") or safe_col(g, "due_date") or ""
                sub = f"Goal  ·  {status}"
                if end_date:
                    sub += f"  ·  due {end_date}"
                row.set_subtitle(sub)
                grp.add(row)
            open_btn = Gtk.Button(label="Open project")
            open_btn.add_css_class("flat")
            open_btn.connect("clicked", lambda _, pid=p["id"]: win._open_project(pid, on_back=win.show_all_tasks))
            grp.set_header_suffix(open_btn)
            self.append(grp)
        if not any_shown:
            sp = Adw.StatusPage(
                title="All caught up!",
                description="No pending tasks or goals across any project",
                icon_name="checkbox-checked-symbolic",
            )
            sp.set_vexpand(True)
            self.append(sp)


class AllFilesView(Gtk.Box):
    """All linked files across every project."""
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=24,
                         margin_start=18, margin_end=18)
        self._win = win
        files = db_all_files_with_project()
        if not files:
            sp = Adw.StatusPage(
                title="No files linked yet",
                description="Open a project and add files in the Files section",
                icon_name="folder-open-symbolic",
            )
            sp.set_vexpand(True)
            self.append(sp)
            return
        groups = {}
        for f in files:
            pid = f["project_id"]
            if pid not in groups:
                groups[pid] = Adw.PreferencesGroup(title=f["project_name"])
            path = f["path"]
            row = Adw.ActionRow(title=f["name"])
            row.set_subtitle(path if len(path) <= 70 else "…" + path[-67:])
            row.set_tooltip_text(path)
            row.set_activatable(True)
            row.connect("activated", lambda _, p=path: self._open(p))
            open_btn = Gtk.Button(icon_name="folder-open-symbolic")
            open_btn.add_css_class("flat"); open_btn.set_valign(Gtk.Align.CENTER)
            open_btn.set_tooltip_text("Open file")
            open_btn.connect("clicked", lambda _, p=path: self._open(p))
            row.add_suffix(open_btn)
            groups[pid].add(row)
        for grp in groups.values():
            self.append(grp)

    def _open(self, path):
        try:
            uri = GLib.filename_to_uri(path, None)
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except Exception:
            try:
                import subprocess
                subprocess.Popen(["xdg-open", path])
            except Exception:
                pass


class ComingUpView(Gtk.Box):
    """All upcoming goals and tasks with end/due dates across all projects."""
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=24,
                         margin_start=18, margin_end=18)
        self._win = win
        self._build()

    def _build(self):
        clear_box(self)
        items = db_coming_up(90)
        if not items:
            sp = Adw.StatusPage(
                title="Nothing due in the next 90 days",
                description="Add goal end dates or task due dates to see them here",
                icon_name="flag-symbolic",
            )
            sp.set_vexpand(True)
            self.append(sp)
            return

        def month_key(it):
            try:
                return datetime.strptime(it["end_date"], "%Y-%m-%d").strftime("%B %Y")
            except ValueError:
                return "Unknown"

        seen_months = {}
        for it in items:
            mk = month_key(it)
            if mk not in seen_months:
                seen_months[mk] = Adw.PreferencesGroup(title=mk)

            end_date  = it["end_date"]
            try:
                days_left = (datetime.strptime(end_date, "%Y-%m-%d").date() - date.today()).days
            except ValueError:
                days_left = 999
            urgency_cl = "error" if days_left <= 2 else ("warning" if days_left <= 7 else "")
            urgency_tx = ("today!" if days_left == 0 else
                          "tomorrow" if days_left == 1 else f"{days_left}d")

            row = Adw.ActionRow(title=it["title"])
            row.set_subtitle(f"{it['kind']}  ·  {it['project_name']}")
            row.set_activatable(True)

            dot = color_dot(it.get("project_color") or "#4fa8c4", size=10)
            dot.set_valign(Gtk.Align.CENTER)
            row.add_prefix(dot)
            row.connect("activated", lambda _, pid=it["project_id"], kind=it["kind"]:
                self._win._open_project(pid, section="goals" if kind == "Goal" else "tasks"))

            ul = Gtk.Label(label=urgency_tx)
            ul.add_css_class("caption")
            if urgency_cl: ul.add_css_class(urgency_cl)
            ul.set_valign(Gtk.Align.CENTER)
            row.add_suffix(ul)
            seen_months[mk].add(row)

        for grp in seen_months.values():
            self.append(grp)


class TodayView(Gtk.Box):
    """Tasks due today and overdue, across all projects."""
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=24,
                         margin_start=18, margin_end=18)
        self._win = win
        self._build()

    def _build(self):
        clear_box(self)
        tasks = db_today_tasks()
        today = date.today().isoformat()

        if not tasks:
            sp = Adw.StatusPage(
                title="Nothing due today",
                description="Enjoy the clear schedule",
                icon_name="checkbox-checked-symbolic",
            )
            sp.set_vexpand(True)
            self.append(sp)
            return

        overdue   = [t for t in tasks if t["due_date"] < today]
        due_today = [t for t in tasks if t["due_date"] == today]

        if overdue:
            ov_grp = Adw.PreferencesGroup(title=f"Overdue  ({len(overdue)})")
            for t in overdue:
                ov_grp.add(self._make_row(t, overdue=True))
            self.append(ov_grp)

        if due_today:
            td_grp = Adw.PreferencesGroup(title=f"Due today  ({len(due_today)})")
            for t in due_today:
                td_grp.add(self._make_row(t))
            self.append(td_grp)

    def _make_row(self, t, overdue=False):
        row = Adw.ActionRow(title=safe_col(t, "text") or "")
        row.set_subtitle(safe_col(t, "project_name") or "")
        row.set_activatable(True)
        row.connect("activated", lambda _, pid=t["project_id"]:
            self._win._open_project(pid, section="tasks"))

        dot = color_dot(safe_col(t, "project_color") or "#4fa8c4", size=10)
        dot.set_valign(Gtk.Align.CENTER)
        row.add_prefix(dot)

        if safe_col(t, "priority") == "high":
            pbar = Gtk.Box(); pbar.set_size_request(4, -1)
            pbar.add_css_class("priority-bar"); pbar.add_css_class("priority-high")
            pbar.set_valign(Gtk.Align.FILL)
            row.add_prefix(pbar)

        if overdue:
            try:
                days_late = (date.today() -
                             datetime.strptime(t["due_date"], "%Y-%m-%d").date()).days
                late_lbl = Gtk.Label(label=f"{days_late}d late")
                late_lbl.add_css_class("caption"); late_lbl.add_css_class("error")
                late_lbl.set_valign(Gtk.Align.CENTER)
                row.add_suffix(late_lbl)
            except (ValueError, TypeError):
                pass
            row.add_css_class("overdue-project-row")

        chev = Gtk.Image(icon_name="go-next-symbolic")
        chev.add_css_class("dim-label")
        row.add_suffix(chev)
        return row


class HomeView(Gtk.Box):
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=24,
                         margin_start=18, margin_end=18)
        self._win = win

        self._build()

    # ── Build ──────────────────────────────────────────

    def _build(self):
        projects = db_projects()

        if not projects:
            sp = Adw.StatusPage(
                title="No projects yet",
                description="Press + in the sidebar to create your first project",
                icon_name="folder-symbolic",
            )
            self.append(sp)
            return

        # ── Homepage tip ──────────────────────────────
        tb = tip_banner("homepage",
            "Click Overall progress to see all tasks and goals across every project. "
            "Project rows highlighted in red or yellow have overdue items. "
            "Press + on any project row to add a task without opening it.")
        if tb: self.append(tb)

        # ── Overall headline ──────────────────────────
        all_todos = []
        for p in projects:
            all_todos.extend(db_todos(p["id"]))
        total_tasks = len(all_todos)
        done_tasks  = sum(1 for t in all_todos if t["done"])
        overall_pct = done_tasks / total_tasks if total_tasks else 0

        headline = Adw.PreferencesGroup()
        ov_row = Adw.ActionRow(title="Overall progress")
        quip = _progress_quip(overall_pct, total_tasks)
        task_summary = (
            f"{done_tasks} of {total_tasks} done across {len(projects)} project{'s' if len(projects)!=1 else ''}"
            if total_tasks else
            f"{len(projects)} project{'s' if len(projects)!=1 else ''}, no tasks yet"
        )
        ov_row.set_subtitle(f"{quip}  ·  {task_summary}")
        bar = Gtk.ProgressBar()
        bar.set_fraction(overall_pct)
        bar.set_valign(Gtk.Align.CENTER)
        bar.set_size_request(120, -1)
        ov_row.add_suffix(bar)
        pct_lbl = Gtk.Label(label=f"{int(overall_pct*100)}%")
        pct_lbl.add_css_class("caption")
        pct_lbl.add_css_class("accent" if overall_pct > 0 else "dim-label")
        pct_lbl.set_valign(Gtk.Align.CENTER)
        ov_row.add_suffix(pct_lbl)
        chev = Gtk.Image(icon_name="go-next-symbolic"); chev.add_css_class("dim-label")
        ov_row.add_suffix(chev)
        ov_row.set_activatable(True)
        ov_row.set_tooltip_text("View all tasks and goals")
        ov_row.connect("activated", lambda _: self._win.show_all_tasks())
        headline.add(ov_row)

        # ── Monthly busyness summary ───────────────────
        _med_t   = int(get_setting("busyness_medium", "8"))
        _heavy_t = int(get_setting("busyness_heavy",  "15"))
        month_due, month_high, month_overdue = db_monthly_summary()
        if month_due > 0 or month_overdue > 0:
            if month_due >= _heavy_t:
                level, level_cls = "Heavy", "error"
            elif month_due >= _med_t:
                level, level_cls = "Medium", "warning"
            elif month_due >= 1:
                level, level_cls = "Light", "success"
            else:
                level, level_cls = "", "dim-label"
            sub_parts = []
            if month_due:
                sub_parts.append(f"{month_due} task{'s' if month_due != 1 else ''} due")
            if month_high:
                sub_parts.append(f"{month_high} high priority")
            if month_overdue:
                sub_parts.append(f"{month_overdue} overdue carrying over")
            month_row = Adw.ActionRow(title="Next 30 days")
            month_row.set_subtitle("  ·  ".join(sub_parts))
            cal_icon = Gtk.Image(icon_name="office-calendar-symbolic")
            cal_icon.set_pixel_size(20); cal_icon.add_css_class("accent")
            month_row.add_prefix(cal_icon)
            if level:
                level_lbl = Gtk.Label(label=level)
                level_lbl.add_css_class("caption")
                level_lbl.add_css_class(level_cls)
                level_lbl.set_valign(Gtk.Align.CENTER)
                month_row.add_suffix(level_lbl)
            headline.add(month_row)

        files_row = Adw.ActionRow(title="All linked files")
        files_row.set_subtitle("Browse files linked across all projects")
        files_icon = Gtk.Image(icon_name="folder-open-symbolic")
        files_icon.set_pixel_size(20); files_icon.add_css_class("accent")
        files_row.add_prefix(files_icon)
        chev2 = Gtk.Image(icon_name="go-next-symbolic"); chev2.add_css_class("dim-label")
        files_row.add_suffix(chev2)
        files_row.set_activatable(True)
        files_row.connect("activated", lambda _: self._win.show_all_files())
        headline.add(files_row)

        # ── Pomodoro sessions this week ───────────────
        pomo_count, pomo_mins = db_pomodoro_week()
        if pomo_count > 0:
            h, m = divmod(pomo_mins, 60)
            pomo_time = f"{h}h {m}m" if h else f"{m}m"
            pomo_row = Adw.ActionRow(title="Focus sessions this week")
            pomo_row.set_subtitle(f"{pomo_count} session{'s' if pomo_count != 1 else ''}  ·  {pomo_time} of deep work")
            t_icon = Gtk.Image()
            t_icon.set_from_icon_name("clock-symbolic")
            t_icon.set_pixel_size(20); t_icon.add_css_class("accent")
            pomo_row.add_prefix(t_icon)
            headline.add(pomo_row)

        self.append(headline)

        # ── Today's goals (primary + stretch) ─────────
        primary_g, stretch_g = db_today_goals()
        if primary_g or stretch_g:
            tg_grp = Adw.PreferencesGroup(title="Today's goals")

            def _make_today_goal_row(g, label_text, label_css):
                done = bool(g["done"])
                row = Adw.ActionRow()
                tier_lbl = Gtk.Label(label=label_text)
                tier_lbl.add_css_class("caption"); tier_lbl.add_css_class(label_css)
                tier_lbl.set_valign(Gtk.Align.CENTER)
                tier_lbl.set_size_request(48, -1)
                row.add_prefix(tier_lbl)

                title = safe_col(g, "text") or ""
                if done:
                    row.set_title(f"✓  {title}")
                    row.add_css_class("dim-label")
                else:
                    row.set_title(title)
                proj_part = (safe_col(g, "project_emoji") or "") + "  " + (safe_col(g, "project_name") or "")
                row.set_subtitle(proj_part.strip())
                row.set_activatable(True)
                row.connect("activated", lambda _, pid=g["project_id"]:
                    self._win._open_project(pid, section="goals"))

                if not done:
                    done_btn = Gtk.Button(label="Done!")
                    done_btn.add_css_class("flat"); done_btn.add_css_class("suggested-action")
                    done_btn.set_valign(Gtk.Align.CENTER)
                    def _mark_done(_, gid=g["id"]):
                        with get_db() as c:
                            c.execute("UPDATE goal SET done=1 WHERE id=?", (gid,))
                        GLib.idle_add(self._build)
                    done_btn.connect("clicked", _mark_done)
                    row.add_suffix(done_btn)
                return row

            if primary_g:
                tg_grp.add(_make_today_goal_row(primary_g, "Primary", "accent"))

            if stretch_g:
                row = _make_today_goal_row(stretch_g, "Stretch", "warning-label")
                if primary_g and not primary_g["done"]:
                    row.set_sensitive(False)
                    row.set_tooltip_text("Complete your primary goal first")
                tg_grp.add(row)

            self.append(tg_grp)

        # ── Inspirational quote (keyed to busyness) ───
        q_level = ("heavy" if month_due >= _heavy_t else
                   "medium" if month_due >= _med_t else
                   "light" if month_due >= 1 else "clear")
        q_text, q_attr = _pick_quote(q_level)
        q_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                        margin_top=4, margin_bottom=4)
        q_lbl = Gtk.Label(wrap=True, xalign=0)
        q_lbl.set_markup(f"<i>{GLib.markup_escape_text(q_text)}</i>")
        q_lbl.add_css_class("dim-label")
        q_box.append(q_lbl)
        a_lbl = Gtk.Label(label=q_attr, xalign=1)
        a_lbl.add_css_class("caption"); a_lbl.add_css_class("dim-label")
        q_box.append(a_lbl)
        self.append(q_box)

        # ── Mini due-date calendar ─────────────────────
        cal_lbl = Gtk.Label(label="Due dates this month", xalign=0)
        cal_lbl.add_css_class("heading")
        cal_lbl.set_margin_top(4)
        self.append(cal_lbl)
        cal = Gtk.Calendar()
        cal.add_css_class("card")
        _refresh_calendar_marks(cal)
        cal.connect("notify::year",  lambda c, _: _refresh_calendar_marks(c))
        cal.connect("notify::month", lambda c, _: _refresh_calendar_marks(c))
        self.append(cal)

        # ── Per-project rows ──────────────────────────
        def _make_proj_row(p):
            todos = db_todos(p["id"])
            total = len(todos)
            done  = sum(1 for t in todos if t["done"])
            pct   = done / total if total else 0
            left  = total - done
            p_emoji = safe_col(p, "emoji") or suggest_emoji(p["name"])
            health_color, health_reason = project_health(p["id"])
            row = Adw.ActionRow(title=f"{p_emoji}  {p['name']}")
            row.add_css_class("proj-bold-row")
            sub_parts = [p["status"]]
            if total:
                sub_parts.append(f"{left} left · {done} done" if left else f"All {total} done ✓")
            row.set_subtitle("  ·  ".join(sub_parts))
            dot = color_dot(p["color"], size=12)
            dot.set_valign(Gtk.Align.CENTER)
            row.add_prefix(dot)
            health_dot = Gtk.Label(label="●")
            health_dot.set_valign(Gtk.Align.CENTER)
            health_dot.set_tooltip_text(health_reason)
            _HEALTH_CSS = {"green": "success", "yellow": "warning", "red": "error"}
            health_dot.add_css_class(_HEALTH_CSS.get(health_color, "dim-label"))
            if health_color == "red":
                row.add_css_class("overdue-project-row")
                overdue_btn = Gtk.Button(label="Overdue →")
                overdue_btn.add_css_class("flat"); overdue_btn.add_css_class("error")
                overdue_btn.set_valign(Gtk.Align.CENTER)
                overdue_btn.set_tooltip_text("Jump to overdue tasks")
                overdue_btn.connect(
                    "clicked",
                    lambda _, pid=p["id"]: self._win._open_project(pid, section="tasks")
                )
                row.add_suffix(overdue_btn)
            elif health_color == "yellow":
                row.add_css_class("warning")
            row.add_prefix(health_dot)
            if total:
                prog_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                   spacing=2, valign=Gtk.Align.CENTER)
                pbar = Gtk.ProgressBar()
                pbar.set_fraction(pct)
                pbar.set_size_request(130, -1)
                # tint bar with project colour via inline CSS
                try:
                    r, g, b = (int(p["color"].lstrip("#")[i:i+2], 16)/255
                               for i in (0, 2, 4))
                    css = (f".proj-bar-{p['id']} progress {{"
                           f"background-color: rgba({int(r*255)},{int(g*255)},{int(b*255)},0.85);}}")
                    prov = Gtk.CssProvider()
                    prov.load_from_string(css)
                    pbar.add_css_class(f"proj-bar-{p['id']}")
                    pbar.get_style_context().add_provider(prov,
                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                except Exception:
                    pass
                frac_lbl = Gtk.Label(
                    label=f"{done}/{total}",
                    css_classes=["caption", "dim-label"],
                    halign=Gtk.Align.CENTER,
                )
                prog_box.append(pbar)
                prog_box.append(frac_lbl)
                row.add_suffix(prog_box)
            add_btn = Gtk.Button(icon_name="list-add-symbolic")
            add_btn.add_css_class("flat"); add_btn.set_valign(Gtk.Align.CENTER)
            add_btn.set_tooltip_text("Quick add task")
            add_btn.connect(
                "clicked",
                lambda _, pid=p["id"], pname=p["name"]:
                    QuickTaskDialog(self._win, pid, pname, on_save=self._refresh).present(),
            )
            row.add_suffix(add_btn)
            row.set_activatable(True)
            row.connect("activated", lambda _, pid=p["id"]: self._win._open_project(pid))
            return row

        active_ps = [p for p in projects if p["status"] != "archived"]

        proj_grp = Adw.PreferencesGroup(title="Projects",
                                         description='Projects in red have overdue items — click “Overdue” to jump straight to them')
        if not active_ps:
            proj_grp.add(Adw.ActionRow(
                title="All projects are archived",
                subtitle="Use 'View archived projects' in the menu to browse them",
            ))
        for p in active_ps:
            proj_grp.add(_make_proj_row(p))
        self.append(proj_grp)

        # ── Due in the next 14 days (goals + tasks) ───
        due_items = db_coming_up(14)
        if due_items:
            due_grp = Adw.PreferencesGroup(title="Due in the next 14 days")
            for it in due_items:
                end_date = it["end_date"]
                try:
                    days_left = (datetime.strptime(end_date, "%Y-%m-%d").date() - date.today()).days
                except ValueError:
                    continue
                urgency_cl = "error" if days_left <= 2 else ("warning" if days_left <= 7 else "dim-label")
                urgency_tx = ("today!" if days_left == 0 else
                              "tomorrow" if days_left == 1 else f"{days_left}d left")
                row = Adw.ActionRow(title=it["title"])
                kind_lbl = "🎯 Goal" if it["kind"] == "Goal" else "✓ Task"
                row.set_subtitle(f"{kind_lbl}  ·  {it['project_name']}  ·  {end_date}")
                dot = color_dot(it.get("project_color") or "#4fa8c4", size=10)
                dot.set_valign(Gtk.Align.CENTER)
                row.add_prefix(dot)
                row.set_activatable(True)
                row.connect("activated", lambda _, pid=it["project_id"], kind=it["kind"]:
                    self._win._open_project(pid, section="goals" if kind == "Goal" else "tasks"))
                ul = Gtk.Label(label=urgency_tx)
                ul.add_css_class("caption"); ul.add_css_class(urgency_cl)
                ul.set_valign(Gtk.Align.CENTER)
                row.add_suffix(ul)
                # Red left-border for goals within 3 days
                if it["kind"] == "Goal" and days_left <= 3:
                    row.add_css_class("overdue-project-row")
                due_grp.add(row)
            self.append(due_grp)

        # ── Coming up soon (15–90 days) ───────────────
        future = [it for it in db_coming_up(90)
                  if it["end_date"] > (date.today() + timedelta(days=14)).isoformat()]
        if future:
            preview = future[:4]
            cu_grp = Adw.PreferencesGroup(title=f"Coming up  ({len(future)} item{'s' if len(future)!=1 else ''} in next 90 days)")
            see_all_btn = Gtk.Button(label="See all")
            see_all_btn.add_css_class("flat")
            see_all_btn.connect("clicked", lambda _: self._win.show_coming_up())
            cu_grp.set_header_suffix(see_all_btn)
            for it in preview:
                end_date = it["end_date"]
                try:
                    dl = (datetime.strptime(end_date, "%Y-%m-%d").date() - date.today()).days
                except ValueError:
                    continue
                row = Adw.ActionRow(title=it["title"])
                row.set_subtitle(f"{it['kind']}  ·  {it['project_name']}  ·  {end_date}")
                dot = color_dot(it.get("project_color") or "#4fa8c4", size=10)
                dot.set_valign(Gtk.Align.CENTER)
                row.add_prefix(dot)
                row.set_activatable(True)
                row.connect("activated", lambda _, pid=it["project_id"], kind=it["kind"]:
                    self._win._open_project(pid, section="goals" if kind == "Goal" else "tasks"))
                dl_lbl = Gtk.Label(label=f"{dl}d")
                dl_lbl.add_css_class("caption"); dl_lbl.add_css_class("dim-label")
                dl_lbl.set_valign(Gtk.Align.CENTER)
                row.add_suffix(dl_lbl)
                cu_grp.add(row)
            self.append(cu_grp)

        # ── Multi-project Goals Gantt ─────────────────
        gantt_lbl = Gtk.Label(label="All Goals — Timeline", xalign=0, margin_top=8)
        gantt_lbl.add_css_class("heading")
        self.append(gantt_lbl)
        self.append(GanttChart(None, None, self._win))

    def _refresh(self):
        """Rebuild home view in-place (called after quick task add)."""
        self._win.show_home()


# ══════════════════════════════════════════════════════
# Project detail — dashboard + navigation
# ══════════════════════════════════════════════════════

class PomodoroWidget(Gtk.Box):
    """Compact horizontal Pomodoro timer bar — embed in a Gtk.Revealer."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                         margin_start=16, margin_end=16,
                         margin_top=6, margin_bottom=6)
        self._work_secs  = int(get_setting("pomo_work_mins",  "25")) * 60
        self._break_secs = int(get_setting("pomo_break_mins",  "5")) * 60
        self._secs_left = self._work_secs
        self._running   = False
        self._mode      = "work"
        self._session   = 1
        self._source_id = None

        # Left: mode + session
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._mode_lbl    = Gtk.Label(label="Work", xalign=0)
        self._mode_lbl.add_css_class("caption")
        self._session_lbl = Gtk.Label(label="Session 1", xalign=0)
        self._session_lbl.add_css_class("caption"); self._session_lbl.add_css_class("dim-label")
        left.append(self._mode_lbl); left.append(self._session_lbl)
        self.append(left)
        self.append(Gtk.Box(hexpand=True))  # spacer

        # Centre: countdown
        self._time_lbl = Gtk.Label()
        self._time_lbl.add_css_class("title-2")
        self._refresh_display()
        self.append(self._time_lbl)
        self.append(Gtk.Box(hexpand=True))  # spacer

        # Right: controls
        self._start_btn = Gtk.Button(label="Start")
        self._start_btn.add_css_class("suggested-action")
        self._start_btn.connect("clicked", self._on_start_pause)
        skip_btn = Gtk.Button(label="Skip")
        skip_btn.add_css_class("flat")
        skip_btn.connect("clicked", self._on_skip)
        reset_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        reset_btn.add_css_class("flat"); reset_btn.set_tooltip_text("Reset")
        reset_btn.connect("clicked", self._on_reset)
        self.append(self._start_btn); self.append(skip_btn); self.append(reset_btn)

        self.connect("destroy", self._cleanup)

    def _refresh_display(self):
        m, s = divmod(self._secs_left, 60)
        self._time_lbl.set_markup(f"<b>{m:02d}:{s:02d}</b>")

    def _tick(self):
        if not self._running:
            return GLib.SOURCE_REMOVE
        self._secs_left -= 1
        self._refresh_display()
        if self._secs_left <= 0:
            self._complete()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _complete(self):
        self._running = False; self._source_id = None
        self._start_btn.set_label("Start")
        if self._mode == "work":
            db_record_pomodoro()           # log completed work session
            self._mode = "break"; self._secs_left = self._break_secs
            self._mode_lbl.set_text("Break")
        else:
            self._mode = "work"; self._session += 1; self._secs_left = self._work_secs
            self._mode_lbl.set_text("Work")
            self._session_lbl.set_text(f"Session {self._session}")
        self._refresh_display()

    def _on_start_pause(self, _):
        if self._running:
            self._running = False
            if self._source_id:
                GLib.source_remove(self._source_id); self._source_id = None
            self._start_btn.set_label("Resume")
        else:
            self._running   = True
            self._start_btn.set_label("Pause")
            self._source_id = GLib.timeout_add(1000, self._tick)

    def _on_skip(self, _):
        self._running = False
        if self._source_id:
            GLib.source_remove(self._source_id); self._source_id = None
        self._secs_left = 0; self._complete()

    def _on_reset(self, _):
        self._running = False
        if self._source_id:
            GLib.source_remove(self._source_id); self._source_id = None
        self._secs_left = self._work_secs if self._mode == "work" else self._break_secs
        self._start_btn.set_label("Start"); self._refresh_display()

    def _cleanup(self, _):
        self._running = False
        if self._source_id:
            GLib.source_remove(self._source_id); self._source_id = None


class ShiftDatesDialog(Adw.Window):
    def __init__(self, parent, pid, on_save=None):
        super().__init__(
            title="Push dates ahead",
            modal=True, transient_for=parent,
            default_width=360, default_height=260, resizable=False,
        )
        self._pid = pid; self._on_save = on_save

        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                      margin_top=16, margin_bottom=24, margin_start=18, margin_end=18)

        grp = Adw.PreferencesGroup(title="Shift all goal and task dates forward")

        # Days spin button
        days_row = Adw.ActionRow(title="Amount")
        self._spin = Gtk.SpinButton.new_with_range(1, 365, 1)
        self._spin.set_value(7)
        self._spin.set_valign(Gtk.Align.CENTER)
        days_row.add_suffix(self._spin)
        grp.add(days_row)

        # Unit dropdown
        unit_row = Adw.ActionRow(title="Unit")
        self._unit = Gtk.DropDown.new_from_strings(["days", "weeks", "months"])
        self._unit.set_valign(Gtk.Align.CENTER)
        unit_row.add_suffix(self._unit)
        grp.add(unit_row)

        box.append(grp)

        btn = Gtk.Button(label="Shift all dates")
        btn.add_css_class("suggested-action"); btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", self._do_shift)
        box.append(btn)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(box)
        tv.set_content(scroll)
        self.set_content(tv)

    def _do_shift(self, _):
        amount = int(self._spin.get_value())
        unit_idx = self._unit.get_selected()
        units = ["days", "weeks", "months"]
        unit = units[unit_idx]
        if unit == "weeks":
            delta_days = amount * 7
        elif unit == "months":
            delta_days = amount * 30
        else:
            delta_days = amount
        delta = timedelta(days=delta_days)

        def _shift_date(ds):
            if not ds:
                return ds
            try:
                return (datetime.strptime(ds, "%Y-%m-%d").date() + delta).isoformat()
            except ValueError:
                return ds

        with get_db() as c:
            for g in c.execute(
                "SELECT id, start_date, end_date FROM goal WHERE project_id=?", (self._pid,)
            ).fetchall():
                new_start = _shift_date(g["start_date"])
                new_end   = _shift_date(g["end_date"])
                c.execute("UPDATE goal SET start_date=?, end_date=? WHERE id=?",
                          (new_start, new_end, g["id"]))
            for t in c.execute(
                "SELECT id, due_date FROM todo WHERE project_id=? AND due_date!=''", (self._pid,)
            ).fetchall():
                new_due = _shift_date(t["due_date"])
                c.execute("UPDATE todo SET due_date=? WHERE id=?", (new_due, t["id"]))

        if self._on_save:
            self._on_save()
        self.close()


class ProjectDetailView(Gtk.Box):
    def __init__(self, pid, window, on_back=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._pid = pid
        self._win = window
        self._on_back = on_back or window.show_home
        self._project = db_project(pid)
        self._list_mode = False   # False = grid tiles, True = compact list

        self._nav = Adw.NavigationView()
        self._nav.connect("popped", lambda _nav, _page: GLib.idle_add(self._rebuild_tiles))

        # Escape / Alt+Left → pop section back to dashboard
        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.MANAGED)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_Escape, 0),
            Gtk.CallbackAction.new(lambda *_: self._nav.pop() or True),
        ))
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_Left, Gdk.ModifierType.ALT_MASK),
            Gtk.CallbackAction.new(lambda *_: self._nav.pop() or True),
        ))
        self.add_controller(sc)

        self._dash_page = self._make_dash_page()
        self._nav.add(self._dash_page)
        self.append(self._nav)

    # ── Dashboard ─────────────────────────────────────────────

    def _make_dash_page(self):
        p = self._project
        page = Adw.NavigationPage(title=p["name"] if p else "Project")
        tv = Adw.ToolbarView()

        hdr = Adw.HeaderBar()
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_btn.add_css_class("flat"); edit_btn.set_tooltip_text("Edit project")
        edit_btn.connect("clicked", self._on_edit)
        hdr.pack_end(edit_btn)

        # Grid ↔ List toggle
        self._view_btn = Gtk.ToggleButton()
        self._view_btn.set_icon_name("view-list-symbolic")
        self._view_btn.set_tooltip_text("Switch to list view")
        self._view_btn.add_css_class("flat")
        self._view_btn.connect("toggled", self._on_view_toggle)
        hdr.pack_end(self._view_btn)

        # Export button
        export_btn = Gtk.Button(icon_name="document-send-symbolic")
        export_btn.add_css_class("flat"); export_btn.set_tooltip_text("Export as Markdown")
        export_btn.connect("clicked", self._do_export)
        hdr.pack_end(export_btn)

        # Shift dates button
        shift_btn = Gtk.Button(icon_name="media-skip-forward-symbolic")
        shift_btn.add_css_class("flat"); shift_btn.set_tooltip_text("Push all dates forward")
        shift_btn.connect("clicked", lambda _: ShiftDatesDialog(
            self._win, self._pid, on_save=self._rebuild_tiles
        ).present())
        hdr.pack_end(shift_btn)

        home_btn = Gtk.Button(icon_name="go-previous-symbolic")
        home_btn.add_css_class("flat")
        home_btn.set_tooltip_text("Back to overview")
        home_btn.connect("clicked", lambda _: self._on_back())
        hdr.pack_start(home_btn)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat"); del_btn.add_css_class("destructive-action")
        del_btn.set_tooltip_text("Delete project")
        del_btn.connect("clicked", self._on_delete)
        hdr.pack_start(del_btn)
        tv.add_top_bar(hdr)


        if p and p["description"]:
            try:
                banner = Adw.Banner(title=p["description"])
                banner.set_revealed(True)
                tv.add_top_bar(banner)
            except AttributeError:
                pass

        scroll = Gtk.ScrolledWindow(vexpand=True)
        self._tiles_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._build_tiles()
        scroll.set_child(self._tiles_box)
        tv.set_content(scroll)
        page.set_child(tv)
        return page

    def _build_tiles(self):
        clear_box(self._tiles_box)
        pid = self._pid

        todos    = db_todos(pid)
        done_t   = sum(1 for t in todos if t["done"])
        goals    = db_goals(pid)
        done_g   = sum(1 for g in goals if g["done"])
        notes    = db_notes(pid)
        files    = db_files(pid)
        playlist = db_playlist_items(pid)

        def sub(count, label, done=None):
            if count == 0:
                return "Nothing yet"
            if done is not None:
                left = count - done
                return f"{left} left · {done} done" if left else f"All {count} done ✓"
            return f"{count} {label}"

        # Tag count across ALL item types
        tag_set = set()
        for it in all_tagged_items(pid):
            tag_set.update(get_tags(it["tags"]))

        pl_sub = (f"{len(playlist)} track{'s' if len(playlist) != 1 else ''}"
                  if playlist else "No tracks yet")

        sections = [
            ("checkbox-checked-symbolic", "To-do list",
             sub(len(todos), "tasks", done_t),
             self._open_todos),
            ("starred-symbolic",          "Goals",
             sub(len(goals), "goals", done_g),
             self._open_goals),
            ("tag-symbolic",              "Labels",
             f"{len(tag_set)} label{'s' if len(tag_set) != 1 else ''} in use" if tag_set else "No labels yet",
             self._open_tags),
            ("document-new-symbolic",     "Notes",
             sub(len(notes), "notes"),
             self._open_notes),
            ("folder-open-symbolic",      "Files",
             sub(len(files), "linked"),
             self._open_files),
            ("audio-x-generic-symbolic",  "Focus Playlist",
             pl_sub,
             self._open_playlist),
        ]

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                        margin_top=18, margin_bottom=18,
                        margin_start=18, margin_end=18)

        if self._list_mode:
            grp = Adw.PreferencesGroup()
            for icon, title, subtitle, cb in sections:
                row = Adw.ActionRow(title=title, subtitle=subtitle)
                img = Gtk.Image(icon_name=icon)
                img.set_pixel_size(20)
                img.add_css_class("accent")
                row.add_prefix(img)
                chev = Gtk.Image(icon_name="go-next-symbolic")
                chev.add_css_class("dim-label")
                row.add_suffix(chev)
                row.set_activatable(True)
                row.connect("activated", lambda _, c=cb: c())
                grp.add(row)
            outer.append(grp)
        else:
            for i in range(0, len(sections), 3):
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                  spacing=12, homogeneous=True)
                for icon, title, subtitle, cb in sections[i:i+3]:
                    row_box.append(self._make_tile(icon, title, subtitle, cb))
                outer.append(row_box)

        # ── Pinned notes pinboard ──────────────────────────────
        pinned = [n for n in notes if n["pinned"]][:3]
        if pinned:
            pin_grp = Adw.PreferencesGroup(title="📌 Pinned notes")
            view_btn = Gtk.Button(label="See all notes")
            view_btn.add_css_class("flat")
            view_btn.connect("clicked", lambda _: self._open_notes())
            pin_grp.set_header_suffix(view_btn)
            for n in pinned:
                snippet = n["content"][:100].replace("\n", " ")
                if len(n["content"]) > 100:
                    snippet += "…"
                prow = Adw.ActionRow(title=snippet, subtitle=n["created_date"])
                prow.set_title_lines(2)
                prow.set_activatable(True)
                n_snap = dict(n)
                prow.connect("activated", lambda _, ns=n_snap: self._open_note_edit(ns))
                add_dblclick(prow, lambda ns=n_snap: self._open_note_edit(ns))
                pin_grp.add(prow)
            outer.append(pin_grp)

        self._tiles_box.append(outer)

    def _make_tile(self, icon_name, title, subtitle, callback):
        btn = Gtk.Button()
        btn.add_css_class("card")
        btn.set_hexpand(True)
        btn.connect("clicked", lambda _: callback())

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                        margin_top=24, margin_bottom=24,
                        margin_start=12, margin_end=12)
        inner.set_halign(Gtk.Align.CENTER)

        img = Gtk.Image(icon_name=icon_name)
        img.set_pixel_size(40)
        img.add_css_class("accent")
        inner.append(img)

        lbl = Gtk.Label(label=title)
        lbl.add_css_class("heading")
        inner.append(lbl)

        sub = Gtk.Label(label=subtitle)
        sub.add_css_class("dim-label")
        sub.add_css_class("caption")
        inner.append(sub)

        btn.set_child(inner)
        return btn

    def _on_view_toggle(self, btn):
        self._list_mode = btn.get_active()
        btn.set_icon_name("view-app-grid-symbolic" if self._list_mode else "view-list-symbolic")
        btn.set_tooltip_text("Switch to grid view" if self._list_mode else "Switch to list view")
        self._build_tiles()

    def _rebuild_tiles(self):
        self._project = db_project(self._pid)
        self._build_tiles()

    # ── Section navigation ─────────────────────────────────────

    def _push(self, title, widget, add_cb=None):
        hdr_widgets = []
        if add_cb:
            add_btn = Gtk.Button(icon_name="list-add-symbolic")
            add_btn.add_css_class("suggested-action")
            add_btn.add_css_class("circular")
            add_btn.connect("clicked", lambda _: add_cb())
            hdr_widgets.append(add_btn)
        self._nav.push(section_page(title, widget, hdr_widgets or None))

    def _open_todos(self):
        self._push("To-do list", TodosView(self._pid, self._win))

    def _open_goals(self):
        try:
            self._push("Goals", GoalsView(self._pid, self._win, push_fn=self._push))
        except Exception as exc:
            import traceback, traceback as tb
            traceback.print_exc()
            toast = Adw.Toast(title=f"Goals error: {exc}", timeout=10)
            self._win._toast_overlay.add_toast(toast)

    def _open_tags(self):
        self._push("Labels", TagsView(self._pid, self._win))

    def _open_notes(self):
        view = NotesView(self._pid, self._win, push_fn=self._push, pop_fn=self._nav.pop)
        self._push("Notes", view)

    def _open_note_edit(self, note):
        self._push(
            note["content"][:30].replace("\n", " "),
            NoteEditView(self._pid, self._win, note=note, on_save=self._rebuild_tiles))

    def _open_files(self):
        view = FilesView(self._pid, self._win)
        self._push("Files", view, add_cb=lambda: view._pick_file(None))

    def _open_playlist(self):
        proj_name = self._project["name"] if self._project else ""
        view = PlaylistView(self._pid, self._win, project_name=proj_name)
        self._push("Focus Playlist", view)

    def _open_section(self, section):
        """Navigate directly into a named section (used by homepage alerts)."""
        dispatch = {
            "tasks":    self._open_todos,
            "goals":    self._open_goals,
            "notes":    self._open_notes,
            "playlist": self._open_playlist,
        }
        fn = dispatch.get(section)
        if fn:
            fn()

    # ── Save as template ──────────────────────────────────────

    def _save_as_template(self, _):
        p = self._project
        todos = [t for t in db_todos(self._pid) if not t["done"]]
        goals = db_goals(self._pid)
        with get_db() as c:
            milestones = c.execute(
                "SELECT * FROM milestone WHERE project_id=? ORDER BY start_date",
                (self._pid,)).fetchall()

        dialog = Adw.Window(title="Save as Template", modal=True,
                            transient_for=self._win, default_width=440,
                            default_height=560, resizable=True)
        tv = Adw.ToolbarView(); tv.add_top_bar(Adw.HeaderBar())
        scroll = Gtk.ScrolledWindow(vexpand=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)
        scroll.set_child(box); tv.set_content(scroll)

        name_grp = Adw.PreferencesGroup()
        name_row = Adw.EntryRow(title="Template name")
        name_row.set_text((p["name"] + " template") if p else "Project template")
        name_grp.add(name_row)
        box.append(name_grp)

        task_checks = []
        goal_checks = []
        ms_checks   = []

        def _make_check_group(title, items, label_fn, checks_list):
            if not items:
                return
            grp = Adw.PreferencesGroup(title=title)
            for item in items:
                cb = Gtk.CheckButton(active=True)
                cb.set_valign(Gtk.Align.CENTER)
                row = Adw.ActionRow(title=label_fn(item))
                row.set_activatable_widget(cb)
                row.add_prefix(cb)
                checks_list.append((cb, item))
                grp.add(row)
            box.append(grp)

        _make_check_group(
            "Tasks (undone)", todos,
            lambda t: safe_col(t, "text") or "",
            task_checks)
        _make_check_group(
            "Goals", goals,
            lambda g: safe_col(g, "text") or "",
            goal_checks)
        _make_check_group(
            "Milestones", milestones,
            lambda m: safe_col(m, "title") or "",
            ms_checks)

        def _do_save(_):
            tname = name_row.get_text().strip() or "Project template"
            sel_tasks = [item for cb, item in task_checks if cb.get_active()]
            sel_goals = [item for cb, item in goal_checks if cb.get_active()]
            sel_ms    = [item for cb, item in ms_checks   if cb.get_active()]
            with get_db() as c:
                c.execute(
                    "INSERT INTO project_template (name, description, color, emoji, builtin) "
                    "VALUES (?,?,?,?,0)",
                    (tname, safe_col(p,"description") if p else "",
                     p["color"] if p else "#4fa8c4",
                     safe_col(p,"emoji") if p else ""))
                tid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                for t in sel_tasks:
                    c.execute(
                        "INSERT INTO pt_todo (template_id, text, priority, tags, recur_days) "
                        "VALUES (?,?,?,?,?)",
                        (tid, t["text"], safe_col(t,"priority") or "normal",
                         safe_col(t,"tags") or "", int(safe_col(t,"recur_days") or 0)))
                for g in sel_goals:
                    goal_text = safe_col(g, "text") or ""
                    c.execute(
                        "INSERT INTO pt_goal (template_id, text, tags) VALUES (?,?,?)",
                        (tid, goal_text, safe_col(g,"tags") or ""))
                for m in sel_ms:
                    try:
                        ms_start_d = date.fromisoformat(m["start_date"])
                        ms_end_d   = date.fromisoformat(m["end_date"])
                        offset = (ms_start_d - date.today()).days
                        dur    = max(1, (ms_end_d - ms_start_d).days)
                    except Exception:
                        offset, dur = 0, 7
                    c.execute(
                        "INSERT INTO pt_milestone (template_id, title, day_offset, duration_days) "
                        "VALUES (?,?,?,?)",
                        (tid, safe_col(m,"title") or "", offset, dur))
            dialog.close()

        save_btn = Gtk.Button(label="Save template", margin_top=6)
        save_btn.add_css_class("suggested-action"); save_btn.add_css_class("pill")
        save_btn.set_halign(Gtk.Align.CENTER)
        save_btn.connect("clicked", _do_save)
        box.append(save_btn)
        dialog.set_content(tv); dialog.present()

    # ── Edit / delete ──────────────────────────────────────────

    def _on_edit(self, _):
        def saved(new_pid=None):
            self._project = db_project(self._pid)
            self._win.refresh_projects()
            # Rebuild the dashboard page in-place so description/name update immediately
            new_page = self._make_dash_page()
            self._nav.replace([new_page])
            self._dash_page = new_page
        ProjectDialog(self._win, project=self._project, on_save=saved).present()

    def _do_export(self, _):
        content  = _generate_markdown(self._pid)
        p        = db_project(self._pid)
        safe_name = re.sub(r"[^\w\s-]", "", p["name"] if p else "project").strip()
        filename  = f"{safe_name or 'project'}.md"
        if hasattr(Gtk, "FileDialog"):
            dialog = Gtk.FileDialog.new()
            dialog.set_title("Export as Markdown")
            dialog.set_initial_name(filename)
            # PyGObject async: callback receives (source, result) — pass content via closure
            dialog.save(self._win, None, lambda d, r, md=content: self._on_export_finish(d, r, md))
        else:
            chooser = Gtk.FileChooserNative(
                title="Export as Markdown",
                transient_for=self._win,
                action=Gtk.FileChooserAction.SAVE,
                accept_label="Export",
                cancel_label="Cancel",
            )
            chooser.set_current_name(filename)
            chooser.connect("response", lambda c, r, md=content: self._on_export_native(c, r, md))
            chooser.show()
            self._export_chooser = chooser  # prevent GC

    def _on_export_finish(self, dialog, result, content):
        try:
            gfile = dialog.save_finish(result)
            path  = gfile.get_path() if gfile else None
            if path:
                with open(path, "w", encoding="utf-8") as fp:
                    fp.write(content)
        except Exception:
            pass

    def _on_export_native(self, chooser, response, content):
        if response == Gtk.ResponseType.ACCEPT:
            gfile = chooser.get_file()
            if gfile:
                path = gfile.get_path()
                if path:
                    with open(path, "w", encoding="utf-8") as fp:
                        fp.write(content)

    def _on_delete(self, _):
        name = self._project["name"] if self._project else "this project"
        try:
            dialog = Adw.AlertDialog(
                heading="Delete project?",
                body=f'"{name}" and all its milestones, tasks, goals, notes, and files will be permanently deleted.',
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("delete", "Delete")
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            dialog.connect("response", lambda d, r: self._confirm_delete() if r == "delete" else None)
            dialog.present(self._win)
        except AttributeError:
            dialog = Gtk.MessageDialog(
                transient_for=self._win, modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.CANCEL,
                text="Delete project?",
            )
            dialog.format_secondary_text(
                f'"{name}" and all its data will be permanently deleted.')
            dialog.add_button("Delete", Gtk.ResponseType.ACCEPT)
            dialog.set_default_response(Gtk.ResponseType.CANCEL)
            def _resp(d, r):
                d.destroy()
                if r == Gtk.ResponseType.ACCEPT:
                    self._confirm_delete()
            dialog.connect("response", _resp)
            dialog.present()

    def _confirm_delete(self):
        with get_db() as c:
            c.execute("DELETE FROM project WHERE id=?", (self._pid,))
        self._win.refresh_projects()
        self._win.show_home()


# ══════════════════════════════════════════════════════
# Project Templates Dialog
# ══════════════════════════════════════════════════════

class CustomTemplateDialog(Adw.Window):
    """Build a project template from scratch."""
    def __init__(self, parent, win, on_save=None):
        super().__init__(title="New Custom Template", modal=True, transient_for=parent,
                         default_width=500, default_height=620, resizable=True)
        self._win = win
        self._on_save = on_save
        self._ms_entries   = []
        self._task_entries = []
        self._goal_entries = []

        tv = Adw.ToolbarView(); tv.add_top_bar(Adw.HeaderBar())
        scroll = Gtk.ScrolledWindow(vexpand=True)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                        margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)
        scroll.set_child(outer); tv.set_content(scroll); self.set_content(tv)

        info_grp = Adw.PreferencesGroup()
        self._name_row  = Adw.EntryRow(title="Template name")
        self._emoji_row = Adw.EntryRow(title="Emoji  (optional)")
        info_grp.add(self._name_row); info_grp.add(self._emoji_row)
        outer.append(info_grp)

        def _section_header(label_text, add_cb, margin_top=8):
            hdr = Gtk.Box(spacing=8, margin_top=margin_top)
            lbl = Gtk.Label(label=label_text, xalign=0, hexpand=True)
            lbl.add_css_class("heading")
            btn = Gtk.Button(icon_name="list-add-symbolic")
            btn.add_css_class("flat"); btn.connect("clicked", lambda _: add_cb())
            hdr.append(lbl); hdr.append(btn)
            return hdr

        self._ms_grp   = Adw.PreferencesGroup()
        self._task_grp = Adw.PreferencesGroup()
        self._goal_grp = Adw.PreferencesGroup()

        outer.append(_section_header("Milestones", self._add_ms_row, margin_top=4))
        hint = Gtk.Label(
            label="Day offset = days from project start.  Duration = length in days.",
            xalign=0)
        hint.add_css_class("caption"); hint.add_css_class("dim-label")
        outer.append(hint)
        outer.append(self._ms_grp)

        outer.append(_section_header("Tasks", self._add_task_row))
        outer.append(self._task_grp)

        outer.append(_section_header("Goals", self._add_goal_row))
        outer.append(self._goal_grp)

        save_btn = Gtk.Button(label="Save template", margin_top=12)
        save_btn.add_css_class("suggested-action"); save_btn.add_css_class("pill")
        save_btn.set_halign(Gtk.Align.CENTER)
        save_btn.connect("clicked", self._save)
        outer.append(save_btn)

        self._add_ms_row(); self._add_task_row(); self._add_goal_row()

    def _add_ms_row(self):
        row = Adw.ActionRow()
        title_e  = Gtk.Entry(placeholder_text="Milestone name", hexpand=True)
        title_e.set_valign(Gtk.Align.CENTER)
        offset_e = Gtk.Entry(placeholder_text="Offset", width_chars=5)
        offset_e.set_text(str(len(self._ms_entries) * 7))
        offset_e.set_valign(Gtk.Align.CENTER)
        dur_e    = Gtk.Entry(placeholder_text="Days", width_chars=5)
        dur_e.set_text("7"); dur_e.set_valign(Gtk.Align.CENTER)
        del_btn  = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat"); del_btn.add_css_class("destructive-action")
        del_btn.set_valign(Gtk.Align.CENTER)
        entry = (title_e, offset_e, dur_e, row)
        del_btn.connect("clicked", lambda _, e=entry: self._remove_ms(e))
        row.add_prefix(title_e); row.add_suffix(offset_e)
        row.add_suffix(dur_e);   row.add_suffix(del_btn)
        self._ms_entries.append(entry); self._ms_grp.add(row)

    def _remove_ms(self, entry):
        self._ms_entries = [e for e in self._ms_entries if e is not entry]
        self._ms_grp.remove(entry[3])

    def _add_task_row(self):
        row = Adw.ActionRow()
        text_e   = Gtk.Entry(placeholder_text="Task description", hexpand=True)
        text_e.set_valign(Gtk.Align.CENTER)
        pri_drop = Gtk.DropDown.new_from_strings(["Normal", "High", "Low"])
        pri_drop.set_valign(Gtk.Align.CENTER)
        del_btn  = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat"); del_btn.add_css_class("destructive-action")
        del_btn.set_valign(Gtk.Align.CENTER)
        entry = (text_e, pri_drop, row)
        del_btn.connect("clicked", lambda _, e=entry: self._remove_task(e))
        row.add_prefix(text_e); row.add_suffix(pri_drop); row.add_suffix(del_btn)
        self._task_entries.append(entry); self._task_grp.add(row)

    def _remove_task(self, entry):
        self._task_entries = [e for e in self._task_entries if e is not entry]
        self._task_grp.remove(entry[2])

    def _add_goal_row(self):
        row = Adw.ActionRow()
        text_e  = Gtk.Entry(placeholder_text="Goal description", hexpand=True)
        text_e.set_valign(Gtk.Align.CENTER)
        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.add_css_class("flat"); del_btn.add_css_class("destructive-action")
        del_btn.set_valign(Gtk.Align.CENTER)
        entry = (text_e, row)
        del_btn.connect("clicked", lambda _, e=entry: self._remove_goal(e))
        row.add_prefix(text_e); row.add_suffix(del_btn)
        self._goal_entries.append(entry); self._goal_grp.add(row)

    def _remove_goal(self, entry):
        self._goal_entries = [e for e in self._goal_entries if e is not entry]
        self._goal_grp.remove(entry[1])

    def _save(self, _):
        tname = self._name_row.get_text().strip()
        if not tname:
            self._name_row.add_css_class("error"); return
        self._name_row.remove_css_class("error")
        emoji = self._emoji_row.get_text().strip()
        with get_db() as c:
            c.execute(
                "INSERT INTO project_template (name, description, color, emoji, builtin) "
                "VALUES (?,?,?,?,0)", (tname, "", "#4fa8c4", emoji))
            tid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            for title_e, offset_e, dur_e, _ in self._ms_entries:
                title = title_e.get_text().strip()
                if not title: continue
                try: offset = int(offset_e.get_text().strip())
                except ValueError: offset = 0
                try: dur = max(1, int(dur_e.get_text().strip()))
                except ValueError: dur = 7
                c.execute(
                    "INSERT INTO pt_milestone (template_id, title, day_offset, duration_days) "
                    "VALUES (?,?,?,?)", (tid, title, offset, dur))
            for text_e, pri_drop, _ in self._task_entries:
                text = text_e.get_text().strip()
                if not text: continue
                pri = ["normal", "high", "low"][pri_drop.get_selected()]
                c.execute(
                    "INSERT INTO pt_todo (template_id, text, priority) VALUES (?,?,?)",
                    (tid, text, pri))
            for text_e, _ in self._goal_entries:
                text = text_e.get_text().strip()
                if not text: continue
                c.execute(
                    "INSERT INTO pt_goal (template_id, text) VALUES (?,?)",
                    (tid, text))
        if self._on_save: self._on_save()
        self.close()


class ProjectTemplatesDialog(Adw.Window):
    def __init__(self, win):
        super().__init__(title="Project Templates", modal=True, transient_for=win,
                         default_width=540, default_height=520)
        self._win = win
        tv = Adw.ToolbarView()
        hdr = Adw.HeaderBar()
        new_btn = Gtk.Button(label="New custom")
        new_btn.add_css_class("suggested-action")
        new_btn.connect("clicked", lambda _: CustomTemplateDialog(
            self, self._win, on_save=self._build).present())
        hdr.pack_end(new_btn)
        tv.add_top_bar(hdr)
        scroll = Gtk.ScrolledWindow(vexpand=True,
                                    margin_top=12, margin_bottom=12,
                                    margin_start=18, margin_end=18)
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        scroll.set_child(self._box)
        tv.set_content(scroll); self.set_content(tv)
        self._build()

    def _build(self):
        clear_box(self._box)
        all_tpl = db_project_templates()
        builtin  = [t for t in all_tpl if safe_col(t, "builtin")]
        user_tpl = [t for t in all_tpl if not safe_col(t, "builtin")]

        if not all_tpl:
            sp = Adw.StatusPage(title="No templates yet",
                                description="Save a project as a template using the save icon, or click 'New custom'",
                                icon_name="document-open-recent-symbolic")
            sp.set_vexpand(True); self._box.append(sp); return

        if builtin:
            grp = Adw.PreferencesGroup(title="Example templates")
            for t in builtin: self._add_row(grp, t, deletable=False)
            self._box.append(grp)

        if user_tpl:
            grp = Adw.PreferencesGroup(title="My templates")
            for t in user_tpl: self._add_row(grp, t, deletable=True)
            self._box.append(grp)

    def _add_row(self, grp, t, deletable):
        row = Adw.ActionRow(title=t["name"])
        emoji = safe_col(t, "emoji") or ""
        if emoji: row.set_title(f"{emoji}  {t['name']}")
        todos, goals, ms = db_pt_items(t["id"])
        parts = []
        if ms:    parts.append(f"{len(ms)} milestone{'s' if len(ms)!=1 else ''}")
        if todos: parts.append(f"{len(todos)} task{'s' if len(todos)!=1 else ''}")
        if goals: parts.append(f"{len(goals)} goal{'s' if len(goals)!=1 else ''}")
        row.set_subtitle("  ·  ".join(parts) if parts else "Empty template")
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("flat"); apply_btn.set_valign(Gtk.Align.CENTER)
        apply_btn.connect("clicked", lambda _, tmpl=t: self._apply(tmpl))
        row.add_suffix(apply_btn)
        if deletable:
            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.add_css_class("flat"); del_btn.add_css_class("destructive-action")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect("clicked", lambda _, tid=t["id"]: self._delete(tid))
            row.add_suffix(del_btn)
        grp.add(row)

    def _apply(self, tmpl):
        todos_t, goals_t, ms_t = db_pt_items(tmpl["id"])
        dlg = Adw.Window(title="Create project from template", modal=True,
                         transient_for=self, default_width=400, resizable=False)
        tv = Adw.ToolbarView(); tv.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)
        grp = Adw.PreferencesGroup(title="New project details")
        name_row = Adw.EntryRow(title="Project name")
        name_row.set_text(tmpl["name"])
        grp.add(name_row)
        start_row = Adw.EntryRow(title="Start date  (+Nd / +Nw / +Nm)")
        start_row.set_text(date.today().isoformat())
        _wire_date_shortcut(start_row)
        grp.add(start_row)
        parts = []
        if ms_t:    parts.append(f"{len(ms_t)} milestone{'s' if len(ms_t)!=1 else ''}")
        if todos_t: parts.append(f"{len(todos_t)} task{'s' if len(todos_t)!=1 else ''}")
        if goals_t: parts.append(f"{len(goals_t)} goal{'s' if len(goals_t)!=1 else ''}")
        info = Adw.ActionRow(title="Template contents")
        info.set_subtitle("  ·  ".join(parts) if parts else "Empty")
        grp.add(info)
        box.append(grp)
        def _do_create(_):
            pname = name_row.get_text().strip() or tmpl["name"]
            start_text = expand_date_shortcut(start_row.get_text().strip())
            try:
                start = datetime.strptime(start_text, "%Y-%m-%d").date()
            except ValueError:
                start = date.today()
            with get_db() as c:
                c.execute(
                    "INSERT INTO project (name, status, description, color, emoji) VALUES (?,?,?,?,?)",
                    (pname, "active", safe_col(tmpl,"description") or "",
                     tmpl["color"], safe_col(tmpl,"emoji") or ""))
                pid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                for i, t in enumerate(todos_t):
                    c.execute(
                        "INSERT INTO todo (project_id,text,priority,tags,order_pos,recur_days) VALUES (?,?,?,?,?,?)",
                        (pid, t["text"], safe_col(t,"priority") or "normal",
                         safe_col(t,"tags") or "", i, int(safe_col(t,"recur_days") or 0)))
                for g in goals_t:
                    c.execute(
                        "INSERT INTO goal (project_id,text,tags) VALUES (?,?,?)",
                        (pid, g["text"], safe_col(g,"tags") or ""))
                for m in ms_t:
                    off = int(safe_col(m,"day_offset") or 0)
                    dur = max(1, int(safe_col(m,"duration_days") or 7))
                    ms_start = (start + timedelta(days=off)).isoformat()
                    ms_end   = (start + timedelta(days=off + dur)).isoformat()
                    c.execute(
                        "INSERT INTO milestone (project_id,title,start_date,end_date) VALUES (?,?,?,?)",
                        (pid, m["title"], ms_start, ms_end))
            dlg.close()
            self._win.refresh_projects(new_pid=pid)
            self.close()
        create_btn = Gtk.Button(label="Create project", margin_top=6)
        create_btn.add_css_class("suggested-action"); create_btn.add_css_class("pill")
        create_btn.set_halign(Gtk.Align.CENTER)
        create_btn.connect("clicked", _do_create)
        box.append(create_btn)
        tv.set_content(box); dlg.set_content(tv); dlg.present()

    def _delete(self, tid):
        with get_db() as c:
            c.execute("DELETE FROM project_template WHERE id=?", (tid,))
        self._build()


# ══════════════════════════════════════════════════════
# Focus Mode View
# ══════════════════════════════════════════════════════

class FocusModeView(Gtk.Box):
    """Focus mode — appearance depends on focus_level setting."""
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._win = win
        self._level = get_setting("focus_level", "extreme")
        if self._level == "extreme":
            self.set_valign(Gtk.Align.CENTER)
            self.set_halign(Gtk.Align.CENTER)
            self.set_spacing(24)
            self.set_margin_top(48); self.set_margin_bottom(48)
            self.set_margin_start(48); self.set_margin_end(48)
        else:
            self.set_margin_top(12); self.set_margin_bottom(24)
            self.set_margin_start(18); self.set_margin_end(18)
            self.set_spacing(16)
        self._build()

    # ── Extreme: single task ─────────────────────────────────────
    def _build(self):
        clear_box(self)
        if self._level == "focused":
            self._build_focused()
        else:
            self._build_extreme()

    def _build_extreme(self):
        best = None; best_score = -1
        for p in db_projects():
            for t in db_todos(p["id"]):
                if t["done"]: continue
                blocked_by = int(safe_col(t, "blocked_by") or 0)
                if blocked_by:
                    with get_db() as c:
                        b = c.execute("SELECT done FROM todo WHERE id=?", (blocked_by,)).fetchone()
                    if b and not b["done"]: continue
                score = {"high": 2, "normal": 1, "low": 0}.get(t["priority"] or "normal", 1)
                if score > best_score:
                    best = (t, p); best_score = score

        if not best:
            sp = Adw.StatusPage(title="Nothing to do!",
                                description="All tasks are done across every project",
                                icon_name="checkbox-checked-symbolic")
            self.append(sp); return

        task, proj = best
        proj_lbl = Gtk.Label(label=(f"{safe_col(proj,'emoji') or ''} {proj['name']}").strip())
        proj_lbl.add_css_class("dim-label"); proj_lbl.add_css_class("caption")
        self.append(proj_lbl)

        task_lbl = Gtk.Label(label=task["text"])
        task_lbl.add_css_class("title-1"); task_lbl.set_wrap(True)
        task_lbl.set_justify(Gtk.Justification.CENTER)
        task_lbl.set_max_width_chars(50)
        self.append(task_lbl)

        if task["priority"] == "high":
            pri_lbl = Gtk.Label(label="High priority")
            pri_lbl.add_css_class("error"); pri_lbl.add_css_class("caption")
            self.append(pri_lbl)

        btn_box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER, margin_top=12)
        done_btn = Gtk.Button(label="Mark done")
        done_btn.add_css_class("suggested-action"); done_btn.add_css_class("pill")
        done_btn.connect("clicked", lambda _, tid=task["id"]: self._complete(tid))
        skip_btn = Gtk.Button(label="Skip to next")
        skip_btn.add_css_class("flat"); skip_btn.add_css_class("pill")
        skip_btn.connect("clicked", lambda _: GLib.idle_add(self._build))
        btn_box.append(done_btn); btn_box.append(skip_btn)
        self.append(btn_box)

    # ── Focused: full-context but clean ──────────────────────────
    def _build_focused(self):
        today = date.today().isoformat()

        # Tasks due today + overdue, sorted by priority
        tasks = db_today_tasks()
        overdue   = [t for t in tasks if t["due_date"] < today]
        due_today = [t for t in tasks if t["due_date"] == today]

        if overdue:
            ov_grp = Adw.PreferencesGroup(title=f"Overdue  ({len(overdue)})")
            for t in overdue:
                row = Adw.ActionRow(title=safe_col(t, "text") or "")
                row.set_subtitle(safe_col(t, "project_name") or "")
                row.set_activatable(True)
                row.connect("activated", lambda _, pid=t["project_id"]:
                    self._win._open_project(pid, section="tasks"))
                pri = safe_col(t, "priority") or "normal"
                if pri == "high":
                    bar = Gtk.Box(); bar.set_size_request(4, -1)
                    bar.add_css_class("error"); bar.set_valign(Gtk.Align.FILL)
                    row.add_prefix(bar)
                ov_grp.add(row)
            self.append(ov_grp)

        if due_today:
            td_grp = Adw.PreferencesGroup(title=f"Due today  ({len(due_today)})")
            for t in due_today:
                row = Adw.ActionRow(title=safe_col(t, "text") or "")
                row.set_subtitle(safe_col(t, "project_name") or "")
                row.set_activatable(True)
                row.connect("activated", lambda _, pid=t["project_id"]:
                    self._win._open_project(pid, section="tasks"))
                td_grp.add(row)
            self.append(td_grp)

        # Active goals (not done, not future)
        all_goals = []
        for p in db_projects():
            for g in db_goals(p["id"]):
                st = compute_goal_status(g)
                if st in ("active", "overdue"):
                    all_goals.append((g, p))
        if all_goals:
            g_grp = Adw.PreferencesGroup(title=f"Active goals  ({len(all_goals)})")
            for g, p in all_goals[:8]:
                row = Adw.ActionRow(title=safe_col(g, "goal") or "")
                emoji = safe_col(p, "emoji") or ""
                row.set_subtitle((f"{emoji} {p['name']}").strip())
                row.set_activatable(True)
                row.connect("activated", lambda _, pid=p["id"]:
                    self._win._open_project(pid, section="goals"))
                if compute_goal_status(g) == "overdue":
                    row.add_css_class("error")
                g_grp.add(row)
            self.append(g_grp)

        # Near-due milestones (next 14 days)
        soon = date.today() + timedelta(days=14)
        ms_rows = []
        with get_db() as c:
            ms_rows = c.execute("""
                SELECT m.*, p.name as project_name, p.emoji as project_emoji
                FROM milestone m JOIN project p ON m.project_id=p.id
                WHERE m.end_date>=? AND m.end_date<=? AND (m.done IS NULL OR m.done=0)
                ORDER BY m.end_date ASC
            """, (today, soon.isoformat())).fetchall()
        if ms_rows:
            ms_grp = Adw.PreferencesGroup(title=f"Milestones due soon  ({len(ms_rows)})")
            for m in ms_rows:
                days_left = (date.fromisoformat(m["end_date"]) - date.today()).days
                due_lbl = f"{days_left}d" if days_left > 0 else "today"
                row = Adw.ActionRow(title=safe_col(m, "name") or "")
                emoji = safe_col(m, "project_emoji") or ""
                row.set_subtitle((f"{emoji} {m['project_name']}  ·  due {due_lbl}").strip())
                ms_grp.add(row)
            self.append(ms_grp)

        if not tasks and not all_goals and not ms_rows:
            sp = Adw.StatusPage(title="Clear schedule",
                                description="Nothing urgent — great time for deep work",
                                icon_name="checkbox-checked-symbolic")
            self.append(sp)

    def _complete(self, tid):
        today = date.today().isoformat()
        with get_db() as c:
            r = c.execute("SELECT * FROM todo WHERE id=?", (tid,)).fetchone()
            c.execute("UPDATE todo SET done=1, completed_date=? WHERE id=?", (today, tid))
            recur = int(safe_col(r, "recur_days") or 0)
            if recur > 0:
                due_back = (date.today() + timedelta(days=recur)).isoformat()
                c.execute("INSERT INTO todo (project_id,text,done,priority,tags,order_pos,completed_date,recur_days,blocked_by) VALUES (?,?,0,?,?,0,?,?,0)",
                          (r["project_id"], r["text"], safe_col(r,"priority") or "normal",
                           safe_col(r,"tags") or "", due_back, recur))
        GLib.idle_add(self._build)


TUTORIAL_TEXT = """\
PROJEX — KEYBOARD SHORTCUTS & HELP
═══════════════════════════════════════════════════════

NAVIGATION
  Ctrl+N    New item (task/goal/note in current view)
  Ctrl+S    Save and close current dialog / note editor
  Esc / ←   Go back (inside project navigation)

TASKS
  Ctrl+N    Open "New task" dialog
  Drag ⠿    Drag the handle to reorder active tasks
  Double-click row    Edit task
  Bulk mode    Click "Select" in header to multi-select

GOALS
  Ctrl+N    New goal dialog
  Double-click row    Open goal detail / summary
  Double-click Gantt bar    Jump to that goal

GANTT CHART
  Drag divider    Resize label column (reveal full names)
  Zoom slider    Scale the timeline horizontally
  Colors dropdown    Switch between jewel-tone palette and system theme
  Double-click bar    Navigate to that goal

NOTES
  Ctrl+S    Save note and return to notes list
  Click star    Pin/unpin note

GENERAL
  Pomodoro ⏱    Start/stop 25-min focus timer in sidebar
  Push dates ⏭    Shift all task/goal dates forward in project header
  Right-click project    Move project to a group
"""

class NowPlayingBar(Gtk.Box):
    """Compact MPRIS now-playing panel for the sidebar bottom."""
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._player = None
        self._current_state = None

        self._rev = Gtk.Revealer(reveal_child=False)
        self._rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0,
                        margin_start=6, margin_end=6, margin_top=4, margin_bottom=4)
        inner.add_css_class("card")

        ctrl = Gtk.Box(spacing=0)
        prev_btn = Gtk.Button(icon_name="media-skip-backward-symbolic")
        prev_btn.add_css_class("flat"); prev_btn.set_valign(Gtk.Align.CENTER)
        prev_btn.connect("clicked", lambda _: self._action("Previous"))
        self._play_btn = Gtk.Button(icon_name="media-playback-start-symbolic")
        self._play_btn.add_css_class("flat"); self._play_btn.set_valign(Gtk.Align.CENTER)
        self._play_btn.connect("clicked", lambda _: self._action("PlayPause"))
        next_btn = Gtk.Button(icon_name="media-skip-forward-symbolic")
        next_btn.add_css_class("flat"); next_btn.set_valign(Gtk.Align.CENTER)
        next_btn.connect("clicked", lambda _: self._action("Next"))
        ctrl.append(prev_btn); ctrl.append(self._play_btn); ctrl.append(next_btn)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                       margin_start=4, hexpand=True)
        info.set_valign(Gtk.Align.CENTER)
        info.set_tooltip_text("Click to open player")
        info.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self._title_lbl = Gtk.Label(xalign=0)
        self._title_lbl.add_css_class("caption")
        self._artist_lbl = Gtk.Label(xalign=0)
        self._artist_lbl.add_css_class("caption"); self._artist_lbl.add_css_class("dim-label")
        info.append(self._title_lbl); info.append(self._artist_lbl)
        gc = Gtk.GestureClick.new()
        gc.set_button(1)
        gc.connect("pressed", lambda _g, _n, _x, _y: mpris_raise(self._player) if self._player else None)
        info.add_controller(gc)

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("flat"); add_btn.set_valign(Gtk.Align.CENTER)
        add_btn.set_tooltip_text("Add to playlist")
        add_btn.connect("clicked", lambda _: self._add_to_playlist())

        inner.append(ctrl); inner.append(info); inner.append(add_btn)
        self._rev.set_child(inner)
        self.append(self._rev)

        self._poll()
        GLib.timeout_add_seconds(3, self._poll)

    def _poll(self):
        players = mpris_get_players()
        if not players:
            self._player = None
            self._rev.set_reveal_child(False)
            return True
        best_name, best_state = None, None
        for p in players:
            s = mpris_get_state(p)
            if s and s["status"] == "Playing":
                best_name, best_state = p, s
                break
        if best_name is None:
            s = mpris_get_state(players[0])
            if s:
                best_name, best_state = players[0], s
        if best_name is None:
            self._rev.set_reveal_child(False)
            return True
        self._player = best_name
        self._current_state = best_state
        is_playing = best_state["status"] == "Playing"
        title  = (best_state["title"] or ("" if is_playing else "Nothing playing"))[:30]
        artist = (best_state["artist"] or "")[:28]
        self._title_lbl.set_label(title)
        self._artist_lbl.set_label(artist)
        self._play_btn.set_icon_name(
            "media-playback-pause-symbolic" if is_playing else "media-playback-start-symbolic"
        )
        self._rev.set_reveal_child(True)
        return True

    def _action(self, action):
        if self._player:
            mpris_action(self._player, action)
            GLib.timeout_add(400, self._poll)

    def _add_to_playlist(self):
        state = self._current_state
        if not state or not state.get("title"):
            return
        win = self.get_root()
        AddToPlaylistDialog(win, state).present()


class AddToPlaylistDialog(Adw.Window):
    """Choose an existing playlist or create a new one, then add the current track."""
    def __init__(self, parent, track_state):
        super().__init__(title="Add to Playlist", modal=True, transient_for=parent,
                         default_width=420, resizable=False)
        self._track = track_state

        tv = Adw.ToolbarView(); tv.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)
        tv.set_content(box); self.set_content(tv)

        # Track preview
        track_grp = Adw.PreferencesGroup(title="Track to add")
        track_row = Adw.ActionRow(title=track_state.get("title") or "Unknown title")
        parts = []
        if track_state.get("artist"): parts.append(track_state["artist"])
        if track_state.get("album"):  parts.append(track_state["album"])
        if parts: track_row.set_subtitle("  ·  ".join(parts))
        track_grp.add(track_row)
        box.append(track_grp)

        # Build playlist choices: existing playlists + "New playlist…"
        projects = [p for p in db_projects() if p["status"] != "archived"]
        # Each project has at most one playlist; include all projects as candidates
        existing = []  # (display_label, project_id)
        for p in projects:
            pl_name = db_playlist_name(p["id"], p["name"])
            emoji = safe_col(p, "emoji") or ""
            label = f"{pl_name}  —  {emoji} {p['name']}".strip()
            existing.append((label, p["id"]))

        dest_grp = Adw.PreferencesGroup(title="Choose playlist")

        # Combo row for existing playlists
        choice_labels = [lbl for lbl, _ in existing] + ["＋  New playlist under a project…"]
        self._choice_drop = Adw.ComboRow(title="Playlist")
        self._choice_drop.set_model(Gtk.StringList.new(choice_labels))
        self._choice_drop.set_selected(0)
        dest_grp.add(self._choice_drop)
        box.append(dest_grp)

        # "New playlist" section — revealed when last option selected
        self._new_grp = Adw.PreferencesGroup(title="New playlist")
        proj_labels = [f"{safe_col(p,'emoji') or ''} {p['name']}".strip() for p in projects]
        self._proj_drop = Adw.ComboRow(title="Project")
        self._proj_drop.set_model(Gtk.StringList.new(proj_labels))
        self._new_grp.add(self._proj_drop)
        self._new_name_row = Adw.EntryRow(title="Playlist name  (optional)")
        self._new_grp.add(self._new_name_row)
        self._new_grp.set_visible(False)
        box.append(self._new_grp)

        self._existing = existing
        self._projects = projects

        self._choice_drop.connect("notify::selected", self._on_choice)

        add_btn = Gtk.Button(label="Add to playlist", margin_top=4)
        add_btn.add_css_class("suggested-action"); add_btn.add_css_class("pill")
        add_btn.set_halign(Gtk.Align.CENTER)
        add_btn.connect("clicked", self._save)
        box.append(add_btn)

    def _on_choice(self, row, _):
        is_new = row.get_selected() == len(self._existing)
        self._new_grp.set_visible(is_new)

    def _save(self, _):
        sel = self._choice_drop.get_selected()
        is_new = sel == len(self._existing)

        if is_new:
            proj_idx = self._proj_drop.get_selected()
            if proj_idx >= len(self._projects):
                return
            project = self._projects[proj_idx]
            pid = project["id"]
            custom_name = self._new_name_row.get_text().strip()
            if custom_name:
                db_playlist_set_name(pid, custom_name)
        else:
            pid = self._existing[sel][1]

        title  = self._track.get("title") or ""
        artist = self._track.get("artist") or ""
        album  = self._track.get("album") or ""
        with get_db() as c:
            pos = c.execute(
                "SELECT COALESCE(MAX(position),0)+1 FROM playlist_item WHERE project_id=?",
                (pid,)).fetchone()[0]
            c.execute(
                "INSERT INTO playlist_item (project_id, title, artist, album, url, position) "
                "VALUES (?,?,?,?,?,?)",
                (pid, title, artist, album, "", pos))
        self.close()


class PlaylistItemDialog(Adw.Dialog):
    """Add or edit a focus playlist track."""
    def __init__(self, parent, pid, item=None, on_save=None):
        super().__init__(
            title="Add track" if item is None else "Edit track",
            content_width=420,
        )
        self._pid = pid; self._item = item; self._on_save = on_save

        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=20, margin_start=12, margin_end=12)

        grp = Adw.PreferencesGroup()
        self._title_row = Adw.EntryRow(title="Song title")
        if item:
            self._title_row.set_text(item["title"] or "")
        grp.add(self._title_row)

        self._artist_row = Adw.EntryRow(title="Artist")
        if item:
            self._artist_row.set_text(safe_col(item, "artist") or "")
        grp.add(self._artist_row)

        self._album_row = Adw.EntryRow(title="Album  (optional)")
        if item:
            self._album_row.set_text(safe_col(item, "album") or "")
        grp.add(self._album_row)

        self._url_row = Adw.EntryRow(title="Link  (optional — Spotify URI, URL…)")
        if item:
            self._url_row.set_text(safe_col(item, "url") or "")
        grp.add(self._url_row)
        box.append(grp)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action"); save_btn.add_css_class("pill")
        save_btn.connect("clicked", self._save)
        box.append(save_btn)

        if item:
            del_btn = Gtk.Button(label="Remove from playlist")
            del_btn.add_css_class("destructive-action"); del_btn.add_css_class("pill")
            del_btn.connect("clicked", self._delete)
            box.append(del_btn)

        tv.set_content(box)
        self.set_child(tv)

        # Ctrl+S saves
        sc = Gtk.ShortcutController()
        sc.set_scope(Gtk.ShortcutScope.MANAGED)
        sc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: (self._save(None), True)[1]),
        ))
        self.add_controller(sc)

    def _save(self, _):
        title = self._title_row.get_text().strip()
        if not title:
            return
        artist = self._artist_row.get_text().strip()
        album  = self._album_row.get_text().strip()
        url    = self._url_row.get_text().strip()
        with get_db() as c:
            if self._item:
                c.execute(
                    "UPDATE playlist_item SET title=?, artist=?, album=?, url=? WHERE id=?",
                    (title, artist, album, url, self._item["id"]))
            else:
                pos = c.execute(
                    "SELECT COALESCE(MAX(position),0) FROM playlist_item WHERE project_id=?",
                    (self._pid,)).fetchone()[0]
                c.execute(
                    "INSERT INTO playlist_item (project_id, title, artist, album, url, position)"
                    " VALUES (?,?,?,?,?,?)",
                    (self._pid, title, artist, album, url, pos + 1))
        self.close()
        if self._on_save:
            self._on_save()

    def _delete(self, _):
        def do_del():
            with get_db() as c:
                c.execute("DELETE FROM playlist_item WHERE id=?", (self._item["id"],))
            self.close()
            if self._on_save:
                self._on_save()
        _confirm_delete(self, "Remove track",
                        f'Remove "{self._item["title"]}" from playlist?', do_del)


class PlaylistView(Gtk.Box):
    """Per-project focus playlist."""
    def __init__(self, pid, win, project_name=""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                         margin_top=12, margin_bottom=12, margin_start=18, margin_end=18)
        self._pid = pid; self._win = win; self._project_name = project_name
        self._build()

    def _build(self):
        clear_box(self)
        items = db_playlist_items(self._pid)
        pl_name = db_playlist_name(self._pid, self._project_name)

        # ── Editable playlist name header ─────────────────────
        name_box = Gtk.Box(spacing=6)
        name_lbl = Gtk.Label(label=pl_name, xalign=0, hexpand=True)
        name_lbl.add_css_class("title-3")
        name_box.append(name_lbl)
        edit_name_btn = Gtk.Button(icon_name="document-edit-symbolic")
        edit_name_btn.add_css_class("flat"); edit_name_btn.set_valign(Gtk.Align.CENTER)
        edit_name_btn.set_tooltip_text("Rename playlist")
        edit_name_btn.connect("clicked", lambda _: self._rename_dialog(pl_name))
        name_box.append(edit_name_btn)
        self.append(name_box)

        tip = Gtk.Label(wrap=True, xalign=0)
        tip.set_markup(
            "<i><span size='small'>Music to listen to while you work on this project. "
            "Add a link and tap the open button to launch your music player.</span></i>")
        tip.add_css_class("dim-label")
        self.append(tip)

        if not items:
            sp = Adw.StatusPage(
                title="Empty playlist",
                description="Hit + to add your first track",
                icon_name="audio-x-generic-symbolic",
            )
            sp.set_vexpand(False)
            self.append(sp)
        else:
            grp = Adw.PreferencesGroup()
            for it in items:
                artist = safe_col(it, "artist") or ""
                album  = safe_col(it, "album") or ""
                subtitle_parts = [p for p in [artist, album] if p]
                row = Adw.ActionRow(title=it["title"])
                if subtitle_parts:
                    row.set_subtitle("  ·  ".join(subtitle_parts))
                url = safe_col(it, "url") or ""
                if url:
                    open_btn = Gtk.Button(icon_name="link-symbolic")
                    open_btn.add_css_class("flat"); open_btn.set_valign(Gtk.Align.CENTER)
                    open_btn.set_tooltip_text("Open link")
                    open_btn.connect("clicked", lambda _, u=url: Gio.AppInfo.launch_default_for_uri(u, None))
                    row.add_suffix(open_btn)
                    row.set_activatable(True)
                    row.connect("activated", lambda _, u=url: Gio.AppInfo.launch_default_for_uri(u, None))
                edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
                edit_btn.add_css_class("flat"); edit_btn.set_valign(Gtk.Align.CENTER)
                edit_btn.set_tooltip_text("Edit")
                edit_btn.connect("clicked", lambda _, i=dict(it):
                    PlaylistItemDialog(self._win, self._pid, item=i, on_save=self._build).present())
                row.add_suffix(edit_btn)
                grp.add(row)
            self.append(grp)

        add_btn = Gtk.Button(label="+ Add track")
        add_btn.add_css_class("suggested-action"); add_btn.add_css_class("pill")
        add_btn.set_halign(Gtk.Align.CENTER)
        add_btn.connect("clicked", lambda _:
            PlaylistItemDialog(self._win, self._pid, on_save=self._build).present())
        self.append(add_btn)

    def _rename_dialog(self, current_name):
        dlg = Adw.Dialog(title="Rename playlist", content_width=380)
        tv = Adw.ToolbarView(); tv.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=20, margin_start=12, margin_end=12)
        grp = Adw.PreferencesGroup()
        entry = Adw.EntryRow(title="Playlist name")
        entry.set_text(current_name)
        grp.add(entry); box.append(grp)
        save_btn = Gtk.Button(label="Rename")
        save_btn.add_css_class("suggested-action"); save_btn.add_css_class("pill")
        def do_rename(_):
            name = entry.get_text().strip()
            if name:
                db_playlist_set_name(self._pid, name)
            dlg.close()
            self._build()
        save_btn.connect("clicked", do_rename)
        box.append(save_btn); tv.set_content(box); dlg.set_child(tv)
        dlg.present(self._win)


class PreferencesDialog(Adw.PreferencesWindow):
    """App-wide preferences — opened from the hamburger menu."""
    def __init__(self, parent):
        super().__init__(title="Preferences", transient_for=parent, modal=True)
        self.set_search_enabled(False)

        # ── Appearance ────────────────────────────────────────────
        app_page = Adw.PreferencesPage(title="Appearance", icon_name="display-brightness-symbolic")

        scheme_grp = Adw.PreferencesGroup(title="Color scheme")
        scheme_row = Adw.ComboRow(title="Theme")
        scheme_row.set_model(Gtk.StringList.new(["Follow system", "Light", "Dark"]))
        _saved = get_setting("color_scheme", "system")
        scheme_row.set_selected({"system": 0, "light": 1, "dark": 2}.get(_saved, 0))
        scheme_row.connect("notify::selected", self._on_scheme)
        scheme_grp.add(scheme_row)
        app_page.add(scheme_grp)

        busy_grp = Adw.PreferencesGroup(
            title="Monthly busyness thresholds",
            description="Controls the Light / Medium / Heavy badge on the home page")
        med_row = Adw.SpinRow.new_with_range(1, 50, 1)
        med_row.set_title("Medium starts at")
        med_row.set_subtitle("tasks due in next 30 days")
        med_row.set_value(int(get_setting("busyness_medium", "8")))
        med_row.connect("notify::value", lambda r, _: set_setting("busyness_medium", int(r.get_value())))
        busy_grp.add(med_row)
        heavy_row = Adw.SpinRow.new_with_range(1, 100, 1)
        heavy_row.set_title("Heavy starts at")
        heavy_row.set_subtitle("tasks due in next 30 days")
        heavy_row.set_value(int(get_setting("busyness_heavy", "15")))
        heavy_row.connect("notify::value", lambda r, _: set_setting("busyness_heavy", int(r.get_value())))
        busy_grp.add(heavy_row)
        app_page.add(busy_grp)

        self.add(app_page)

        # ── Focus / Pomodoro ──────────────────────────────────────
        focus_page = Adw.PreferencesPage(title="Focus", icon_name="clock-symbolic")

        level_grp = Adw.PreferencesGroup(
            title="Focus mode level",
            description="Controls what appears when you open Focus mode from the menu")
        level_row = Adw.ComboRow(title="Level")
        level_row.set_model(Gtk.StringList.new(["Extreme", "Focused"]))
        _focus_lvl = get_setting("focus_level", "extreme")
        level_row.set_selected(0 if _focus_lvl == "extreme" else 1)
        level_row.connect("notify::selected",
            lambda r, _: set_setting("focus_level", ["extreme", "focused"][r.get_selected()]))

        extreme_hint = Adw.ActionRow(title="Extreme")
        extreme_hint.set_subtitle("One task only · timer · nothing else. Pure single-point focus.")
        extreme_hint.set_activatable(False)

        focused_hint = Adw.ActionRow(title="Focused")
        focused_hint.set_subtitle(
            "Timer · today's tasks + overdue across all projects · active goals · "
            "near-due milestones. All relevant context, no project clutter.")
        focused_hint.set_activatable(False)

        level_grp.add(level_row)
        level_grp.add(extreme_hint)
        level_grp.add(focused_hint)
        focus_page.add(level_grp)

        pomo_grp = Adw.PreferencesGroup(
            title="Pomodoro timer",
            description="Changes take effect the next time you open the timer")
        work_row = Adw.SpinRow.new_with_range(5, 120, 5)
        work_row.set_title("Work session")
        work_row.set_subtitle("minutes")
        work_row.set_value(int(get_setting("pomo_work_mins", "25")))
        work_row.connect("notify::value", lambda r, _: set_setting("pomo_work_mins", int(r.get_value())))
        pomo_grp.add(work_row)
        break_row = Adw.SpinRow.new_with_range(1, 60, 1)
        break_row.set_title("Break")
        break_row.set_subtitle("minutes")
        break_row.set_value(int(get_setting("pomo_break_mins", "5")))
        break_row.connect("notify::value", lambda r, _: set_setting("pomo_break_mins", int(r.get_value())))
        pomo_grp.add(break_row)
        focus_page.add(pomo_grp)

        self.add(focus_page)

    def _on_scheme(self, row, _):
        key = ["system", "light", "dark"][row.get_selected()]
        set_setting("color_scheme", key)
        mgr = Adw.StyleManager.get_default()
        mgr.set_color_scheme({
            "system": Adw.ColorScheme.DEFAULT,
            "light":  Adw.ColorScheme.FORCE_LIGHT,
            "dark":   Adw.ColorScheme.FORCE_DARK,
        }[key])


class HelpDialog(Adw.Window):
    def __init__(self, parent):
        super().__init__(title="Help & Shortcuts", modal=True, transient_for=parent,
                         default_width=560, default_height=620, resizable=True)
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        scroll = Gtk.ScrolledWindow(vexpand=True,
                                    margin_top=12, margin_bottom=12,
                                    margin_start=18, margin_end=18)
        label = Gtk.Label(label=TUTORIAL_TEXT, xalign=0, yalign=0,
                          wrap=False, selectable=False)
        label.add_css_class("monospace")
        scroll.set_child(label)
        tv.set_content(scroll)
        self.set_content(tv)


# ══════════════════════════════════════════════════════
# Main window
# ══════════════════════════════════════════════════════

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Projex")
        self.set_default_size(1100, 720)

        split = Adw.NavigationSplitView()
        split.set_min_sidebar_width(220)
        split.set_max_sidebar_width(300)
        self._split = split

        self._collapsed_groups = set()

        # ── Sidebar ───────────────────────────────────
        sidebar_page = Adw.NavigationPage(title="Projects")
        stv = Adw.ToolbarView()
        shdr = Adw.HeaderBar()
        shdr.set_show_end_title_buttons(False)
        new_btn = Gtk.Button(icon_name="list-add-symbolic")
        new_btn.add_css_class("suggested-action")
        new_btn.add_css_class("circular")
        new_btn.set_tooltip_text("New project")
        new_btn.connect("clicked",
            lambda _: ProjectDialog(self, on_save=self.refresh_projects).present())
        shdr.pack_end(new_btn)
        home_btn = Gtk.Button(icon_name="go-home-symbolic")
        home_btn.add_css_class("flat")
        home_btn.set_tooltip_text("Overview")
        home_btn.connect("clicked", lambda _: self.show_home())
        shdr.pack_start(home_btn)
        today_btn = Gtk.Button(icon_name="view-list-symbolic")
        today_btn.add_css_class("flat")
        today_btn.set_tooltip_text("Today")
        today_btn.connect("clicked", lambda _: self.show_today())
        shdr.pack_start(today_btn)
        coming_btn = Gtk.Button(icon_name="flag-symbolic")
        coming_btn.add_css_class("flat")
        coming_btn.set_tooltip_text("Upcoming Deadlines")
        coming_btn.connect("clicked", lambda _: self.show_coming_up())
        shdr.pack_start(coming_btn)
        # Pomodoro — clock icon only, no duplication
        self._pomo_btn = Gtk.ToggleButton(icon_name="clock-symbolic")
        self._pomo_btn.add_css_class("flat")
        self._pomo_btn.set_tooltip_text("Pomodoro timer")
        shdr.pack_end(self._pomo_btn)

        # ── Tools menu (⋮) — groups secondary actions ──────────
        tools_popover = Gtk.Popover()
        tools_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                            margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)

        def _menu_btn(label, icon, callback):
            b = Gtk.Button()
            b.add_css_class("flat")
            inner = Gtk.Box(spacing=10)
            inner.append(Gtk.Image(icon_name=icon))
            inner.append(Gtk.Label(label=label, xalign=0, hexpand=True))
            b.set_child(inner)
            b.connect("clicked", lambda _: (tools_popover.popdown(), callback()))
            tools_box.append(b)

        # Apply saved color scheme on startup
        _saved_scheme = get_setting("color_scheme", "system")
        Adw.StyleManager.get_default().set_color_scheme({
            "light":  Adw.ColorScheme.FORCE_LIGHT,
            "dark":   Adw.ColorScheme.FORCE_DARK,
        }.get(_saved_scheme, Adw.ColorScheme.DEFAULT))

        _menu_btn("Preferences",           "preferences-system-symbolic",   lambda: PreferencesDialog(self).present())
        tools_box.append(Gtk.Separator())
        _menu_btn("Focus mode",           "view-fullscreen-symbolic",       self.show_focus_mode)
        _menu_btn("Pinned notes",         "starred-symbolic",               self.show_pinned_notes)
        _menu_btn("Archived projects",    "folder-symbolic",                self.show_archived_projects)
        _menu_btn("Project templates",    "document-open-recent-symbolic",  lambda: ProjectTemplatesDialog(self).present())
        _menu_btn("New group",            "folder-new-symbolic",            self._new_group_dialog)
        tools_box.append(Gtk.Separator())
        _menu_btn("Help & shortcuts",  "dialog-question-symbolic",       lambda: HelpDialog(self).present())

        tools_popover.set_child(tools_box)
        tools_btn = Gtk.MenuButton()
        tools_btn.set_icon_name("open-menu-symbolic")
        tools_btn.add_css_class("flat")
        tools_btn.set_tooltip_text("Tools & settings")
        tools_btn.set_popover(tools_popover)
        shdr.pack_end(tools_btn)

        # ── Global Pomodoro — created here so it sits BELOW shdr ──
        self._pomo_widget = PomodoroWidget()
        self._pomo_rev = Gtk.Revealer(reveal_child=False)
        self._pomo_rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._pomo_rev.set_child(self._pomo_widget)
        self._pomo_btn.connect("toggled", lambda b: self._pomo_rev.set_reveal_child(b.get_active()))

        stv.add_top_bar(shdr)
        stv.add_top_bar(self._pomo_rev)   # below header bar → window controls always on top

        # Search bar
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Search…")
        self._search.set_margin_start(8); self._search.set_margin_end(8)
        self._search.set_margin_top(6);   self._search.set_margin_bottom(2)
        self._search.connect("search-changed", self._on_search)
        stv.add_top_bar(self._search)

        # Sort dropdown
        _SORT_LABELS = ["Manual order", "Alphabetical", "Most recently active",
                        "Date added", "Most goals", "Most outstanding"]
        self._sort_mode = get_setting("sidebar_sort", "manual")
        _saved_sort_idx = _SORT_MODES.index(self._sort_mode) if self._sort_mode in _SORT_MODES else 0
        self._sort_drop = Gtk.DropDown.new_from_strings(_SORT_LABELS)
        self._sort_drop.set_selected(_saved_sort_idx)
        self._sort_drop.set_margin_start(8); self._sort_drop.set_margin_end(8)
        self._sort_drop.set_margin_top(2);   self._sort_drop.set_margin_bottom(4)
        def _on_sort_changed(drop, _):
            self._sort_mode = _SORT_MODES[drop.get_selected()]
            set_setting("sidebar_sort", self._sort_mode)
            self.refresh_projects()
        self._sort_drop.connect("notify::selected", _on_sort_changed)
        stv.add_top_bar(self._sort_drop)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.add_css_class("navigation-sidebar")
        self._listbox.connect("row-activated",
            lambda _lb, row: self._open_project(row._pid) if row._pid else None)
        self._listbox.set_filter_func(self._sidebar_filter)

        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_child(self._listbox)
        stv.set_content(sw)

        now_playing = NowPlayingBar()
        stv.add_bottom_bar(now_playing)

        sidebar_page.set_child(stv)
        split.set_sidebar(sidebar_page)

        # ── Content ───────────────────────────────────
        self._content_page = Adw.NavigationPage(title="Projex")
        self.show_home()
        split.set_content(self._content_page)

        # ── Status bar ────────────────────────────────
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                             margin_start=10, margin_end=6,
                             margin_top=3, margin_bottom=3)
        status_bar.append(Gtk.Box(hexpand=True))
        ver_btn = Gtk.Button(label=f"v{VERSION}")
        ver_btn.add_css_class("flat")
        ver_btn.add_css_class("caption")
        ver_btn.set_tooltip_text("View changelog")
        ver_btn.connect("clicked", lambda _: ChangelogDialog(self).present())
        status_bar.append(ver_btn)

        split.set_vexpand(True)
        main_tv = Adw.ToolbarView()
        main_tv.set_content(split)
        main_tv.add_bottom_bar(status_bar)
        self.set_content(main_tv)

        self.refresh_projects()

        # ── Global keyboard shortcuts ──────────────────
        gsc = Gtk.ShortcutController()
        gsc.set_scope(Gtk.ShortcutScope.MANAGED)
        gsc.add_shortcut(Gtk.Shortcut.new(
            Gtk.KeyvalTrigger.new(Gdk.KEY_f, Gdk.ModifierType.CONTROL_MASK),
            Gtk.CallbackAction.new(lambda *_: self._search.grab_focus() or True),
        ))
        self.add_controller(gsc)

        # First-run welcome tutorial
        if get_setting("welcome_shown") != "1":
            GLib.idle_add(lambda: WelcomeTutorial(self).present() or False)

    def refresh_projects(self, new_pid=None):
        row = self._listbox.get_row_at_index(0)
        while row is not None:
            self._listbox.remove(row)
            row = self._listbox.get_row_at_index(0)

        mode = getattr(self, "_sort_mode", "manual")
        is_manual = (mode == "manual")
        groups = {g["id"]: g for g in db_groups()}

        def _add_project_row(p):
            lbrow = Gtk.ListBoxRow()
            lbrow._pid      = p["id"]
            lbrow._pname    = p["name"]
            lbrow._pstatus  = p["status"]
            lbrow._group_id = int(safe_col(p, "group_id") or 0)

            inner = Gtk.Box(spacing=8, margin_top=9, margin_bottom=9,
                            margin_start=8, margin_end=12)

            # ── Drag handle (manual order only) ──────────────────
            if is_manual:
                handle = Gtk.Label(label="⠿")
                handle.add_css_class("dim-label")
                handle.set_valign(Gtk.Align.CENTER)
                handle.set_margin_start(4)
                try:
                    handle.set_cursor(Gdk.Cursor.new_from_name("grab", None))
                except Exception:
                    pass
                drag = Gtk.DragSource.new()
                drag.set_actions(Gdk.DragAction.MOVE)
                drag.connect("prepare", lambda src, x, y, i=p["id"]:
                    Gdk.ContentProvider.new_for_value(str(i)))
                drag.connect("drag-begin", lambda src, data, r=lbrow:
                    src.set_icon(Gtk.WidgetPaintable.new(r), 0, 0))
                handle.add_controller(drag)
                inner.append(handle)

                drop = Gtk.DropTarget.new(str, Gdk.DragAction.MOVE)
                drop.connect("drop", lambda tgt, val, x, y, tid=p["id"]: (
                    db_reorder_project(int(val), tid),
                    GLib.idle_add(self.refresh_projects),
                    True
                )[-1])
                lbrow.add_controller(drop)

            dot = color_dot(p["color"], size=12)
            dot.set_valign(Gtk.Align.CENTER)
            inner.append(dot)

            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1,
                               hexpand=True)
            emoji = safe_col(p, "emoji") or suggest_emoji(p["name"])
            display_name = f"{emoji}  {p['name']}" if emoji else p["name"]
            name_lbl = Gtk.Label(label=display_name, xalign=0)
            name_lbl.set_ellipsize(3)
            status_lbl = Gtk.Label(label=p["status"], xalign=0)
            status_lbl.add_css_class("caption")
            status_lbl.add_css_class("dim-label")
            text_box.append(name_lbl)
            text_box.append(status_lbl)
            inner.append(text_box)

            # Right-click → move-to-group popover
            popover = Gtk.Popover()
            pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                              margin_top=4, margin_bottom=4, margin_start=4, margin_end=4)
            pop_hdr = Gtk.Label(label="Move to group", xalign=0)
            pop_hdr.add_css_class("caption"); pop_hdr.add_css_class("dim-label")
            pop_hdr.set_margin_bottom(4)
            pop_box.append(pop_hdr)

            def _move(pid, gid):
                db_set_project_group(pid, gid)
                popover.popdown()
                self.refresh_projects()

            no_grp = Gtk.Button(label="— No group")
            no_grp.add_css_class("flat")
            no_grp.connect("clicked", lambda _, pid=p["id"]: _move(pid, 0))
            pop_box.append(no_grp)
            for g in groups.values():
                gb = Gtk.Button(label=g["name"])
                gb.add_css_class("flat")
                gb.connect("clicked", lambda _, pid=p["id"], gid=g["id"]: _move(pid, gid))
                pop_box.append(gb)

            popover.set_child(pop_box)
            popover.set_parent(inner)

            gc3 = Gtk.GestureClick.new()
            gc3.set_button(3)
            gc3.connect("pressed", lambda _g, _n, _x, _y: popover.popup())
            inner.add_controller(gc3)

            lbrow.set_child(inner)
            self._listbox.append(lbrow)

        if is_manual:
            # Manual order: respect groups + position-based ordering
            projects = list(db_projects_sorted("manual"))
            grouped = {}
            ungrouped = []
            for p in projects:
                gid = int(safe_col(p, "group_id") or 0)
                if gid and gid in groups:
                    grouped.setdefault(gid, []).append(p)
                else:
                    ungrouped.append(p)

            for p in ungrouped:
                _add_project_row(p)

            for gid, g in groups.items():
                if gid not in grouped:
                    continue
                hrow = Gtk.ListBoxRow()
                hrow._pid = None; hrow._pname = ""; hrow._pstatus = ""
                hrow._group_id = -1
                hrow.set_activatable(False)
                collapsed = gid in self._collapsed_groups
                hinner = Gtk.Box(spacing=6, margin_top=6, margin_bottom=4,
                                 margin_start=12, margin_end=12)
                arrow_lbl = Gtk.Label(label="▶" if collapsed else "▼")
                arrow_lbl.add_css_class("caption")
                name_lbl = Gtk.Label(label=g["name"], xalign=0, hexpand=True)
                name_lbl.add_css_class("caption"); name_lbl.add_css_class("group-header-row")
                del_btn = Gtk.Button(icon_name="user-trash-symbolic")
                del_btn.add_css_class("flat"); del_btn.add_css_class("destructive-action")
                del_btn.set_valign(Gtk.Align.CENTER)

                def _delete_group(_, gid=gid, gname=g["name"]):
                    def _do(gid=gid):
                        db_delete_group(gid)
                        self._collapsed_groups.discard(gid)
                        self.refresh_projects()
                    _confirm_delete(self, "Delete group?",
                                    f"\"{gname}\" will be removed. Projects in it won't be deleted.",
                                    lambda: _do())
                del_btn.connect("clicked", _delete_group)
                hinner.append(arrow_lbl); hinner.append(name_lbl); hinner.append(del_btn)
                hrow.set_child(hinner)

                gc_hdr = Gtk.GestureClick.new()
                gc_hdr.set_button(1)
                def _toggle_grp(_g, _n, _x, _y, gid=gid):
                    if gid in self._collapsed_groups:
                        self._collapsed_groups.discard(gid)
                    else:
                        self._collapsed_groups.add(gid)
                    self._listbox.invalidate_filter()
                    self.refresh_projects()
                gc_hdr.connect("pressed", _toggle_grp)
                hinner.add_controller(gc_hdr)
                self._listbox.append(hrow)

                for p in grouped[gid]:
                    _add_project_row(p)
        else:
            # Non-manual sort: flat list, no groups, no drag handles
            for p in db_projects_sorted(mode):
                _add_project_row(p)

        if new_pid:
            self._open_project(new_pid)

    def _sidebar_filter(self, row):
        q = self._search.get_text().strip().lower()
        # Group header rows are always visible
        if getattr(row, "_pid", None) is None:
            return True
        # Archived projects are hidden from the sidebar
        if getattr(row, "_pstatus", "") == "archived":
            return False
        gid = getattr(row, "_group_id", 0)
        if gid and gid in self._collapsed_groups:
            return False
        if q:
            return q in getattr(row, "_pname", "").lower()
        return True

    def _on_search(self, entry):
        self._listbox.invalidate_filter()
        q = entry.get_text().strip()
        if q:
            self._show_content_view(GlobalSearchView(q, self), f'Search: "{q}"')
        else:
            self.show_home()

    def _new_group_dialog(self):
        dialog = Adw.Window(title="New Group", modal=True, transient_for=self,
                            default_width=340, resizable=False)
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=18, margin_start=18, margin_end=18)
        grp = Adw.PreferencesGroup()
        entry = Adw.EntryRow(title="Group name")
        grp.add(entry)
        box.append(grp)
        btn = Gtk.Button(label="Create Group", margin_top=4)
        btn.add_css_class("suggested-action"); btn.add_css_class("pill")

        def _create(_):
            name = entry.get_text().strip()
            if not name:
                return
            db_create_group(name)
            dialog.close()
            self.refresh_projects()

        btn.connect("clicked", _create)
        entry.connect("entry-activated", _create)
        box.append(btn)
        tv.set_content(box)
        dialog.set_content(tv)
        dialog.present()

    def _show_content_view(self, view, title="Projex"):
        tv = Adw.ToolbarView()
        hdr = Adw.HeaderBar()
        back_btn = Gtk.Button(icon_name="go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.set_tooltip_text("Back to overview")
        back_btn.connect("clicked", lambda _: self.show_home())
        hdr.pack_start(back_btn)
        tv.add_top_bar(hdr)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(view)
        tv.set_content(scroll)
        self._content_page.set_child(tv)
        self._content_page.set_title(title)
        self._split.set_show_content(True)

    def show_home(self):
        self._search.set_text("")
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(HomeView(self))
        tv.set_content(scroll)
        self._content_page.set_child(tv)
        self._content_page.set_title("Homepage")

    def show_all_tasks(self):
        self._show_content_view(AllTasksGoalsView(self), "All Tasks & Goals")

    def show_all_files(self):
        self._show_content_view(AllFilesView(self), "All Linked Files")

    def show_coming_up(self):
        self._show_content_view(ComingUpView(self), "Upcoming Deadlines")

    def show_today(self):
        self._show_content_view(TodayView(self), "Today")

    def show_focus_mode(self):
        if self._content_page.get_title() == "Focus Mode":
            self.show_home()
        else:
            self._show_content_view(FocusModeView(self), "Focus Mode")
            if not self._pomo_btn.get_active():
                self._pomo_btn.set_active(True)
            if not self._pomo_widget._running:
                self._pomo_widget._on_start_pause(None)

    def show_pinned_notes(self):
        self._show_content_view(AllPinnedNotesView(self), "Pinned Notes")

    def show_archived_projects(self):
        self._show_content_view(ArchivedProjectsView(self), "Archived Projects")

    def _open_project(self, pid, on_back=None, section=None):
        detail = ProjectDetailView(pid=pid, window=self, on_back=on_back)
        self._content_page.set_child(detail)
        p = db_project(pid)
        self._content_page.set_title(p["name"] if p else "Project")
        self._split.set_show_content(True)
        if section:
            GLib.idle_add(lambda: detail._open_section(section) or False)


# ══════════════════════════════════════════════════════
# Welcome Tutorial
# ══════════════════════════════════════════════════════

class WelcomeTutorial(Adw.Window):
    """Multi-page first-run walkthrough."""

    PAGES = [
        (
            "starred-symbolic",
            "Welcome to Projex",
            "A focused project tracker built around Projects → Goals → Tasks → Notes.\n\n"
            "This quick tour covers the key ideas. "
            "You can always reopen it from Help & shortcuts in the ☰ menu.",
        ),
        (
            "folder-symbolic",
            "Projects & the sidebar",
            "Press + in the sidebar to create a project. Each project has its own colour and emoji.\n\n"
            "Right-click a project to assign it to a named group (e.g. Work / Personal). "
            "The ☰ menu lets you archive projects when done — they disappear from the main sidebar "
            "but stay accessible from the archived list.",
        ),
        (
            "appointment-new-symbolic",
            "Goals & the Gantt chart",
            "Goals are milestones with a start date, end date, status, and priority. "
            "Set a 'Depends on' link between goals to draw dependency arrows on the Gantt chart.\n\n"
            "Use +7d, +2w, or +1m in any date field as a shortcut. "
            "Goals appear on the homepage Gantt so you can see every project's timeline at a glance.",
        ),
        (
            "checkbox-checked-symbolic",
            "Tasks, Notes & Focus",
            "Tasks live inside a project — type #tag in the task name to label it instantly. "
            "Assign a task to a goal to group your work.\n\n"
            "Notes support free-form text with pinning so highlights float to the dashboard.\n\n"
            "Focus Mode (☰ menu) surfaces your single highest-priority task with a Pomodoro timer.",
        ),
    ]

    def __init__(self, parent):
        super().__init__(title="Welcome to Projex", modal=True,
                         transient_for=parent, default_width=480,
                         default_height=460, resizable=False)
        self._page_idx = 0

        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Page content area
        self._icon = Gtk.Image(); self._icon.set_pixel_size(64)
        self._icon.set_margin_top(28); self._icon.add_css_class("accent")
        self._title_lbl = Gtk.Label(); self._title_lbl.add_css_class("title-2")
        self._title_lbl.set_margin_top(12)
        self._body_lbl = Gtk.Label()
        self._body_lbl.set_wrap(True); self._body_lbl.set_xalign(0)
        self._body_lbl.set_margin_top(12)
        self._body_lbl.set_margin_start(28); self._body_lbl.set_margin_end(28)

        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        icon_box.set_halign(Gtk.Align.CENTER)
        icon_box.append(self._icon)
        icon_box.append(self._title_lbl)
        outer.append(icon_box)
        outer.append(self._body_lbl)

        # Page dots
        self._dots_box = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER,
                                 margin_top=20, margin_bottom=4)
        self._dots = []
        for i in range(len(self.PAGES)):
            dot = Gtk.Label(label="●")
            dot.add_css_class("caption")
            self._dots_box.append(dot)
            self._dots.append(dot)
        outer.append(self._dots_box)

        # Navigation buttons
        btn_box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER,
                          margin_top=16, margin_bottom=28)
        self._back_btn = Gtk.Button(label="← Back")
        self._back_btn.add_css_class("flat")
        self._back_btn.connect("clicked", lambda _: self._go(-1))
        self._next_btn = Gtk.Button(label="Next →")
        self._next_btn.add_css_class("suggested-action"); self._next_btn.add_css_class("pill")
        self._next_btn.connect("clicked", lambda _: self._go(1))
        btn_box.append(self._back_btn); btn_box.append(self._next_btn)
        outer.append(btn_box)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(outer)
        tv.set_content(scroll)
        self.set_content(tv)
        self._render()

    def _render(self):
        icon, title, body = self.PAGES[self._page_idx]
        self._icon.set_from_icon_name(icon)
        self._title_lbl.set_label(title)
        self._body_lbl.set_label(body)
        last = self._page_idx == len(self.PAGES) - 1
        self._next_btn.set_label("Done ✓" if last else "Next →")
        self._back_btn.set_sensitive(self._page_idx > 0)
        for i, dot in enumerate(self._dots):
            dot.remove_css_class("accent"); dot.remove_css_class("dim-label")
            dot.add_css_class("accent" if i == self._page_idx else "dim-label")

    def _go(self, direction):
        if direction > 0 and self._page_idx == len(self.PAGES) - 1:
            set_setting("welcome_shown", "1")
            self.close()
            return
        self._page_idx = max(0, min(len(self.PAGES) - 1, self._page_idx + direction))
        self._render()


# ══════════════════════════════════════════════════════
# Application
# ══════════════════════════════════════════════════════

class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        _load_css()
        MainWindow(application=app).present()


if __name__ == "__main__":
    GLib.set_prgname(APP_ID)
    GLib.set_application_name("Projex")
    init_db()
    migrate_db()
    App().run()
