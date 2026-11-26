"""报名策略（策略模式）。

设计要点
--------
* ``RegistrationPolicy`` 定义稳定抽象：只回答“报名提交后应处于什么状态、产生什么事件”。
* 直接报名与审核报名是两种实现，新增规则 = 新增实现并在注册表登记，主流程零改动。
* 名额检查属于**公共不变量**，不在策略内部各自实现；策略只声明
  ``occupies_capacity_on_submit``，由服务决定校验时点（见 ``services.RegistrationService``）。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from .constants import (
    EVENT_APPROVED,
    EVENT_SUBMITTED,
    PolicyType,
    RegistrationStatus,
)
from .errors import GradeNotAllowed, UnknownPolicy
from .models import Activity, Student


@dataclass(frozen=True)
class RegistrationContext:
    """策略判断所需的只读上下文。"""

    activity: Activity
    student: Student
    approved_count: int
    now: datetime


@dataclass(frozen=True)
class RegistrationDecision:
    """策略结论：报名记录初始状态 + 需发布的事件名。"""

    status: RegistrationStatus
    event_type: str


class RegistrationPolicy(ABC):
    policy_type: PolicyType
    label: str = ""
    occupies_capacity_on_submit: bool = False

    @abstractmethod
    def decide(self, context: RegistrationContext) -> RegistrationDecision:
        """返回报名提交后的初始状态与事件。"""


class RegistrationRule(ABC):
    """可组合的附加规则（v2 / CR-01）。

    规则只回答“是否放行”，不改变报名最终状态；因此可以与任意策略组合，
    例如“直接报名 + 年级限定”，而无需为核心服务增加分支。
    """

    label: str = ""

    @abstractmethod
    def check(self, context: RegistrationContext) -> None:
        """不满足规则时抛出 DomainError 子类。"""


class GradeRangeRule(RegistrationRule):
    """年级范围规则：闭区间 [min_grade, max_grade]，未配置的一端视为不限。"""

    label = "年级限定"

    GRADE_TEXT = {1: "大一", 2: "大二", 3: "大三", 4: "大四"}

    def check(self, context: RegistrationContext) -> None:
        low = context.activity.min_grade
        high = context.activity.max_grade
        if low is None and high is None:
            return
        low = low if low is not None else 1
        high = high if high is not None else 4
        grade = context.student.grade
        if low <= grade <= high:
            return
        allowed = f"{self.GRADE_TEXT.get(low, low)}—{self.GRADE_TEXT.get(high, high)}"
        raise GradeNotAllowed(
            f"该活动仅面向{allowed}学生报名，你当前是{context.student.grade_label}，不符合报名条件"
        )


class CompositePolicy(RegistrationPolicy):
    """策略 + 规则链：先依次校验规则，再交由内层策略决定状态。"""

    def __init__(
        self,
        policy_type: PolicyType,
        inner: RegistrationPolicy,
        rules: list[RegistrationRule] | None = None,
        label: str | None = None,
    ):
        self.policy_type = policy_type
        self.inner = inner
        self.rules = list(rules or [])
        self.label = label or inner.label
        self.occupies_capacity_on_submit = inner.occupies_capacity_on_submit

    def decide(self, context: RegistrationContext) -> RegistrationDecision:
        for rule in self.rules:
            rule.check(context)
        return self.inner.decide(context)


class DirectRegistrationPolicy(RegistrationPolicy):
    policy_type = PolicyType.DIRECT
    label = "直接报名"
    occupies_capacity_on_submit = True

    def decide(self, context: RegistrationContext) -> RegistrationDecision:
        return RegistrationDecision(RegistrationStatus.APPROVED, EVENT_APPROVED)


class ApprovalRegistrationPolicy(RegistrationPolicy):
    policy_type = PolicyType.APPROVAL
    label = "管理员审核"
    occupies_capacity_on_submit = False

    def decide(self, context: RegistrationContext) -> RegistrationDecision:
        return RegistrationDecision(RegistrationStatus.PENDING, EVENT_SUBMITTED)


class GradeLimitedDirectPolicy(CompositePolicy):
    """v2 / CR-01：直接报名 + 年级限定规则。"""

    def __init__(self):
        super().__init__(
            policy_type=PolicyType.GRADE_DIRECT,
            inner=DirectRegistrationPolicy(),
            rules=[GradeRangeRule()],
            label="年级限定直接报名",
        )


class PolicyRegistry:
    """策略注册表：按 policy_type 取实现，避免服务层出现 if/elif 分支。"""

    def __init__(self, policies: list[RegistrationPolicy] | None = None):
        self._policies: dict[PolicyType, RegistrationPolicy] = {}
        for policy in policies or [
            DirectRegistrationPolicy(),
            ApprovalRegistrationPolicy(),
            GradeLimitedDirectPolicy(),
        ]:
            self.register(policy)

    def register(self, policy: RegistrationPolicy) -> None:
        self._policies[policy.policy_type] = policy

    def get(self, policy_type: PolicyType | str) -> RegistrationPolicy:
        try:
            key = PolicyType(policy_type)
        except ValueError as exc:  # 未知报名方式
            raise UnknownPolicy(f"未知的报名方式：{policy_type}") from exc
        return self._policies[key]

    @property
    def all(self) -> list[RegistrationPolicy]:
        return list(self._policies.values())


default_registry = PolicyRegistry()
