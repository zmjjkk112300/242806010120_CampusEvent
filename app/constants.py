"""领域常量：报名状态、活动报名方式、事件名。

状态值直接使用中文持久化，便于界面展示与数据库核查；
代码中一律通过枚举比较，禁止散落字符串字面量。
"""

from enum import Enum

# 版本标识（v2 = 完成 CR-01 / CR-02 变更后的版本）
APP_VERSION = "change-v2"


class PolicyType(str, Enum):
    """活动报名方式。"""

    DIRECT = "direct"
    APPROVAL = "approval"
    GRADE_DIRECT = "grade_direct"   # v2 / CR-01：年级限定直接报名

    @property
    def label(self) -> str:
        return {
            "direct": "直接报名",
            "approval": "管理员审核",
            "grade_direct": "年级限定直接报名",
        }[self.value]


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

# 需要发送邮件的业务事件（v2 / CR-02）：报名通过、审核通过、审核拒绝
EMAIL_EVENTS = (EVENT_APPROVED, EVENT_REJECTED)


class EmailStatus(str, Enum):
    """模拟邮件发送状态。"""

    SENT = "已发送"
    FAILED = "发送失败"
