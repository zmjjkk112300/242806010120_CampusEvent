"""站内通知观察者：把报名领域事件转换为站内消息。"""

from .constants import EVENT_APPROVED, EVENT_CANCELLED, EVENT_REJECTED, EVENT_SUBMITTED
from .events import RegistrationEvent
from .models import Message


class InAppNotificationObserver:
    """写入站内消息。

    事务边界：观察者在独立会话中写入并提交，与报名事务解耦。
    若写入失败，异常交由事件总线记录，报名记录仍然有效。
    """

    TEMPLATES = {
        EVENT_APPROVED: "你报名的活动《{title}》已通过。",
        EVENT_SUBMITTED: "你报名的活动《{title}》已提交，等待管理员审核。",
        EVENT_REJECTED: "很遗憾，你报名的活动《{title}》未通过审核。",
        EVENT_CANCELLED: "你已取消活动《{title}》的报名。",
    }

    def __init__(self, session_factory, logger=None):
        self._session_factory = session_factory
        self._logger = logger

    def build_content(self, event: RegistrationEvent) -> str:
        template = self.TEMPLATES.get(event.name, "活动《{title}》报名状态更新。")
        return template.format(title=event.activity_title or "未命名活动")

    def handle(self, event: RegistrationEvent) -> None:
        content = self.build_content(event)
        session = self._session_factory()
        try:
            exists = (
                session.query(Message)
                .filter(Message.student_id == event.student_id, Message.event_key == event.event_key)
                .first()
            )
            if exists is not None:
                # 幂等：同一事件重复投递不产生第二条通知
                if self._logger is not None:
                    self._logger.info("重复事件已忽略 event_key=%s", event.event_key)
                return
            session.add(
                Message(
                    student_id=event.student_id,
                    activity_id=event.activity_id,
                    content=content,
                    event_key=event.event_key,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
