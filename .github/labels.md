# Label Setup Guide

The **Flask Limit** project uses a structured labeling system to organize issues, pull requests, changelogs, and automated releases.

## Core Labels

### 🐛 Bug Labels

| Label        | Description                                   |
| ------------ | --------------------------------------------- |
| `bug`        | A confirmed bug affecting functionality       |
| `regression` | A bug that breaks previously working behavior |

### ✨ Feature Labels

| Label         | Description                            |
| ------------- | -------------------------------------- |
| `feature`     | A new feature or enhancement           |
| `improvement` | Improvements to existing functionality |
| `refactor`    | Non-functional code restructuring      |

### 📚 Documentation

| Label  | Description                        |
| ------ | ---------------------------------- |
| `docs` | Documentation updates or additions |

### 🎨 UI / DX

| Label   | Description                                 |
| ------- | ------------------------------------------- |
| `ux`    | Developer experience improvements           |
| `style` | Formatting, comments, or style-only changes |

### ⚡ Performance

| Label         | Description                         |
| ------------- | ----------------------------------- |
| `performance` | Optimizations or speed improvements |

### 🧪 Testing

| Label   | Description                        |
| ------- | ---------------------------------- |
| `tests` | Unit tests or testing improvements |

### 🚀 Release Drafter Categories

These are **required** for automatic changelog grouping:

| Label         | Category         |
| ------------- | ---------------- |
| `feature`     | 🚀 Features      |
| `bug`         | 🐛 Bug Fixes     |
| `refactor`    | 🛠 Refactoring    |
| `performance` | 🚦 Performance   |
| `docs`        | 📚 Documentation |
| `tests`       | 🧪 Tests         |
| `maintenance` | ⚙️ Maintenance   |

### ⚠️ PR Versioning tags

| Label   | Description                         |
| ------- | ----------------------------------- |
| `patch` | PR triggers a patch release (0.0.X) |
| `minor` | PR triggers a minor release (0.X.0) |
| `major` | PR triggers a major release (X.0.0) |

### ⚠️ Priority / Severity

| Label              | Description            |
| ------------------ | ---------------------- |
| `priority: high`   | Needs urgent attention |
| `priority: medium` | Address when possible  |
| `priority: low`    | Not urgent             |

### 💬 Community & Support

| Label        | Description                                  |
| ------------ | -------------------------------------------- |
| `question`   | A request for help or clarification          |
| `discussion` | Open-ended design or architecture discussion |

## How Labels Are Used

- **Issues** get labels indicating type (bug, feature), priority, and area.
- **Pull Requests** get labels that map to Release Drafter categories.
- **Release Drafter** auto-generates changelogs using these labels.

This labeling structure ensures consistent project organization and high-quality changelogs.
