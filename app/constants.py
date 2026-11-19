"""领域常量：报名状态、活动报名方式、事件名。

状态值直接使用中文持久化，便于界面展示与数据库核查；
代码中一律通过枚举比较，禁止散落字符串字面量。
"""

from enum import Enum


class PolicyType(str, Enum):
    """活动报名方式。"""

    DIRECT = "direct"
    APPROVAL = "approval"

    @property
    def label(self) -> str:
        return {"direct": "直接报名", "approval": "管理员审核"}[self.value]


class RegistrationStatus(str, Enum):
    """报名记录状态。"""

    PENDING = "待审核"
    APPROVED = "已通过"
    REJECTED = "已拒绝"
    CANCELLED = "已取消"

    @property
    def is_active(self) -> bool:
        """有效报名：占用唯一性约束的状态。"""
        return self in (RegistrationStatus.PENDING, RegistrationStatus.APPROVED)


# 事件名常量：业务服务发布，通知观察者订阅
EVENT_SUBMITTED = "registration.submitted"
EVENT_APPROVED = "registration.approved"
EVENT_REJECTED = "registration.rejected"
EVENT_CANCELLED = "registration.cancelled"

ALL_EVENTS = (EVENT_SUBMITTED, EVENT_APPROVED, EVENT_REJECTED, EVENT_CANCELLED)
