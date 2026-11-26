"""领域事件与事件总线（观察者模式的载体）。

* 业务服务只负责 ``publish``，不关心谁来消费；
* 通知观察者订阅全部报名相关事件，负责把事件转换为站内消息；
* 单个观察者抛出异常被总线捕获并记录，不会反向影响已提交的报名事务。
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from .constants import RegistrationStatus


@dataclass(frozen=True)
class RegistrationEvent:
    """报名领域事件。``event_key`` 为幂等键，用于避免重复通知。"""

    name: str
    registration_id: int
    activity_id: int
    student_id: str
    status: RegistrationStatus
    activity_title: str = ""
    occurred_at: datetime = field(default_factory=datetime.now)

    @property
    def event_key(self) -> str:
        return f"{self.name}:{self.registration_id}"


EventHandler = Callable[[RegistrationEvent], None]


class DomainEventBus:
    """同步事件总线：注册处理器、发布事件、收集失败。"""

    def __init__(self, logger=None):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self.failures: list[tuple[RegistrationEvent, Exception]] = []
        self._logger = logger

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    def subscribe_all(self, handler: EventHandler, event_names: list[str]) -> None:
        for name in event_names:
            self.subscribe(name, handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """取消订阅（测试与热插拔场景使用）。"""
        handlers = self._handlers.get(event_name, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: RegistrationEvent) -> list[Exception]:
        """发布事件；处理器异常被吞掉并留痕，保证主流程继续。"""

        errors: list[Exception] = []
        for handler in list(self._handlers.get(event.name, [])):
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - 通知失败不应影响报名结果
                errors.append(exc)
                self.failures.append((event, exc))
                if self._logger is not None:
                    self._logger.error(
                        "事件处理器失败 event=%s registration=%s: %s",
                        event.name,
                        event.registration_id,
                        exc,
                    )
        return errors
