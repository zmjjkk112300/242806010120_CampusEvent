"""通知观察者：站内消息 + 模拟邮件（v2）。

* :class:`InAppNotificationObserver` —— 基线能力，写入站内消息；
* :class:`EmailNotificationObserver` —— CR-02 新增，订阅同一条领域事件发送模拟邮件，
  与站内消息互不影响，也不改动 ``RegistrationService``。
"""

from .constants import (
    EMAIL_EVENTS,
    EVENT_APPROVED,
    EVENT_CANCELLED,
    EVENT_REJECTED,
    EVENT_SUBMITTED,
    EmailStatus,
)
from .errors import EmailSendFailed
from .events import RegistrationEvent
from .models import EmailRecord, Message, Student


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


class EmailNotificationObserver:
    """CR-02：把报名事件转换为模拟邮件，并落一条发送记录。

    事务边界与站内消息一致：使用独立会话，失败只留痕，不回滚报名。
    ``(recipient, event_key)`` 唯一约束 + 发送前查重，保证同一业务事件只发一次。
    """

    SUBJECTS = {
        EVENT_APPROVED: "【CampusEvent】报名结果：已通过",
        EVENT_REJECTED: "【CampusEvent】报名结果：未通过",
    }
    BODIES = {
        EVENT_APPROVED: "你报名的活动《{title}》已通过，请按时参加。",
        EVENT_REJECTED: "很遗憾，你报名的活动《{title}》未通过审核。",
    }

    def __init__(self, session_factory, sender, logger=None):
        self._session_factory = session_factory
        self._sender = sender
        self._logger = logger

    def default_recipient(self, student: Student | None, student_id: str) -> str:
        if student is not None and student.email:
            return student.email
        return f"{student_id}@campus.example.edu"

    def handle(self, event: RegistrationEvent) -> None:
        if event.name not in EMAIL_EVENTS:
            return

        subject = self.SUBJECTS.get(event.name, "【CampusEvent】报名状态更新")
        body = self.BODIES.get(event.name, "活动《{title}》报名状态更新。").format(
            title=event.activity_title or "未命名活动"
        )

        session = self._session_factory()
        try:
            student = session.get(Student, event.student_id)
            recipient = self.default_recipient(student, event.student_id)

            exists = (
                session.query(EmailRecord)
                .filter(EmailRecord.recipient == recipient, EmailRecord.event_key == event.event_key)
                .first()
            )
            if exists is not None:
                # 幂等：同一业务事件重复投递只保留一条记录
                if self._logger is not None:
                    self._logger.info("重复邮件事件已忽略 event_key=%s", event.event_key)
                return

            status = EmailStatus.SENT.value
            error = ""
            try:
                self._sender.send(recipient, subject, body)
            except EmailSendFailed as exc:
                status = EmailStatus.FAILED.value
                error = str(exc)[:160]
                if self._logger is not None:
                    self._logger.error(
                        "模拟邮件发送失败 recipient=%s event_key=%s: %s",
                        recipient,
                        event.event_key,
                        exc,
                    )

            session.add(
                EmailRecord(
                    student_id=event.student_id,
                    activity_id=event.activity_id,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    status=status,
                    error=error,
                    event_key=event.event_key,
                )
            )
            session.commit()

            if status == EmailStatus.FAILED.value:
                # 失败记录已落库，再抛出以便事件总线统一留痕；报名事务早已提交
                raise EmailSendFailed(error)
        except EmailSendFailed:
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
