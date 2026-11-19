"""基础设施：引擎、会话工厂、事件总线。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from .constants import ALL_EVENTS
from .events import DomainEventBus
from .models import Base
from .notifications import InAppNotificationObserver

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


def session() -> Session:
    """当前请求使用的会话（同一请求内复用）。"""
    return _state["scoped"]()


def session_factory() -> Session:
    """新建一个独立会话，供通知观察者使用（与业务事务解耦，调用方负责关闭）。"""
    return _state["factory"]()


def remove_session() -> None:
    if "scoped" in _state:
        _state["scoped"].remove()


def init_event_bus(logger=None) -> DomainEventBus:
    bus = DomainEventBus(logger=logger)
    observer = InAppNotificationObserver(session_factory, logger=logger)
    bus.subscribe_all(observer.handle, list(ALL_EVENTS))
    _state["bus"] = bus
    return bus


def event_bus() -> DomainEventBus:
    return _state["bus"]
