"""
Database models and utilities for CogniTask AI.
Uses SQLAlchemy ORM with SQLite.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, case
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Database setup
DATABASE_URL = "sqlite:///cognitask.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Priority order for sorting (higher number = higher priority)
PRIORITY_ORDER = {
    "urgent": 4,
    "high": 3,
    "medium": 2,
    "low": 1
}

VALID_STATUSES = ["todo", "inprogress", "done", "blocked"]
VALID_PRIORITIES = ["low", "medium", "high", "urgent"]


class Task(Base):
    """Task model for storing tasks in the database."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="todo", index=True)
    priority = Column(String(20), nullable=False, default="medium", index=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    parent_task_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date,
            "parent_task_id": self.parent_task_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get a database session."""
    return SessionLocal()


def generate_task_id() -> str:
    """Generate a unique task ID."""
    return str(uuid.uuid4())


# --- CRUD Operations ---

def create_task(
    db: Session,
    title: str,
    description: str | None = None,
    status: str = "todo",
    priority: str = "medium",
    due_date: datetime | None = None,
    parent_task_id: str | None = None
) -> Task:
    """Create a new task."""
    task = Task(
        task_id=generate_task_id(),
        title=title,
        description=description,
        status=status if status in VALID_STATUSES else "todo",
        priority=priority if priority in VALID_PRIORITIES else "medium",
        due_date=due_date,
        parent_task_id=parent_task_id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task_by_id(db: Session, task_id: str) -> Task | None:
    """Get a task by its task_id."""
    return db.query(Task).filter(Task.task_id == task_id).first()


def get_all_tasks(db: Session) -> list[Task]:
    """Get all tasks ordered by creation date (newest first)."""
    return db.query(Task).order_by(Task.created_at.desc()).all()


def get_tasks_by_status(db: Session, status: str) -> list[Task]:
    """Get all tasks with a specific status."""
    return db.query(Task).filter(Task.status == status).order_by(Task.created_at.desc()).all()


def get_incomplete_tasks(db: Session) -> list[Task]:
    """Get all incomplete tasks (todo or inprogress)."""
    return db.query(Task).filter(Task.status.in_(["todo", "inprogress"])).all()


def get_subtasks(db: Session, parent_task_id: str) -> list[Task]:
    """Get all subtasks of a given parent task."""
    return db.query(Task).filter(Task.parent_task_id == parent_task_id).order_by(Task.created_at.asc()).all()


def has_subtasks(db: Session, task_id: str) -> bool:
    """Check if a task has any subtasks."""
    return db.query(Task).filter(Task.parent_task_id == task_id).count() > 0


def get_root_tasks(db: Session) -> list[Task]:
    """Get all tasks that don't have a parent (root level)."""
    return db.query(Task).filter(Task.parent_task_id == None).order_by(Task.created_at.desc()).all()


def update_task(
    db: Session,
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_date: datetime | None = None,
    parent_task_id: str | None = None,
    clear_due_date: bool = False,
    clear_parent: bool = False
) -> Task | None:
    """Update an existing task. Returns None if task not found."""
    task = get_task_by_id(db, task_id)
    if not task:
        return None

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if status is not None and status in VALID_STATUSES:
        task.status = status
    if priority is not None and priority in VALID_PRIORITIES:
        task.priority = priority
    if due_date is not None:
        task.due_date = due_date
    if clear_due_date:
        task.due_date = None
    if parent_task_id is not None:
        task.parent_task_id = parent_task_id
    if clear_parent:
        task.parent_task_id = None

    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: str) -> bool:
    """Delete a task. Returns False if task not found or has subtasks."""
    task = get_task_by_id(db, task_id)
    if not task:
        return False

    if has_subtasks(db, task_id):
        return False

    db.delete(task)
    db.commit()
    return True


def get_next_priority_task(db: Session) -> Task | None:
    """
    Get the highest priority incomplete task for Focus Mode.
    Priority order: urgent > high > medium > low
    Tie-breaker: earliest due date (nulls last), then oldest created
    """
    # Create a case statement for priority ordering
    priority_case = case(
        (Task.priority == "urgent", 4),
        (Task.priority == "high", 3),
        (Task.priority == "medium", 2),
        (Task.priority == "low", 1),
        else_=0
    )

    return (
        db.query(Task)
        .filter(Task.status.in_(["todo", "inprogress"]))
        .order_by(
            priority_case.desc(),  # Higher priority first
            Task.due_date.asc().nullslast(),  # Earlier due dates first, nulls last
            Task.created_at.asc()  # Older tasks first
        )
        .first()
    )


def get_task_stats(db: Session) -> dict:
    """Get statistics about tasks."""
    total = db.query(Task).count()
    todo = db.query(Task).filter(Task.status == "todo").count()
    inprogress = db.query(Task).filter(Task.status == "inprogress").count()
    done = db.query(Task).filter(Task.status == "done").count()
    blocked = db.query(Task).filter(Task.status == "blocked").count()

    # Count overdue tasks
    now = datetime.now(timezone.utc)
    overdue = db.query(Task).filter(
        Task.due_date < now,
        Task.status.in_(["todo", "inprogress"])
    ).count()

    return {
        "total": total,
        "todo": todo,
        "inprogress": inprogress,
        "done": done,
        "blocked": blocked,
        "overdue": overdue
    }
