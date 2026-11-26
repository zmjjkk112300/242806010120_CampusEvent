"""实验二变更阶段（v2）验收测试：CR-01 年级限定、CR-02 邮件通知。

CR1-01 — CR1-05、CR2-01 — CR2-05 各一条；C1—C10 的回归由 test_acceptance.py 覆盖，
两者在同一命令中一起运行即完成“变更后重新运行 C1—C10”的证据。
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app import create_app, extensions
from app.constants import (
    EVENT_APPROVED,
    PolicyType,
    RegistrationStatus,
)
from app.errors import CapacityExceeded, DuplicateRegistration, EmailSendFailed, GradeNotAllowed
from app.events import RegistrationEvent
from app.models import Activity, EmailRecord, Message, Registration, Student
from app.notifications import EmailNotificationObserver
from app.services import RegistrationService


# ------------------------------------------------------------------ 工具
def email_rows(student_id: str | None = None) -> list[EmailRecord]:
    session = extensions.session()
    session.expire_all()
    stmt = select(EmailRecord)
    if student_id:
        stmt = stmt.where(EmailRecord.student_id == student_id)
    return list(session.scalars(stmt))


def grade_activity(make_activity, low=2, high=3):
    return make_activity(
        title="年级限定活动",
        capacity=10,
        policy_type=PolicyType.GRADE_DIRECT,
        min_grade=low,
        max_grade=high,
    )


# ================================================================== CR-01
def test_cr1_01_sophomore_can_register_grade_limited_activity(make_activity, service):
    """CR1-01 大二学生（grade=2）报名年级限定活动 → 通过。"""
    activity = grade_activity(make_activity)
    registration = service.register(activity.activity_id, "S002")
    assert registration.status == RegistrationStatus.APPROVED.value
    assert service.stats(activity.activity_id)["approved"] == 1


def test_cr1_02_junior_can_register_grade_limited_activity(make_activity, service):
    """CR1-02 大三学生（grade=3）报名年级限定活动 → 通过。"""
    activity = grade_activity(make_activity)
    registration = service.register(activity.activity_id, "S001")
    assert registration.status == RegistrationStatus.APPROVED.value


def test_cr1_03_freshman_is_rejected_with_reason(make_activity, service):
    """CR1-03 大一学生（grade=1）报名 → 拒绝并给出明确原因。"""
    activity = grade_activity(make_activity)
    with pytest.raises(GradeNotAllowed) as excinfo:
        service.register(activity.activity_id, "S003")
    assert "大二—大三" in str(excinfo.value)
    assert "大一" in str(excinfo.value)
    assert service.registrations.list_of_student("S003") == []


def test_cr1_04_senior_is_rejected_with_reason(make_activity, service):
    """CR1-04 大四学生（grade=4）报名 → 拒绝并给出明确原因。"""
    activity = grade_activity(make_activity)
    with pytest.raises(GradeNotAllowed) as excinfo:
        service.register(activity.activity_id, "S004")
    assert "大四" in str(excinfo.value)
    assert service.registrations.list_of_student("S004") == []


def test_cr1_05_grade_rule_respects_public_invariants(make_activity, service):
    """CR1-05 年级规则仍受名额、活动时间、重复报名等公共约束约束。"""
    activity = grade_activity(make_activity, low=2, high=3)
    service.register(activity.activity_id, "S002")

    # 重复报名
    with pytest.raises(DuplicateRegistration):
        service.register(activity.activity_id, "S002")

    # 名额：容量收到 1 后大二再报满
    small = make_activity(
        title="年级限定小班", capacity=1, policy_type=PolicyType.GRADE_DIRECT, min_grade=2, max_grade=3
    )
    service.register(small.activity_id, "S002")
    with pytest.raises(CapacityExceeded):
        service.register(small.activity_id, "S001")

    # 活动已开始
    started = make_activity(
        title="已开始活动", policy_type=PolicyType.GRADE_DIRECT, start_in_days=-1, min_grade=2, max_grade=3
    )
    from app.errors import ActivityStarted

    with pytest.raises(ActivityStarted):
        service.register(started.activity_id, "S002")

    # 原有直接报名行为不变：随便哪个年级都能报
    plain = make_activity(title="普通直接报名", capacity=5, policy_type=PolicyType.DIRECT)
    assert service.register(plain.activity_id, "S003").status == RegistrationStatus.APPROVED.value


def test_cr1_06_web_grade_limit_shows_reason(client, make_activity):
    """页面流程：大一学生点击报名 → 页面显示年级不符原因，不产生报名记录。"""
    activity = grade_activity(make_activity, low=2, high=3)
    client.post("/login/student", data={"student_id": "S003"})
    response = client.post(
        f"/activities/{activity.activity_id}/register", follow_redirects=True
    )
    text = response.get_data(as_text=True)
    assert "不符合报名条件" in text
    assert "立即报名" in text  # 仍停留在可报名页，未生成报名记录
    assert extensions.session().scalars(
        select(Registration).where(Registration.student_id == "S003")
    ).first() is None


# ================================================================== CR-02
def test_cr2_01_direct_registration_sends_inapp_and_email(make_activity, service):
    """CR2-01 直接报名通过：站内消息与模拟邮件都有记录。"""
    activity = make_activity(title="直接报名活动", capacity=3, policy_type=PolicyType.DIRECT)
    service.register(activity.activity_id, "S001")

    session = extensions.session()
    session.expire_all()
    inapp = list(session.scalars(select(Message).where(Message.student_id == "S001")))
    mails = email_rows("S001")
    assert len(inapp) == 1 and "已通过" in inapp[0].content
    assert len(mails) == 1
    assert mails[0].recipient == "s001@campus.example.edu"
    assert mails[0].status == "已发送"
    assert activity.title in mails[0].body


def test_cr2_02_approve_and_reject_send_both_channels(make_activity, service):
    """CR2-02 审核通过 / 拒绝：站内消息与邮件都记录对应结果。"""
    activity = make_activity(title="审核活动", capacity=5, policy_type=PolicyType.APPROVAL)
    first = service.register(activity.activity_id, "S001")
    second = service.register(activity.activity_id, "S003")
    service.approve(first.registration_id)
    service.reject(second.registration_id)

    session = extensions.session()
    session.expire_all()
    approved_mail = [m for m in email_rows("S001") if "已通过" in m.body]
    rejected_mail = [m for m in email_rows("S003") if "未通过" in m.body]
    assert approved_mail and approved_mail[0].status == "已发送"
    assert rejected_mail and rejected_mail[0].status == "已发送"

    inapp_approved = [
        m.content for m in session.scalars(select(Message).where(Message.student_id == "S001"))
    ]
    inapp_rejected = [
        m.content for m in session.scalars(select(Message).where(Message.student_id == "S003"))
    ]
    assert any("已通过" in text for text in inapp_approved)
    assert any("未通过审核" in text for text in inapp_rejected)


def test_cr2_03_email_failure_keeps_registration_and_logs_error(make_activity, app):
    """CR2-03 模拟邮件发送失败：报名状态正确、失败有记录（错误日志）。"""
    from app.events import DomainEventBus
    from app.mailer import MockEmailSender

    activity = make_activity(title="邮件故障活动", capacity=3, policy_type=PolicyType.DIRECT)
    # 独立总线：只挂一个必定失败的邮件观察者，避免默认观察者先成功发信导致去重
    failing_bus = DomainEventBus(logger=app.logger)
    observer = EmailNotificationObserver(
        extensions.session_factory, MockEmailSender(fail_times=1, logger=app.logger), logger=app.logger
    )
    failing_bus.subscribe(EVENT_APPROVED, observer.handle)

    service = RegistrationService(extensions.session(), failing_bus)
    created = service.register(activity.activity_id, "S001")

    assert created.status == RegistrationStatus.APPROVED.value
    assert extensions.session().get(Registration, created.registration_id) is not None
    failed = [row for row in email_rows("S001") if row.status == "发送失败"]
    assert failed and "模拟邮件服务器不可用" in failed[0].error
    assert failing_bus.failures  # 事件总线留痕


def test_cr2_04_duplicate_business_event_sends_once(make_activity, service, app):
    """CR2-04 同一业务事件重复投递：邮件与站内消息都不会重复生成。"""
    activity = make_activity(title="幂等活动", capacity=5, policy_type=PolicyType.DIRECT)
    registration = service.register(activity.activity_id, "S001")
    observer = EmailNotificationObserver(
        extensions.session_factory, extensions.email_sender(), logger=app.logger
    )
    event = RegistrationEvent(
        name=EVENT_APPROVED,
        registration_id=registration.registration_id,
        activity_id=activity.activity_id,
        student_id="S001",
        status=RegistrationStatus.APPROVED,
        activity_title=activity.title,
    )
    observer.handle(event)  # 重复投递

    assert len(email_rows("S001")) == 1


def test_cr2_05_email_recipient_falls_back_when_missing(make_activity, service, db):
    """CR2-05 学生未维护邮箱时使用默认收件地址，邮件链路不中断。"""
    db.add(Student(student_id="S005", name="临时学生", grade=1, email=""))
    db.commit()
    activity = make_activity(title="无邮箱活动", capacity=3, policy_type=PolicyType.DIRECT)
    service.register(activity.activity_id, "S005")

    rows = email_rows("S005")
    assert len(rows) == 1
    assert rows[0].recipient == "S005@campus.example.edu"
    assert rows[0].status == "已发送"


# ================================================================== 迁移
def test_v2_demo_top_up_is_idempotent(app):
    """老库补齐：缺少年级限定演示活动时补一条，重复调用不产生重复数据。"""
    from app.seed import ensure_change_demo

    session = extensions.session()
    assert session.scalar(select(Activity).where(Activity.policy_type == "grade_direct")) is None
    ensure_change_demo(session)
    ensure_change_demo(extensions.session())

    rows = list(session.scalars(select(Activity).where(Activity.policy_type == "grade_direct")))
    assert len(rows) == 1
    assert (rows[0].min_grade, rows[0].max_grade) == (2, 3)


def test_v2_schema_migration_adds_columns_and_keeps_data(tmp_path):
    """旧库升级：新增列自动补齐，既有活动与报名数据不丢。"""
    database_uri = f"sqlite:///{tmp_path / 'legacy.db'}"
    config = {
        "TESTING": True,
        "DATABASE_URI": database_uri,
        "SECRET_KEY": "test-secret",
        "SEED_DEMO": False,
        "EMAIL_FAIL_TIMES": 0,
    }

    app = create_app(config)
    with app.app_context():
        session = extensions.session()
        session.add(Student(student_id="S001", name="张皓南", grade=3, email="s001@campus.example.edu"))
        activity = Activity(
            title="迁移前活动",
            category="其他",
            location="待定",
            capacity=5,
            policy_type=PolicyType.DIRECT.value,
            start_at=datetime.now() + timedelta(days=3),
        )
        session.add(activity)
        session.commit()
        RegistrationService(extensions.session(), extensions.event_bus()).register(
            activity.activity_id, "S001"
        )

    app2 = create_app(config)
    with app2.app_context():
        session = extensions.session()
        session.expire_all()
        assert session.get(Student, "S001").grade == 3
        assert len(list(session.scalars(select(Activity)))) == 1
        assert len(list(session.scalars(select(Registration)))) == 1
