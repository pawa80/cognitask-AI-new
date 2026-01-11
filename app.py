"""
CogniTask AI - An AI-enhanced task manager built with Streamlit.
"""

import streamlit as st
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser

import database as db
import gemini_utils

# --- Page Configuration ---
st.set_page_config(
    page_title="CogniTask AI",
    page_icon="brain",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Initialize Database ---
db.init_db()


# --- Session State Initialization ---
def init_session_state():
    """Initialize session state variables."""
    if "current_view" not in st.session_state:
        st.session_state.current_view = "tasks"
    if "editing_task_id" not in st.session_state:
        st.session_state.editing_task_id = None
    if "show_add_form" not in st.session_state:
        st.session_state.show_add_form = False
    if "show_ai_input" not in st.session_state:
        st.session_state.show_ai_input = False
    if "ai_parsed_task" not in st.session_state:
        st.session_state.ai_parsed_task = None
    if "breakdown_task_id" not in st.session_state:
        st.session_state.breakdown_task_id = None
    if "breakdown_subtasks" not in st.session_state:
        st.session_state.breakdown_subtasks = None


init_session_state()


# --- Helper Functions ---
def format_date(dt: datetime | None) -> str:
    """Format a datetime for display."""
    if dt is None:
        return "No due date"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%b %d, %Y")


def get_priority_color(priority: str) -> str:
    """Get color for priority badge."""
    colors = {
        "urgent": "red",
        "high": "orange",
        "medium": "blue",
        "low": "gray"
    }
    return colors.get(priority, "gray")


def get_status_emoji(status: str) -> str:
    """Get emoji for status."""
    emojis = {
        "todo": "[ ]",
        "inprogress": "[~]",
        "done": "[x]",
        "blocked": "[!]"
    }
    return emojis.get(status, "[ ]")


def parse_due_date(date_str: str | None) -> datetime | None:
    """Parse a date string to datetime."""
    if not date_str:
        return None
    try:
        return date_parser.parse(date_str).replace(tzinfo=timezone.utc)
    except Exception:
        return None


# --- Sidebar ---
def render_sidebar():
    """Render the sidebar with navigation and stats."""
    with st.sidebar:
        st.title("CogniTask AI")

        # Navigation
        st.subheader("Navigation")
        if st.button("Task List", use_container_width=True,
                     type="primary" if st.session_state.current_view == "tasks" else "secondary"):
            st.session_state.current_view = "tasks"
            st.rerun()

        if st.button("Focus Mode", use_container_width=True,
                     type="primary" if st.session_state.current_view == "focus" else "secondary"):
            st.session_state.current_view = "focus"
            st.rerun()

        st.divider()

        # Stats
        st.subheader("Stats")
        session = db.get_db()
        try:
            stats = db.get_task_stats(session)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total", stats["total"])
                st.metric("To Do", stats["todo"])
                st.metric("Done", stats["done"])
            with col2:
                st.metric("In Progress", stats["inprogress"])
                st.metric("Blocked", stats["blocked"])
                if stats["overdue"] > 0:
                    st.metric("Overdue", stats["overdue"])
        finally:
            session.close()

        st.divider()

        # AI Status
        st.subheader("AI Status")
        if gemini_utils.is_configured():
            st.success("Gemini AI connected")
        else:
            st.warning("AI not configured")
            st.caption("Add GOOGLE_AI_API_KEY to .streamlit/secrets.toml")


# --- Task List View ---
def render_task_list():
    """Render the main task list view."""
    st.header("Tasks")

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("+ Add Task", use_container_width=True):
            st.session_state.show_add_form = not st.session_state.show_add_form
            st.session_state.show_ai_input = False
            st.session_state.ai_parsed_task = None
            st.rerun()

    with col2:
        if st.button("+ AI Add", use_container_width=True, disabled=not gemini_utils.is_configured()):
            st.session_state.show_ai_input = not st.session_state.show_ai_input
            st.session_state.show_add_form = False
            st.rerun()

    # Filter controls
    with col3:
        filter_status = st.selectbox(
            "Filter by status",
            ["All", "To Do", "In Progress", "Done", "Blocked"],
            label_visibility="collapsed"
        )

    # Add task form
    if st.session_state.show_add_form:
        render_add_task_form()

    # AI input form
    if st.session_state.show_ai_input:
        render_ai_input_form()

    # Get and display tasks
    session = db.get_db()
    try:
        status_map = {
            "All": None,
            "To Do": "todo",
            "In Progress": "inprogress",
            "Done": "done",
            "Blocked": "blocked"
        }
        status_filter = status_map.get(filter_status)

        if status_filter:
            all_tasks = db.get_tasks_by_status(session, status_filter)
        else:
            all_tasks = db.get_all_tasks(session)

        if not all_tasks:
            st.info("No tasks yet. Add your first task above!")
        else:
            # Build task hierarchy
            render_task_hierarchy(session, all_tasks)

    finally:
        session.close()


def render_add_task_form():
    """Render the manual add task form."""
    with st.expander("Add New Task", expanded=True):
        with st.form("add_task_form"):
            title = st.text_input("Title*", max_chars=255)
            description = st.text_area("Description (optional)", max_chars=10000)

            col1, col2 = st.columns(2)
            with col1:
                priority = st.selectbox("Priority", ["medium", "low", "high", "urgent"])
            with col2:
                due_date = st.date_input("Due Date (optional)", value=None)

            # Parent task selection
            session = db.get_db()
            try:
                all_tasks = db.get_all_tasks(session)
                task_options = {"None": None}
                for task in all_tasks:
                    task_options[f"{task.title[:50]}..."] = task.task_id
                parent = st.selectbox("Parent Task (optional)", options=list(task_options.keys()))
            finally:
                session.close()

            submitted = st.form_submit_button("Create Task", use_container_width=True)

            if submitted:
                if not title.strip():
                    st.error("Title is required")
                else:
                    session = db.get_db()
                    try:
                        due_dt = datetime.combine(due_date, datetime.min.time()).replace(tzinfo=timezone.utc) if due_date else None
                        parent_id = task_options.get(parent)

                        db.create_task(
                            session,
                            title=title.strip(),
                            description=description.strip() if description else None,
                            priority=priority,
                            due_date=due_dt,
                            parent_task_id=parent_id
                        )
                        st.success("Task created!")
                        st.session_state.show_add_form = False
                        st.rerun()
                    finally:
                        session.close()


def render_ai_input_form():
    """Render the AI-powered task input form."""
    with st.expander("AI Task Input", expanded=True):
        st.caption("Describe your task naturally, and AI will parse it for you.")

        user_input = st.text_area(
            "What do you need to do?",
            placeholder="e.g., Call mom tomorrow - it's urgent\ne.g., Finish the report by Friday, high priority",
            key="ai_input_text"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Parse with AI", use_container_width=True):
                if user_input.strip():
                    with st.spinner("AI is parsing your input..."):
                        result = gemini_utils.parse_task_input(user_input)
                        if result:
                            st.session_state.ai_parsed_task = result
                            st.rerun()
                        else:
                            st.error("Failed to parse input. Try being more specific.")
                else:
                    st.warning("Please enter a task description")

        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_ai_input = False
                st.session_state.ai_parsed_task = None
                st.rerun()

        # Show parsed result for confirmation
        if st.session_state.ai_parsed_task:
            st.divider()
            st.subheader("Parsed Task Preview")

            parsed = st.session_state.ai_parsed_task

            with st.form("confirm_ai_task"):
                title = st.text_input("Title", value=parsed.get("title", ""), max_chars=255)
                description = st.text_area("Description", value=parsed.get("description") or "")
                priority = st.selectbox(
                    "Priority",
                    ["low", "medium", "high", "urgent"],
                    index=["low", "medium", "high", "urgent"].index(parsed.get("priority", "medium"))
                )
                due_str = parsed.get("due_date")
                if due_str:
                    try:
                        due_val = date_parser.parse(due_str).date()
                    except Exception:
                        due_val = None
                else:
                    due_val = None
                due_date = st.date_input("Due Date", value=due_val)

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Create Task", use_container_width=True, type="primary"):
                        if title.strip():
                            session = db.get_db()
                            try:
                                due_dt = datetime.combine(due_date, datetime.min.time()).replace(tzinfo=timezone.utc) if due_date else None
                                db.create_task(
                                    session,
                                    title=title.strip(),
                                    description=description.strip() if description else None,
                                    priority=priority,
                                    due_date=due_dt
                                )
                                st.success("Task created!")
                                st.session_state.ai_parsed_task = None
                                st.session_state.show_ai_input = False
                                st.rerun()
                            finally:
                                session.close()
                        else:
                            st.error("Title is required")

                with col2:
                    if st.form_submit_button("Discard", use_container_width=True):
                        st.session_state.ai_parsed_task = None
                        st.rerun()


def render_task_hierarchy(session, all_tasks: list):
    """Render tasks in a hierarchical view."""
    # Build lookup maps
    tasks_by_id = {t.task_id: t for t in all_tasks}
    children_map = {}
    for task in all_tasks:
        if task.parent_task_id:
            if task.parent_task_id not in children_map:
                children_map[task.parent_task_id] = []
            children_map[task.parent_task_id].append(task)

    # Find root tasks (no parent or parent not in current view)
    root_tasks = [t for t in all_tasks if not t.parent_task_id or t.parent_task_id not in tasks_by_id]

    def render_task(task, indent_level=0):
        """Render a single task with its children."""
        indent = "    " * indent_level

        # Check if we're editing this task
        is_editing = st.session_state.editing_task_id == task.task_id
        is_breaking_down = st.session_state.breakdown_task_id == task.task_id

        with st.container():
            # Task header
            status_emoji = get_status_emoji(task.status)
            priority_color = get_priority_color(task.priority)

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                task_label = f"{indent}{status_emoji} **{task.title}**"
                if task.priority in ["urgent", "high"]:
                    task_label += f" :{priority_color}[{task.priority}]"
                st.markdown(task_label)

                if task.due_date:
                    due_str = format_date(task.due_date)
                    now = datetime.now(timezone.utc)
                    task_due = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)
                    if task_due < now and task.status not in ["done"]:
                        st.caption(f"{indent}:red[Overdue: {due_str}]")
                    else:
                        st.caption(f"{indent}Due: {due_str}")

            with col2:
                status_display = task.status.replace("inprogress", "in progress")
                st.caption(status_display)

            with col3:
                if st.button("Edit", key=f"edit_{task.task_id}", use_container_width=True):
                    st.session_state.editing_task_id = task.task_id if not is_editing else None
                    st.session_state.breakdown_task_id = None
                    st.rerun()

        # Edit form
        if is_editing:
            render_edit_task_form(session, task)

        # Breakdown form
        if is_breaking_down:
            render_breakdown_form(session, task)

        # Render children
        children = children_map.get(task.task_id, [])
        for child in children:
            render_task(child, indent_level + 1)

    # Render all root tasks
    for task in root_tasks:
        render_task(task)
        st.divider()


def render_edit_task_form(session, task):
    """Render the edit form for a task."""
    with st.container():
        st.subheader("Edit Task")

        with st.form(f"edit_form_{task.task_id}"):
            title = st.text_input("Title", value=task.title, max_chars=255)
            description = st.text_area("Description", value=task.description or "")

            col1, col2 = st.columns(2)
            with col1:
                status = st.selectbox(
                    "Status",
                    ["todo", "inprogress", "done", "blocked"],
                    index=["todo", "inprogress", "done", "blocked"].index(task.status)
                )
            with col2:
                priority = st.selectbox(
                    "Priority",
                    ["low", "medium", "high", "urgent"],
                    index=["low", "medium", "high", "urgent"].index(task.priority)
                )

            due_val = task.due_date.date() if task.due_date else None
            due_date = st.date_input("Due Date", value=due_val)
            clear_due = st.checkbox("Clear due date")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.form_submit_button("Save", use_container_width=True, type="primary"):
                    if title.strip():
                        due_dt = datetime.combine(due_date, datetime.min.time()).replace(tzinfo=timezone.utc) if due_date and not clear_due else None
                        db.update_task(
                            session,
                            task.task_id,
                            title=title.strip(),
                            description=description.strip() if description else None,
                            status=status,
                            priority=priority,
                            due_date=due_dt,
                            clear_due_date=clear_due
                        )
                        st.session_state.editing_task_id = None
                        st.rerun()
                    else:
                        st.error("Title is required")

            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.editing_task_id = None
                    st.rerun()

            with col3:
                if st.form_submit_button("Breakdown", use_container_width=True, disabled=not gemini_utils.is_configured()):
                    st.session_state.breakdown_task_id = task.task_id
                    st.session_state.editing_task_id = None
                    st.rerun()

            with col4:
                if st.form_submit_button("Delete", use_container_width=True):
                    if db.has_subtasks(session, task.task_id):
                        st.error("Cannot delete: task has subtasks")
                    else:
                        db.delete_task(session, task.task_id)
                        st.session_state.editing_task_id = None
                        st.rerun()


def render_breakdown_form(session, task):
    """Render the AI breakdown form for a task."""
    with st.container():
        st.subheader(f"Break Down: {task.title}")

        if st.session_state.breakdown_subtasks is None:
            if st.button("Generate Sub-tasks with AI", key=f"gen_breakdown_{task.task_id}"):
                with st.spinner("AI is breaking down your task..."):
                    subtasks = gemini_utils.breakdown_task(task.title, task.description)
                    if subtasks:
                        st.session_state.breakdown_subtasks = subtasks
                        st.rerun()
                    else:
                        st.error("Failed to generate sub-tasks. Try again.")

            if st.button("Cancel", key=f"cancel_breakdown_{task.task_id}"):
                st.session_state.breakdown_task_id = None
                st.rerun()

        else:
            st.write("**Suggested sub-tasks:**")
            for i, subtask in enumerate(st.session_state.breakdown_subtasks):
                st.write(f"{i+1}. {subtask}")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Create All", key=f"create_all_{task.task_id}", type="primary"):
                    for subtask_title in st.session_state.breakdown_subtasks:
                        db.create_task(
                            session,
                            title=subtask_title,
                            parent_task_id=task.task_id,
                            priority=task.priority  # Inherit parent priority
                        )
                    st.session_state.breakdown_task_id = None
                    st.session_state.breakdown_subtasks = None
                    st.success(f"Created {len(st.session_state.breakdown_subtasks)} sub-tasks!")
                    st.rerun()

            with col2:
                if st.button("Regenerate", key=f"regen_{task.task_id}"):
                    st.session_state.breakdown_subtasks = None
                    st.rerun()

            with col3:
                if st.button("Cancel", key=f"cancel2_{task.task_id}"):
                    st.session_state.breakdown_task_id = None
                    st.session_state.breakdown_subtasks = None
                    st.rerun()


# --- Focus Mode View ---
def render_focus_mode():
    """Render the Focus Mode view."""
    st.header("Focus Mode")
    st.caption("What should you work on next?")

    session = db.get_db()
    try:
        task = db.get_next_priority_task(session)

        if not task:
            st.info("You're all caught up! No pending tasks.")
            if st.button("Go to Task List"):
                st.session_state.current_view = "tasks"
                st.rerun()
            return

        # Display the priority task prominently
        st.divider()

        priority_color = get_priority_color(task.priority)
        st.markdown(f"### {task.title}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Priority:** :{priority_color}[{task.priority.upper()}]")
        with col2:
            st.markdown(f"**Status:** {task.status}")
        with col3:
            if task.due_date:
                st.markdown(f"**Due:** {format_date(task.due_date)}")
            else:
                st.markdown("**Due:** Not set")

        if task.description:
            st.markdown("**Description:**")
            st.write(task.description)

        st.divider()

        # Action buttons
        st.subheader("Quick Actions")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Mark Done", use_container_width=True, type="primary"):
                db.update_task(session, task.task_id, status="done")
                st.success("Marked as done!")
                st.rerun()

        with col2:
            if task.status == "todo":
                if st.button("Start Working", use_container_width=True):
                    db.update_task(session, task.task_id, status="inprogress")
                    st.rerun()
            else:
                if st.button("Back to To Do", use_container_width=True):
                    db.update_task(session, task.task_id, status="todo")
                    st.rerun()

        with col3:
            if st.button("Mark Blocked", use_container_width=True):
                db.update_task(session, task.task_id, status="blocked")
                st.rerun()

        with col4:
            if st.button("Edit Task", use_container_width=True):
                st.session_state.current_view = "tasks"
                st.session_state.editing_task_id = task.task_id
                st.rerun()

        # Show sub-tasks if any
        subtasks = db.get_subtasks(session, task.task_id)
        if subtasks:
            st.divider()
            st.subheader("Sub-tasks")
            for subtask in subtasks:
                status_emoji = get_status_emoji(subtask.status)
                st.write(f"{status_emoji} {subtask.title}")

        # Progress indicator
        st.divider()
        stats = db.get_task_stats(session)
        total_incomplete = stats["todo"] + stats["inprogress"]
        if total_incomplete > 0:
            st.caption(f"{total_incomplete} task(s) remaining")

    finally:
        session.close()


# --- Main App ---
def main():
    """Main application entry point."""
    render_sidebar()

    if st.session_state.current_view == "tasks":
        render_task_list()
    elif st.session_state.current_view == "focus":
        render_focus_mode()


if __name__ == "__main__":
    main()
