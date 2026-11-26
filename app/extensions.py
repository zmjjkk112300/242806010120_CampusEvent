"""基础设施：引擎、会话工厂、事件总线。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from .constants import ALL_EVENTS, EMAIL_EVENTS
from .events import DomainEventBus
from .mailer import MockEmailSender
from .models import Base
from .notifications import EmailNotificationObserver, InAppNotificationObserver

_state: dict = {}


def init_engine(database_uri: str) -> None:
    connect_args = {"check_same_thread": False} if database_uri.startswith("sqlite") else {}
    engine = create_engine(database_uri, future=True, connect_args=connect_args)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    _state["engine"] = engine
    _state["factory"] = factory
    _state["scoped"] = scoped_session(factory)


def create_all() -> None:
    Base.metadata.create_all(_state["engine"])


def ensure_schema() -> list[str]:
    """v2 轻量迁移：为已有 SQLite 库补上 CR-01/CR-02 新增列。

    ``create_all`` 只建新表、不改旧表，因此这里按列名检查后 ``ALTER TABLE``。
    返回执行过的迁移动作，便于启动日志留痕；非 SQLite 数据库直接跳过。
    """

    engine = _state["engine"]
    if engine.dialect.name != "sqlite":
        return []

    actions: list[str] = []
    additions = {
        "students": [
            ("grade", "INTEGER NOT NULL DEFAULT 1"),
            ("email", "VARCHAR(120) NOT NULL DEFAULT ''"),
        ],
        "activities": [
            ("min_grade", "INTEGER"),
            ("max_grade", "INTEGER"),
        ],
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, ddl in columns:
                if name in existing:
                    continue
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                actions.append(f"{table}.{name}")
        if "students.grade" in actions:
            # 已有演示账号补回真实年级与邮箱，避免迁移后一律变成大一
            for student_id, grade, email in (
                ("S001", 3, "s001@campus.example.edu"),
                ("S002", 2, "s002@campus.example.edu"),
                ("S003", 1, "s003@campus.example.edu"),
            ):
                conn.exec_driver_sql(
                    "UPDATE students SET grade = ?, email = ? WHERE student_id = ?",
                    (grade, email, student_id),
                )
    return actions


def session() -> Session:
    """当前请求使用的会话（同一请求内复用）。"""
    return _state["scoped"]()


def session_factory() -> Session:
    """新建一个独立会话，供通知观察者使用（与业务事务解耦，调用方负责关闭）。"""
    return _state["factory"]()


def remove_session() -> None:
    if "scoped" in _state:
        _state["scoped"].remove()


def init_event_bus(logger=None, email_sender=None, email_fail_times: int = 0) -> DomainEventBus:
    bus = DomainEventBus(logger=logger)
    observer = InAppNotificationObserver(session_factory, logger=logger)
    bus.subscribe_all(observer.handle, list(ALL_EVENTS))

    # v2 / CR-02：邮件观察者与站内消息观察者并列订阅，互不影响
    sender = email_sender or MockEmailSender(fail_times=email_fail_times, logger=logger)
    email_observer = EmailNotificationObserver(session_factory, sender, logger=logger)
    bus.subscribe_all(email_observer.handle, list(EMAIL_EVENTS))

    _state["bus"] = bus
    _state["email_sender"] = sender
    return bus


def event_bus() -> DomainEventBus:
    return _state["bus"]


def email_sender():
    """当前装配的邮件发送器（测试可读取投递记录）。"""
    return _state.get("email_sender")
