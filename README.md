# Projex

A native GNOME project tracker built with GTK4 and libadwaita.

Track projects, milestones, tasks, goals, and writing — all in one
clean desktop app.

## Features

- **Projects** — name, status, description, and a custom colour
- **Milestones** — date-ranged milestones with a live Gantt chart
- **To-dos** — task list with priority levels (normal / high / low)
- **Goals** — simple goal list with completion tracking
- **Writing log** — journal-style entries with draft/done status
- Data stored in `~/.local/share/projex/tracker.db` (XDG standard)

## Requirements

- Python 3.10+
- GTK 4
- libadwaita ≥ 1.4
- PyGObject (python3-gobject)

## Installation

```bash
cd projex
./install.sh
```

This installs the required system packages (GTK4, libadwaita,
PyGObject), registers the app icon, and creates a desktop launcher so
Projex appears in your application menu.

Supported package managers: zypper (openSUSE), dnf (Fedora),
apt (Debian/Ubuntu).

## Running

```bash
python3 app.py
```

Or launch **Projex** from your GNOME application grid after running
`install.sh`.

## Project structure

```
projex/
├── app.py          Main application (GTK4/libadwaita)
├── CHANGELOG.md    Version history
├── install.sh      Dependency installer and launcher setup
├── icons/
│   └── io.github.emmastf.Projex.svg   App icon
└── README.txt      Legacy quick-start note
```

## Data

All data lives in a single SQLite database:

```
~/.local/share/projex/tracker.db
```

Tables: `project`, `milestone`, `todo`, `goal`, `writing_entry`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT
