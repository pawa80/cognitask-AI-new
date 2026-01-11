# CogniTask AI - Simplified MVP Specification

## Project Context
- **Started**: 19/04/2025
- **Simplified**: 11/01/2026
- **Approach**: Streamlit MVP for single user

---

## 1. Overall Goal

**App Name**: CogniTask AI

**Purpose**: An AI-enhanced task manager that helps you capture tasks naturally (via AI parsing), break them down into sub-tasks, and focus on what's next.

**Target User**: Single user (you), personal productivity tool.

**Key Features**:
1. Natural language task input (AI parses into structured task)
2. AI-powered task breakdown into sub-tasks
3. "What's Next?" Focus Mode
4. Hierarchical task management (parent/child tasks)

---

## 2. Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **UI** | Streamlit | Rapid development, Python-only, built-in state management |
| **Backend** | Python 3.10+ | Single language, simple |
| **Database** | SQLite + SQLAlchemy | File-based, no server needed, ORM for clean code |
| **AI** | Google Gemini 1.5 Flash | Fast, cheap, good at structured output |
| **Deployment** | Streamlit Cloud (future) | Free hosting option |

---

## 3. Authentication

**MVP Approach**: Simple password protection via Streamlit's built-in secrets or a basic password check.

- No JWT, no refresh tokens, no CSRF
- Password stored in `.streamlit/secrets.toml` or environment variable
- Session-based (Streamlit handles this)

**Future**: Can add Streamlit Authenticator package if multi-user needed.

---

## 4. Data Models

### Task Model (SQLAlchemy)
```python
class Task:
    id: int                    # Primary key (auto-increment)
    task_id: str               # UUID for external reference
    title: str                 # Required, max 255 chars
    description: str | None    # Optional details
    status: str                # 'todo', 'inprogress', 'done', 'blocked'
    priority: str              # 'low', 'medium', 'high', 'urgent'
    due_date: datetime | None  # Optional deadline
    parent_task_id: str | None # UUID of parent task (for sub-tasks)
    created_at: datetime       # Auto-set on creation
    updated_at: datetime       # Auto-updated on changes
```

### Status Flow
```
todo -> inprogress -> done
          |
          v
       blocked
```

### Priority Levels (sorted high to low)
1. urgent
2. high
3. medium
4. low

---

## 5. Database Setup

- SQLite file: `cognitask.db` in project root
- SQLAlchemy ORM for all database operations
- Tables created on first run if not exist
- No migrations for MVP (recreate DB if schema changes)

---

## 6. AI Integration

### API Setup
- Model: `gemini-1.5-flash-latest`
- API Key: Stored in `.streamlit/secrets.toml` as `GOOGLE_AI_API_KEY`
- Response format: JSON mode

### Feature 1: NLP Task Parsing
**Input**: Natural language like "Call mom tomorrow, it's urgent"
**Output**: Structured task data:
```json
{
  "title": "Call mom",
  "description": null,
  "priority": "urgent",
  "due_date": "2026-01-12"
}
```

### Feature 2: Task Breakdown
**Input**: A task title/description
**Output**: List of 3-7 actionable sub-tasks
```json
{
  "sub_tasks": [
    "Research options",
    "Compare prices",
    "Make decision"
  ]
}
```

---

## 7. Core Features

### 7.1 Task List View
- Display all tasks in a list
- Show hierarchy (indent sub-tasks under parents)
- Filter by status
- Sort by priority, due date, or creation date

### 7.2 Add Task (Manual)
- Simple form: title, description, priority, due date
- Optional: assign as sub-task of existing task

### 7.3 Add Task (AI-Powered)
- Text input for natural language
- AI parses and shows preview
- User confirms or edits before saving

### 7.4 Task Breakdown (AI)
- Button on any task
- AI generates sub-tasks
- User reviews and confirms
- Sub-tasks created with parent reference

### 7.5 Edit Task
- Click task to edit
- Change any field
- Mark complete/blocked

### 7.6 Delete Task
- Delete button with confirmation
- Cannot delete if has sub-tasks (must delete children first)

### 7.7 Focus Mode ("What's Next?")
- Single task view
- Shows highest priority incomplete task
- Priority order: urgent > high > medium > low
- Tie-breaker: earliest due date, then oldest created
- Quick actions: Mark done, Start working, Skip to next

---

## 8. Streamlit UI Structure

```
App Layout:
├── Sidebar
│   ├── App title/logo
│   ├── Navigation (Task List | Focus Mode)
│   └── Quick stats (total tasks, overdue, etc.)
│
└── Main Area
    ├── Task List View
    │   ├── Filter/Sort controls
    │   ├── "Add Task" button (opens modal/expander)
    │   ├── "AI Add Task" button
    │   └── Task list with hierarchy
    │
    └── Focus Mode View
        ├── Current priority task (big display)
        ├── Action buttons
        └── Progress indicator
```

---

## 9. File Structure

```
cognitask-AI-new/
├── app.py                 # Main Streamlit app
├── database.py            # SQLAlchemy models and DB setup
├── gemini_utils.py        # AI helper functions
├── requirements.txt       # Python dependencies
├── cognitask.db          # SQLite database (gitignored)
├── .streamlit/
│   └── secrets.toml      # API keys (gitignored)
├── .gitignore
├── README.md
└── claude.md             # This spec (living document)
```

---

## 10. Environment & Secrets

### .streamlit/secrets.toml (DO NOT COMMIT)
```toml
GOOGLE_AI_API_KEY = "your-api-key-here"
APP_PASSWORD = "your-simple-password"  # Optional
```

### .gitignore must include:
```
.streamlit/secrets.toml
cognitask.db
__pycache__/
*.pyc
.env
```

---

## 11. Dependencies (requirements.txt)

```
streamlit>=1.30.0
sqlalchemy>=2.0.0
google-generativeai>=0.3.0
python-dateutil>=2.8.0
```

---

## 12. Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

---

## 13. Future Enhancements (Post-MVP)

- [ ] Multi-user with Streamlit Authenticator
- [ ] Recurring tasks
- [ ] Tags/categories
- [ ] Calendar view
- [ ] Export to CSV
- [ ] Mobile PWA wrapper
- [ ] Task templates
- [ ] AI task prioritization suggestions

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-11 | Switch from FastAPI+JS to Streamlit | Simpler for amateur dev, faster to build |
| 2026-01-11 | Drop complex JWT auth | Single user, overkill for MVP |
| 2026-01-11 | Drop ETags/CSRF | Not needed with Streamlit's model |
| 2026-01-11 | Keep SQLite + SQLAlchemy | Good balance of simplicity and structure |
| 2026-01-11 | Keep Gemini AI features | Core differentiator of the app |

---
