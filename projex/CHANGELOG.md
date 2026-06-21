# Changelog

All notable changes to Projex are documented here.
Versioning follows Semantic Versioning (semver.org).

---

## [0.1.10] - 2026-06-20

### Added
- **Pomodoro timer**: 🍅 alarm button in the project header reveals a compact
  horizontal timer bar — 25-minute work / 5-minute break cycles with
  Start/Pause, Skip (jump to next phase), and Reset; session counter increments
  each completed cycle; timer keeps running while navigating between sections
- **Activity streaks**: completing tasks now records a `completed_date`; a
  "🔥 N-day streak" badge appears on the To-do tile subtitle and the home page
  project row whenever you've completed at least one task on N consecutive days
- **"Pick a task for me"**: shuffle button in the Tasks section header picks a
  random undone task and shows it in a dismissable banner at the top of the
  list — useful when you can't decide what to do next
- **Bulk task actions**: "Select" toggle in the Tasks header enters multi-select
  mode; selection checkboxes appear on each active task row; a bottom action bar
  offers "Mark done (N)" and "Delete (N)" to act on all selected tasks at once
- **Milestone completion %**: a 0–100 slider in the milestone edit dialog records
  how far along a milestone is; the Gantt bar renders a partial fill (dimmed
  background = full range, solid fill = completion fraction) with a % label
  inside the filled portion
- **Export as Markdown**: a share button in the project dashboard header opens a
  save dialog; the exported `.md` file contains milestones, open/closed tasks,
  goals, and a writing log preview

---

## [0.1.9] - 2026-06-20

### Added
- **Back button on all content views**: every view opened from the home page
  (All Tasks & Goals, All Files, Coming Up Soon, Search results) now has a ←
  back button in its header bar that returns to the overview
- **Back button on project dashboard**: the project detail view now has a ←
  button in the header bar so you can return to the overview without using the
  sidebar home button
- **Project emoji**: each project gets an auto-suggested emoji based on its
  name (e.g., "Student journal" → 🎓, "Fitness" → 💪); editable in the project
  dialog; shown in the sidebar and on the home page project rows
- **Fun progress quip**: the overall-progress row on the home page now shows a
  cheeky one-liner matching the completion level (e.g., "Glass half full! 🥛"
  at 50%, "Absolutely crushed it! You legend 🎉" at 100%)
- **Coming up soon summary on home page**: a condensed "Coming up" section
  between the due-soon list and the Gantt shows the next 4 items due in days
  15–60, with a "See all" button linking to the full view

### Fixed
- **All linked files** now opens files correctly using `GLib.filename_to_uri`
  (same method as the per-project Files section)

---

## [0.1.8] - 2026-06-20

### Added
- **Global search**: type in the search bar above the project list to find
  tasks, milestones, goals, notes, and writing entries across all projects;
  results appear in the content area with project name and type as context
- **Writing log word count**: each entry row now shows word count in its
  subtitle; the section title shows a running total (e.g., "Writing log (1,840 words)")
- **Goal deadlines**: goals now have an optional due-date field (YYYY-MM-DD),
  visible in the Edit Goal dialog; goals with upcoming due dates appear in the
  "Due in the next 14 days" home section alongside milestones
- **Hide archived projects in sidebar**: a "Show archived" toggle below the
  search bar collapses all archived projects from the sidebar on demand
- **Overall progress is now clickable**: the progress row on the home page
  navigates to "All Tasks & Goals" — a full cross-project task and goal list
- **All linked files page**: a new "All linked files" row on the home page
  opens a browse view of every file linked across all projects, grouped by
  project, with one-click open
- **Coming up soon**: a ⏰ alarm button in the sidebar opens a "Coming Up
  Soon" view showing all milestones and goal deadlines in the next 90 days,
  grouped by month with urgency colours
- **Gantt priority outlines**: each bar in the Gantt chart now has a coloured
  stroke outline indicating priority — red for high, blue for low, yellow for
  normal — making priority visible without opening the edit dialog

### Changed
- "Due in the next 14 days" home section now includes goals with due dates
  alongside milestones, sorted chronologically

---

## [0.1.7] - 2026-06-20

### Added
- **Drag-to-reorder tasks**: active tasks have a ⠿ drag handle on the left;
  drag one row onto another to swap order; position is persisted in the DB
  (`order_pos` column on `todo`)
- **Milestone templates**: a Templates button (⏱) in the Timeline header opens
  a template library where you can create named sets of milestones with
  day-offset and duration fields, save the current project's milestones as a
  template, and apply any template to the project from a chosen start date
- **Collapse completed tasks**: done tasks are now hidden by default under a
  "▶ N completed tasks" disclosure row; click it to reveal/hide (starts
  collapsed on every rebuild)
- **Project colour strip on home Gantt**: each milestone bar in the home
  overview Gantt now has a 5 px coloured strip at the far-left edge matching
  the project colour — makes it easy to visually group bars by project
- **Quick-add task from home view**: each project row on the Overview page now
  has a `+` button that opens a compact "Quick task" dialog (title + priority +
  #tags, press Enter to save); the overview refreshes immediately after saving

---

## [0.1.3] - 2026-06-20

### Added
- **Calendar date picker in milestone dialog**: a `Gtk.Calendar` widget lets
  you click a date rather than type it; radio buttons let you switch which
  field (Start or End) the calendar controls; typing in the entry still works
  and syncs the calendar display automatically
- **Milestone fields — priority & status**: milestones now carry Priority
  (normal / high / low) and Status (pending / active / done / blocked) in
  addition to a free-text Notes field
- **Priority bar on milestone rows**: same 4 px left-edge colour bar used by
  tasks — red for high, blue for low
- **Status badge on milestone rows**: small colour-coded label (success /
  accent / error / dim) beside each milestone
- **Gantt status colours**: bars are now coloured by status — green for done,
  red for blocked, dimmed accent for pending, full accent for active
- **Year/range selector for Gantt**: a "View" dropdown above the chart lets
  you pin the x-axis to a specific calendar year (current year ± range up to
  ~9 years out); select "All" to auto-fit the existing milestones; milestones
  that extend beyond the selected range show arrow indicators on the bar
- **Quarter lines on Gantt**: ranges longer than ~2 years switch from monthly
  to quarterly grid lines, keeping the chart readable at any scale

### Changed
- Tags input now accepts comma-separated values without requiring `#` prefix:
  `design, urgent` and `#design #urgent` are equivalent; mixing styles works
  too (`design, #urgent`)
- `TodoEditDialog` tags field uses the same flexible parser

---

## [0.1.2] - 2026-06-20

### Added
- **Labels / hashtags on tasks**: type `#tag` anywhere in a new task and
  it is extracted automatically — e.g. "Design mockup #design #urgent"
  stores the text and labels separately
- **Labels section**: new dashboard tile showing every label used in the
  project, with task count, done count, completion progress bar, and a
  per-label task list for spotting patterns
- **Edit task dialog**: pencil button on every task opens a dialog to
  change the text, labels, and priority after the fact
- **High/low priority indicator**: a 4 px coloured bar on the left edge
  of each task row — red for high, blue for low, invisible for normal

### Changed
- Priority is now editable inline via a dropdown on each active task row
  (was read-only in 0.1.1)
- `TodoEditDialog` normalises label input: words without a leading `#`
  get one added automatically on save

---

## [0.1.1] - 2026-06-19

### Fixed
- Sidebar project rows now activate correctly when clicked (replaced
  Adw.ActionRow with plain Gtk.ListBoxRow to avoid event-capture conflict
  with the color-dot DrawingArea prefix)
- After creating a new project the app now navigates directly into it

### Added
- Project dashboard: clicking a project shows a tile grid of sections
  rather than a flat tab bar — gives a clear overview and lets you jump
  straight to the area you need
- Notes section: quick free-text notes per project, with pin support
- Files section: link existing files on disk; open them with the system
  default application via a single click
- Adw.NavigationView for in-project navigation (dashboard → section →
  back, with automatic back button)
- Two new DB tables: `note` and `file`

---

## [0.1.0] - 2026-06-19

### Added
- Initial release of Projex
- Native GTK4 / libadwaita desktop UI
- Project management: name, status, description, color
- Milestone tracking with Gantt chart (Cairo)
- To-do lists with priority levels
- Goal tracking with completion status
- Writing log entries with draft/done status
- SQLite data store at ~/.local/share/projex/tracker.db (XDG-compliant)
- Desktop launcher and scalable SVG icon
- install.sh for system dependency setup
- Status bar with version number; click to open this changelog
