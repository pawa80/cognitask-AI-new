PRODUCT ROADMAP

Claude: always push to main to I don't have to merge
Claude: We are going to deploy with streamlit
Claude: remmeber I'm an amateur so tell me exactly where to put secrets like API keys and ensure gitignore is correct and things like that

PRODUCT ROADMAP FOR COGNITASK (claude: you can improve or suggest other if you want)
Working with Gemini
Started 19/04/2025
Updated 26/04/2025
Source: Evernote notebook

CogniTask AI - Application Specification (FINAL - for Local Build)
1. Overall Goal & Context
App Name: CogniTask AI
Purpose: An AI-enhanced task manager designed to support a user's workflow, helping them switch between planning/strategizing and focused execution. Uses AI for task input parsing and breakdown. Includes a "Focus Mode" driven by prioritization rules.
Target User: Single user per instance initially (focus on personal use).
2. Technology Stack
Backend: Python (3.10+) with FastAPI framework.
Database: SQLite initially (using SQLAlchemy ORM for interaction).
Frontend: Standard HTML, CSS, JavaScript. Ensure responsiveness for desktop and mobile (PWA target).
AI Integration: Google AI API (Gemini 1.5 Flash latest model) via HTTPS requests. API key stored locally via .env file / environment variables.
Local Environment: Python virtual environment (.venv), VS Code.
3. User Authentication
Method: Email & Password.
Email Handling: Normalize email to lowercase before uniqueness checks and storage. Treat user+tag@domain.com as distinct from user@domain.com.
Password Hashing: Use passlib.context.CryptContext with bcrypt scheme, work factor 12. Store only the hash.
Password Strength Rule: Minimum 10 characters, including at least one uppercase letter, one lowercase letter, one number, and one special character. Implement validation during signup.
JWT Strategy: Issue short-lived (15 min) JWT Access Tokens containing user_id, exp. Sent via Authorization: Bearer <token> header. Use HS256 algorithm. Issue longer-lived (7 days) JWT Refresh Tokens containing user_id, exp. Sent via secure HttpOnly, Secure, SameSite=Strict cookie. Use HS256 algorithm. Store JWT_SECRET_KEY and REFRESH_SECRET_KEY securely (e.g., in .env file loaded via python-dotenv, accessed via os.environ).
CSRF Protection (Refresh Endpoint): Implement Double Submit Cookie pattern for /auth/refresh. Generate a non-HttpOnly cookie (e.g., csrf_refresh_token) containing a random value when issuing tokens. Require the same value to be sent in a custom HTTP header (e.g., X-CSRF-Token) on requests to /auth/refresh. Validate the header value matches the cookie value. Assume frontend and backend are served from the same origin during local development (http://localhost:8000 or similar).
API Endpoints (FastAPI Routers): POST /auth/signup: Validate input (email format, password strength rule). Check normalized email uniqueness in DB. Hash password. Store user in DB. Return 201 Created or 409 Conflict / 422 Unprocessable Entity. POST /auth/login: Find user by normalized email. Verify hash. Generate access & refresh tokens. Return access token in JSON body, set refresh token cookie. Use generic "Invalid email or password" error message (401 Unauthorized). Apply rate limiting. POST /auth/refresh: Requires valid refresh token cookie and matching CSRF token header/cookie. Validates refresh token. Issues new access token in response body. POST /auth/logout: Clears refresh token cookie. Returns 200 OK.
Rate Limiting: Use slowapi library with an in-memory backend. Apply rate limits (e.g., 10 attempts / 15 min per IP) to /auth/login, /auth/signup, and /auth/refresh. Return 429 Too Many Requests when exceeded.
4. Data Models (Define using Pydantic for API validation & SQLAlchemy for DB)
User (SQLAlchemy Model): Table users. id: Integer Primary Key or UUID Primary Key. user_id: String (UUID v4 hex, unique, indexed). email: String (lowercase, unique, indexed). hashed_password: String. created_at: DateTime (UTC, default now).
Task (SQLAlchemy Model): Table tasks. id: Integer Primary Key or UUID Primary Key. task_id: String (UUID v4 hex, unique, indexed). user_id: String (UUID v4 hex, indexed, Foreign Key to users.user_id - if using UUID PKs, otherwise link to users.id). title: String (Required, max 255 chars). description: Text or String(10000) | None (Use "-" string if null/empty after AI processing before saving?). status: String (Enum: 'todo', 'inprogress', 'done', 'blocked'. Default: 'todo', indexed). priority: String (Enum: 'low', 'medium', 'high', 'urgent'. Default: 'medium', indexed). created_at: DateTime (UTC, default now). updated_at: DateTime (UTC, default now, updates on modification). due_date: DateTime (UTC) | None (indexed). parent_task_id: String (UUID v4 hex) | None (indexed, potentially Foreign Key to tasks.task_id - self-referential).
5. Database Setup (SQLite with SQLAlchemy)
Use SQLAlchemy Core or ORM.
Define models (User, Task) as Python classes.
Use Alembic for database migrations (optional for MVP but good practice).
Create initial SQLite database file (e.g., cognitask.db).
Implement helper functions/dependency injection for getting DB sessions in FastAPI routes.
6. Core Task API (/tasks/) (Require valid Access Token - Use FastAPI Dependencies)
Data Isolation: ALL DB queries MUST filter by the user_id obtained from the validated JWT access token. Use SQLAlchemy session queries like session.query(Task).filter(Task.user_id == current_user_id, Task.task_id == requested_task_id).first(). Return 404 if not found/owned.
GET /tasks/: Fetch a paginated list of tasks for the authenticated user. Query Params: limit (int, max 100, default 50), offset (int, default 0). Fetch tasks using SQLAlchemy: session.query(Task).filter(Task.user_id == current_user_id).order_by(Task.created_at.desc()).offset(offset).limit(limit).all(). Return the list of task objects (Pydantic schema for response). Sorting/filtering beyond basic fetch order is handled client-side.
POST /tasks/ (Standard Creation): Create a new task associated with the user. Request body validated by Pydantic TaskCreate schema. Validate input (title required, enums, lengths, valid parent_task_id if provided - check parent exists and belongs to user, prevent self-reference, prevent direct A<->B cycle). Generate task_id (UUID), set user_id, default status/priority, created_at, updated_at. Create SQLAlchemy Task object, add to session, commit. Return 201 Created with the full task object (Pydantic TaskRead schema) and ETag header.
GET /tasks/{task_id}: Fetch a specific task. Query DB for Task matching task_id AND user_id. Return 404 if not found. Return 200 OK with task object (TaskRead schema) and ETag header.
PATCH /tasks/{task_id}: Partially update a task. Requires If-Match header matching current Etag. Return 428/409. Fetch task from DB (ensuring ownership, 404 if not found). Validate provided fields in request body (Pydantic TaskUpdate schema). Check valid parent_task_id if changed. Update task object fields, update updated_at. Commit session. Return 200 OK with updated task object (TaskRead schema) and new ETag.
DELETE /tasks/{task_id}: Delete a task. Requires If-Match header. Return 428/409. Fetch task (ensuring ownership, 404 otherwise). Deletion Rule: Check if any other task has this task's task_id as its parent_task_id. If so, return 409 Conflict {"error_code": "DELETE_BLOCKED_HAS_CHILDREN"}. If allowed, delete task object from session, commit. Return 204 No Content.
Etag Generation: Use hashlib.sha256(json.dumps(task_pydantic_obj.dict(), sort_keys=True, default=str).encode()).hexdigest(). Compute based on the Pydantic response model.
Error Handling: Use FastAPI exception handlers. Return structured JSON errors ({"error_code": "...", "detail": "..."}) and appropriate HTTP status codes.
7. AI Helper Module (gemini_utils.py)
Create this Python module.
Implement call_gemini(prompt: str) -> dict | None: Takes prompt text. Retrieves GOOGLE_AI_API_KEY from os.environ (loaded via python-dotenv from .env file). Configures google-generativeai client. Specifies model: gemini-1.5-flash-latest. Sets generation_config=genai.types.GenerationConfig(response_mime_type="application/json"). Makes API call with timeout (e.g., 30s). Uses try...except to catch Google AI exceptions, general exceptions. Log errors. Return None on failure. If successful, parse JSON response. Return parsed dict.
8. Feature: NLP Task Input
Backend - Analysis Endpoint: POST /tasks/analyze Requires Auth. Request body: {"user_input": "string"} (Pydantic model). Get current date UTC. Format NLP Input Prompt. Call gemini_utils.call_gemini(prompt). Handle Response: Success (returns dict): Validate with Pydantic model. If valid, ensure extracted_description is string (use "-" if null/empty). Return 200 OK with validated AI data. Failure (returns None): Return 422 {"error_code": "AI_PROCESSING_FAILED", "original_input": user_input}.
Backend - Creation: Use standard POST /tasks/ endpoint, called by frontend.
Google AI Prompt (NLP Input): (Include the exact prompt text here as defined previously)
Frontend: Implement confirmation UI flow.
9. Feature: AI Task Breakdown
Backend Endpoint: POST /tasks/{task_id}/breakdown Requires Auth. Verify task ownership. Fetch parent task title/description from DB. Format Breakdown Prompt. Call gemini_utils.call_gemini(prompt). Handle Response: Success (returns dict): Validate structure ({"sub_tasks": list[str]}). If valid, for each sub-task string: Create a new Task record in DB (using SQLAlchemy), setting title and parent_task_id. Commit session. Failure (returns None): Return 422 {"error_code": "AI_BREAKDOWN_FAILED"}. Return 201 Created (or 200 OK) with list of created sub-task objects (TaskRead schema).
Google AI Prompt (Breakdown): (Include the exact prompt text here as defined previously)
Frontend: Add button. Update UI on success/show error on failure.
10. Feature: Promote Task
Backend Endpoint: POST /tasks/{task_id}/promote Requires Auth. Requires If-Match header. Fetch task from DB (check ownership, check parent_task_id is not null - 400 otherwise). Fetch parent task from DB. Get grandparent ID (parent's parent_task_id). Update current task's parent_task_id to grandparent ID. Update updated_at. Commit session. Return 200 OK with updated task object (TaskRead schema) and new Etag.
Frontend: Add button (visible for sub-tasks). Update UI on success.
11. Feature: "What's Next?" Focus Mode
Backend Endpoint: GET /tasks/next Requires Auth. Query DB using SQLAlchemy for tasks where user_id matches and status is 'todo' or 'inprogress'. Apply sorting: Task.priority.desc() (handle enum sorting appropriately), Task.due_date.asc().nullslast(), Task.created_at.asc(). Fetch the first result (.first()). Return 200 OK with the task object (TaskRead schema), or 204 No Content if no task found.
Frontend: Implement Focus Mode UI as described previously. Call /tasks/next to get task. Use PATCH /tasks/{task_id} to update status.
12. Frontend Requirements
Standard HTML/CSS/JS. Responsive.
Handle JWT Access Token storage (in-memory/sessionStorage) & sending.
Handle CSRF token for refresh.
Handle Etags (If-Match).
Render nested tasks visually.
Escape all user content (.textContent).
Implement all necessary views and user flows.
13. General Requirements & Operations
Structure: Logical project structure (e.g., separate folders for routers, models, services/utils). Use FastAPI routers.
Entrypoint: main.py sets up FastAPI app. Run with uvicorn main:app --reload.
Secrets: Use .env file and python-dotenv locally for JWT_SECRET_KEY, REFRESH_SECRET_KEY, GOOGLE_AI_API_KEY. Create a .env.example file excluding actual secrets. Add .env to .gitignore.
Testing (pytest): Implement tests covering core logic, auth, isolation. Mock external services (DB session, AI API). Use test database (e.g., separate SQLite file). Note potential bcrypt install needs.
CORS: Configure FastAPI CORS middleware for local development origin (e.g., http://localhost:8000 or frontend dev server port).
Dependencies: Use requirements.txt (pip freeze > requirements.txt) or pyproject.toml (if using Poetry). Specify Python version (e.g., 3.10+).
Database: Include instructions on initializing the SQLite DB (e.g., running a script to create tables based on SQLAlchemy models).

