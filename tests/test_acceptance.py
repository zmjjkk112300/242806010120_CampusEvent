"""实验二初始版本验收测试：C1—C10 各一条，外加 8 条边界/异常用例。

运行：pytest -v
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app import create_app, extensions
from app.constants import (
    ALL_EVENTS,
    EVENT_APPROVED,
    PolicyType,
    RegistrationStatus,
)
from app.errors import (
    ActivityStarted,
    CapacityExceeded,
    DuplicateRegistration,
    HasRegistrations,
    InvalidStatusTransition,
    NotOwner,
    UnknownPolicy,
    ValidationError,
)
from app.events import DomainEventBus, RegistrationEvent
from app.models import Activity, Message, Registration
from app.notifications import InAppNotificationObserver
from app.repositories import ActivityRepository
from app.services import RegistrationService


# ------------------------------------------------------------------ 工具函数
def message_texts(student_id: str) -> list[str]:
    session = extensions.session()
    session.expire_all()
    rows = session.scalars(select(Message).where(Message.student_id == student_id)).all()
    return [row.content for row in rows]


def status_of(service, activity_id: int, student_id: str) -> str:
    registration = service.registrations.latest_of(activity_id, student_id)
    return registration.status if registration else ""


# ================================================================== C1—C10
def test_c1_admin_creates_direct_activity_with_capacity_two(make_activity, db):
    """C1 管理员创建直接报名活动，容量 2。"""
    activity = make_activity(title="程序设计竞赛校内选拔", capacity=2, policy_type=PolicyType.DIRECT)
    assert activity.activity_id > 0
    assert activity.capacity == 2
    assert activity.policy_type == PolicyType.DIRECT.value
    assert db.scalars(select(Activity).where(Activity.title == "程序设计竞赛校内选拔")).first() is not None


def test_c2_direct_registration_approves_and_notifies(make_activity, service):
    """C2 学生 A 报名直接报名活动：直接变为已通过并通知。"""
    activity = make_activity(capacity=2, policy_type=PolicyType.DIRECT)
    registration = service.register(activity.activity_id, "S001")

    assert registration.status == RegistrationStatus.APPROVED.value
    texts = message_texts("S001")
    assert len(texts) == 1
    assert "已通过" in texts[0]
    assert activity.title in texts[0]


def test_c3_duplicate_registration_is_rejected(make_activity, service):
    """C3 同一学生再次提交相同活动报名：拒绝重复有效报名。"""
    activity = make_activity(capacity=5, policy_type=PolicyType.DIRECT)
    service.register(activity.activity_id, "S001")

    with pytest.raises(DuplicateRegistration):
        service.register(activity.activity_id, "S001")

    assert len(service.registrations.list_of_student("S001")) == 1


def test_c4_capacity_limit_blocks_third_student(make_activity, service):
    """C4 名额已满后第三名学生报名失败。"""
    activity = make_activity(capacity=2, policy_type=PolicyType.DIRECT)
    service.register(activity.activity_id, "S001")
    service.register(activity.activity_id, "S002")

    with pytest.raises(CapacityExceeded):
        service.register(activity.activity_id, "S003")

    stats = service.stats(activity.activity_id)
    assert stats["approved"] == 2
    assert stats["remaining"] == 0
    assert service.registrations.list_of_student("S003") == []


def test_c5_approval_activity_creates_pending_registration(make_activity, service):
    """C5 审核型活动：学生申请后状态为待审核。"""
    activity = make_activity(capacity=10, policy_type=PolicyType.APPROVAL)
    registration = service.register(activity.activity_id, "S001")

    assert registration.status == RegistrationStatus.PENDING.value
    texts = message_texts("S001")
    assert "等待管理员审核" in texts[0]
    stats = service.stats(activity.activity_id)
    assert stats["pending"] == 1
    assert stats["approved"] == 0  # 待审核不占名额


def test_c6_admin_approves_pending_registration(make_activity, service):
    """C6 管理员批准待审核报名：变为已通过且生成通知。"""
    activity = make_activity(capacity=10, policy_type=PolicyType.APPROVAL)
    registration = service.register(activity.activity_id, "S001")

    approved = service.approve(registration.registration_id)

    assert approved.status == RegistrationStatus.APPROVED.value
    texts = message_texts("S001")
    assert any("已通过" in text for text in texts)
    assert service.stats(activity.activity_id)["approved"] == 1


def test_c7_admin_rejects_pending_registration(make_activity, service):
    """C7 管理员拒绝另一条待审核报名：变为已拒绝且生成通知。"""
    activity = make_activity(capacity=10, policy_type=PolicyType.APPROVAL)
    first = service.register(activity.activity_id, "S001")
    second = service.register(activity.activity_id, "S002")

    service.approve(first.registration_id)
    rejected = service.reject(second.registration_id)

    assert rejected.status == RegistrationStatus.REJECTED.value
    assert any("未通过审核" in text for text in message_texts("S002"))
    assert service.stats(activity.activity_id)["pending"] == 0


def test_c8_approval_fails_when_capacity_is_full(make_activity, service):
    """C8 批准时容量已满：批准失败，不超出人数上限。"""
    activity = make_activity(capacity=1, policy_type=PolicyType.APPROVAL)
    first = service.register(activity.activity_id, "S001")
    second = service.register(activity.activity_id, "S002")

    service.approve(first.registration_id)
    with pytest.raises(CapacityExceeded):
        service.approve(second.registration_id)

    assert second.status == RegistrationStatus.PENDING.value
    assert service.stats(activity.activity_id)["approved"] == 1


def test_c9_cancel_updates_status_and_stats(make_activity, service):
    """C9 学生取消待审核或已通过报名：状态已取消，统计同步变化。"""
    direct = make_activity(title="直接报名活动", capacity=5, policy_type=PolicyType.DIRECT)
    approved_reg = service.register(direct.activity_id, "S001")
    service.cancel(approved_reg.registration_id, "S001")

    assert approved_reg.status == RegistrationStatus.CANCELLED.value
    assert service.stats(direct.activity_id)["approved"] == 0
    assert service.stats(direct.activity_id)["remaining"] == 5

    review = make_activity(title="审核活动", capacity=5, policy_type=PolicyType.APPROVAL)
    pending_reg = service.register(review.activity_id, "S002")
    service.cancel(pending_reg.registration_id, "S002")

    assert pending_reg.status == RegistrationStatus.CANCELLED.value
    assert service.stats(review.activity_id)["pending"] == 0


# ================================================================== 扩展边界
def test_c10_data_survives_restart(tmp_path):
    """C10 重新启动服务后活动、报名、通知数据仍一致。"""
    database_uri = f"sqlite:///{tmp_path / 'persist.db'}"
    config = {
        "TESTING": True,
        "DATABASE_URI": database_uri,
        "SECRET_KEY": "test-secret",
        "SEED_DEMO": False,
    }

    app1 = create_app(config)
    with app1.app_context():
        from app.models import Student

        session = extensions.session()
        session.add(Student(student_id="S001", name="张皓南"))
        activity = Activity(
            title="持久化校验活动",
            category="文体活动",
            location="活动中心",
            capacity=3,
            policy_type=PolicyType.DIRECT.value,
            start_at=datetime.now() + timedelta(days=3),
        )
        session.add(activity)
        session.commit()
        service = RegistrationService(extensions.session(), extensions.event_bus())
        service.register(activity.activity_id, "S001")
        first_registration_id = service.registrations.list_of_student("S001")[0].registration_id

    app2 = create_app(config)
    with app2.app_context():
        session = extensions.session()
        session.expire_all()
        activity_count = len(list(session.scalars(select(Activity))))
        registrations = list(session.scalars(select(Registration)))
        messages = list(session.scalars(select(Message)))

        assert activity_count == 1
        assert len(registrations) == 1
        assert registrations[0].registration_id == first_registration_id
        assert registrations[0].status == RegistrationStatus.APPROVED.value
        assert len(messages) == 1
        assert messages[0].is_read == 0


def test_extra_cancelled_registration_can_apply_again(make_activity, service):
    """已取消记录保留历史，允许再次申请。"""
    activity = make_activity(capacity=5, policy_type=PolicyType.APPROVAL)
    first = service.register(activity.activity_id, "S001")
    service.cancel(first.registration_id, "S001")
    second = service.register(activity.activity_id, "S001")

    assert first.status == RegistrationStatus.CANCELLED.value
    assert second.status == RegistrationStatus.PENDING.value
    assert len(service.registrations.list_of_student("S001")) == 2


def test_extra_registration_blocked_after_activity_started(make_activity, service):
    """活动开始后不允许新增报名。"""
    activity = make_activity(start_in_days=-1)
    with pytest.raises(ActivityStarted):
        service.register(activity.activity_id, "S001")


def test_extra_delete_activity_with_registrations_is_refused(make_activity, service):
    """已有报名的活动拒绝删除，无报名可删除。"""
    activity = make_activity(capacity=5)
    service.register(activity.activity_id, "S001")
    repository = ActivityRepository(extensions.session())

    with pytest.raises(HasRegistrations):
        repository.delete(activity.activity_id)

    empty = make_activity(title="无报名活动", capacity=5)
    repository.delete(empty.activity_id)
    assert extensions.session().get(Activity, empty.activity_id) is None


def test_extra_notification_failure_does_not_rollback_registration(make_activity, app):
    """通知失败只留痕，不影响已提交的报名记录。"""
    activity = make_activity(capacity=5, policy_type=PolicyType.DIRECT)
    bus = DomainEventBus(logger=app.logger)

    def unavailable(event):  # noqa: ARG001
        raise RuntimeError("通知服务暂不可用")

    bus.subscribe_all(unavailable, list(ALL_EVENTS))
    service = RegistrationService(extensions.session(), bus)
    registration = service.register(activity.activity_id, "S001")

    assert registration.status == RegistrationStatus.APPROVED.value
    assert len(bus.failures) == 1
    assert extensions.session().get(Registration, registration.registration_id) is not None


def test_extra_duplicate_event_produces_single_message(make_activity, service, app):
    """同一事件重复投递不产生第二条通知（幂等）。"""
    activity = make_activity(capacity=5, policy_type=PolicyType.DIRECT)
    registration = service.register(activity.activity_id, "S001")
    observer = InAppNotificationObserver(extensions.session_factory, logger=app.logger)
    event = RegistrationEvent(
        name=EVENT_APPROVED,
        registration_id=registration.registration_id,
        activity_id=activity.activity_id,
        student_id="S001",
        status=RegistrationStatus.APPROVED,
        activity_title=activity.title,
    )
    observer.handle(event)  # 重复投递
    assert len(message_texts("S001")) == 1


def test_extra_cannot_cancel_others_registration(make_activity, service):
    """不能取消他人的报名。"""
    activity = make_activity(capacity=5)
    registration = service.register(activity.activity_id, "S001")
    with pytest.raises(NotOwner):
        service.cancel(registration.registration_id, "S002")


def test_extra_unknown_policy_is_rejected(db):
    """未知报名方式快速失败，不产生脏数据。"""
    activity = Activity(
        title="未知策略活动",
        category="其他",
        location="待定",
        capacity=5,
        policy_type="weird",
        start_at=datetime.now() + timedelta(days=2),
    )
    db.add(activity)
    db.commit()
    service = RegistrationService(extensions.session(), extensions.event_bus())
    with pytest.raises(UnknownPolicy):
        service.register(activity.activity_id, "S001")


def test_extra_unknown_student_is_rejected(make_activity, service):
    """不存在的学生账号不能报名。"""
    activity = make_activity(capacity=5)
    with pytest.raises(ValidationError):
        service.register(activity.activity_id, "S999")
    assert service.registrations.list_of_student("S999") == []


def test_extra_reject_requires_pending_status(make_activity, service):
    """只有待审核的报名可以被拒绝。"""
    activity = make_activity(capacity=5, policy_type=PolicyType.DIRECT)
    registration = service.register(activity.activity_id, "S001")
    with pytest.raises(InvalidStatusTransition):
        service.reject(registration.registration_id)
    assert registration.status == RegistrationStatus.APPROVED.value


# ================================================================== 页面流程
def test_web_student_can_login_and_register(client, make_activity):
    """页面流程：学生登录 → 报名 → 我的报名可见。"""
    activity = make_activity(title="页面报名活动", capacity=2)
    client.post("/login/student", data={"student_id": "S001"})
    response = client.post(f"/activities/{activity.activity_id}/register", follow_redirects=True)
    assert response.status_code == 200
    assert "报名成功" in response.get_data(as_text=True)

    my_page = client.get("/my/registrations")
    assert "已通过" in my_page.get_data(as_text=True)


def test_web_admin_approves_from_review_page(client, make_activity, service):
    """页面流程：管理员登录 → 审核页面批准。"""
    activity = make_activity(title="页面审核活动", capacity=5, policy_type=PolicyType.APPROVAL)
    registration = service.register(activity.activity_id, "S002")

    client.post("/login/admin", data={"password": "admin123"})
    response = client.post(
        f"/admin/registrations/{registration.registration_id}/approve", follow_redirects=True
    )
    assert "已批准该报名" in response.get_data(as_text=True)
    assert registration.status == RegistrationStatus.APPROVED.value


def test_web_activity_form_rejects_empty_title(client, db):
    """页面流程：活动名称为空时不创建数据。"""
    client.post("/login/admin", data={"password": "admin123"})
    before = len(list(db.scalars(select(Activity))))
    response = client.post(
        "/admin/activities/new",
        data={"title": " ", "capacity": "5", "start_at": "2026-12-01T10:00", "policy_type": "direct"},
        follow_redirects=True,
    )
    assert "活动名称不能为空" in response.get_data(as_text=True)
    assert len(list(db.scalars(select(Activity)))) == before


def test_web_unauthenticated_register_redirects_to_login(client, make_activity):
    """未登录报名被拦截到登录页。"""
    activity = make_activity(capacity=5)
    response = client.post(f"/activities/{activity.activity_id}/register")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
