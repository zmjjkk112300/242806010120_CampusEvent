"""报名业务服务：唯一决定状态流转的地方。

职责边界
--------
* 公共不变量（活动存在、活动未开始、无重复有效报名、名额不超限）在服务内校验；
* “提交后处于什么状态”交给 ``RegistrationPolicy``（策略模式）；
* “状态变化后如何通知”交给事件总线 + 观察者（观察者模式）；
* 事件在报名事务提交后才发布，通知失败不回滚报名。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from .constants import (
    EVENT_APPROVED,
    EVENT_CANCELLED,
    EVENT_REJECTED,
    RegistrationStatus,
)
from .errors import (
    CapacityExceeded,
    DuplicateRegistration,
    InvalidStatusTransition,
    NotOwner,
    RegistrationNotFound,
    ValidationError,
    ActivityStarted,
)
from .events import DomainEventBus, RegistrationEvent
from .models import Registration, Student
from .policies import PolicyRegistry, RegistrationContext, default_registry
from .repositories import ActivityRepository, RegistrationRepository


class RegistrationService:
    def __init__(
        self,
        session: Session,
        bus: DomainEventBus,
        registry: PolicyRegistry | None = None,
        now_provider=datetime.now,
    ):
        self.session = session
        self.bus = bus
        self.registry = registry or default_registry
        self._now = now_provider
        self.activities = ActivityRepository(session)
        self.registrations = RegistrationRepository(session)

    # ------------------------------------------------------------------ 查询
    def approved_count(self, activity_id: int) -> int:
        return self.registrations.count_by_status(activity_id, RegistrationStatus.APPROVED)

    def pending_count(self, activity_id: int) -> int:
        return self.registrations.count_by_status(activity_id, RegistrationStatus.PENDING)

    def stats(self, activity_id: int) -> dict:
        activity = self.activities.get(activity_id)
        approved = self.approved_count(activity_id)
        pending = self.pending_count(activity_id)
        return {
            "capacity": activity.capacity,
            "approved": approved,
            "pending": pending,
            "remaining": max(activity.capacity - approved, 0),
        }

    # ------------------------------------------------------------------ 命令
    def register(self, activity_id: int, student_id: str) -> Registration:
        now = self._now()
        activity = self.activities.get(activity_id)
        if activity.start_at <= now:
            raise ActivityStarted()

        student = self.session.get(Student, student_id)
        if student is None:
            raise ValidationError("学生不存在，请使用演示账号登录")

        if self.registrations.active_of(activity_id, student_id) is not None:
            raise DuplicateRegistration()

        policy = self.registry.get(activity.policy_type)
        approved = self.approved_count(activity_id)
        if policy.occupies_capacity_on_submit and approved >= activity.capacity:
            raise CapacityExceeded()

        decision = policy.decide(
            RegistrationContext(
                activity=activity,
                student=student,
                approved_count=approved,
                now=now,
            )
        )

        registration = Registration(
            activity_id=activity_id,
            student_id=student_id,
            status=decision.status.value,
            created_at=now,
            updated_at=now,
        )
        self.session.add(registration)
        self.session.commit()

        # 事务提交后再发布事件：通知失败不影响报名结果
        self._publish(decision.event_type, registration, activity.title)
        return registration

    def cancel(self, registration_id: int, student_id: str) -> Registration:
        now = self._now()
        registration = self._require(registration_id)
        if registration.student_id != student_id:
            raise NotOwner()
        activity = self.activities.get(registration.activity_id)
        if activity.start_at <= now:
            raise ActivityStarted()
        if registration.status_value not in (
            RegistrationStatus.PENDING,
            RegistrationStatus.APPROVED,
        ):
            raise InvalidStatusTransition("只有待审核或已通过的报名可以取消")

        registration.status = RegistrationStatus.CANCELLED.value
        registration.updated_at = now
        self.session.commit()
        self._publish(EVENT_CANCELLED, registration, activity.title)
        return registration

    def approve(self, registration_id: int) -> Registration:
        """批准待审核报名：此时才占用名额，必须再次检查容量。"""
        now = self._now()
        registration = self._require(registration_id)
        if registration.status_value is not RegistrationStatus.PENDING:
            raise InvalidStatusTransition("只有待审核的报名可以批准")
        activity = self.activities.get(registration.activity_id)
        approved = self.approved_count(activity.activity_id)
        if approved >= activity.capacity:
            raise CapacityExceeded("名额已满，无法批准该报名")

        registration.status = RegistrationStatus.APPROVED.value
        registration.updated_at = now
        self.session.commit()
        self._publish(EVENT_APPROVED, registration, activity.title)
        return registration

    def reject(self, registration_id: int) -> Registration:
        now = self._now()
        registration = self._require(registration_id)
        if registration.status_value is not RegistrationStatus.PENDING:
            raise InvalidStatusTransition("只有待审核的报名可以拒绝")
        activity = self.activities.get(registration.activity_id)
        registration.status = RegistrationStatus.REJECTED.value
        registration.updated_at = now
        self.session.commit()
        self._publish(EVENT_REJECTED, registration, activity.title)
        return registration

    # ------------------------------------------------------------------ 内部
    def _require(self, registration_id: int) -> Registration:
        registration = self.registrations.get(registration_id)
        if registration is None:
            raise RegistrationNotFound()
        return registration

    def _publish(self, event_name: str, registration: Registration, title: str) -> None:
        self.bus.publish(
            RegistrationEvent(
                name=event_name,
                registration_id=registration.registration_id,
                activity_id=registration.activity_id,
                student_id=registration.student_id,
                status=registration.status_value,
                activity_title=title,
            )
        )
