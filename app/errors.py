"""业务异常：服务层抛出，路由层统一转换为中文提示，避免 500 与脏数据。"""


class DomainError(Exception):
    """业务规则不满足的基类。"""

    message = "操作失败"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message


class CapacityExceeded(DomainError):
    message = "名额已满，无法完成该操作"


class DuplicateRegistration(DomainError):
    message = "你已报名该活动，请勿重复报名"


class ActivityNotFound(DomainError):
    message = "活动不存在或已被删除"


class ActivityStarted(DomainError):
    message = "活动已开始，无法报名或取消报名"


class RegistrationNotFound(DomainError):
    message = "报名记录不存在"


class InvalidStatusTransition(DomainError):
    message = "当前状态不允许该操作"


class NotOwner(DomainError):
    message = "只能操作自己的报名记录"


class HasRegistrations(DomainError):
    message = "该活动已有报名记录，不能删除"


class UnknownPolicy(DomainError):
    message = "未知的报名方式"


class ValidationError(DomainError):
    message = "输入内容不合法"
