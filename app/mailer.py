"""模拟邮件发送器（v2 / CR-02）。

教学场景不接入真实邮件服务器，由 ``MockEmailSender`` 模拟投递：
* 正常时仅记录一条发送时间并返回；
* 可通过 ``fail_times`` 注入故障，用于验证“发送失败不影响报名结果”；
* 真正的收件人、主题、内容、状态落库由 ``EmailNotificationObserver`` 负责。
"""

from abc import ABC, abstractmethod
from datetime import datetime

from .errors import EmailSendFailed


class EmailSender(ABC):
    """邮件发送端口：更换真实实现时只替换该类，不改观察者与业务代码。"""

    @abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> datetime:
        """投递邮件并返回投递时间；失败时抛 :class:`EmailSendFailed`。"""


class MockEmailSender(EmailSender):
    def __init__(self, fail_times: int = 0, logger=None):
        self.fail_times = fail_times
        self._logger = logger
        self.sent: list[tuple[str, str, str]] = []

    def send(self, recipient: str, subject: str, body: str) -> datetime:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise EmailSendFailed("模拟邮件服务器不可用（fail_times 注入）")
        self.sent.append((recipient, subject, body))
        if self._logger is not None:
            self._logger.info("模拟邮件已投递 recipient=%s subject=%s", recipient, subject)
        return datetime.now()
