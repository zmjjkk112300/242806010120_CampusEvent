"""演示数据初始化：3 名学生、1 个管理员账号、4 个活动。"""

from datetime import datetime, timedelta

from sqlalchemy import select

from .constants import PolicyType, RegistrationStatus
from .models import Activity, Message, Registration, Student


def seed_demo_data(app) -> None:
    from . import extensions

    session = extensions.session()
    try:
        if session.scalar(select(Student).limit(1)) is not None:
            # 已有数据（v1 升级而来）：只补齐 v2 新增的演示要素，不覆盖既有数据
            ensure_change_demo(session)
            return

        now = datetime.now()
        students = [
            Student(student_id="S001", name="张皓南", grade=3, email="s001@campus.example.edu"),
            Student(student_id="S002", name="李思远", grade=2, email="s002@campus.example.edu"),
            Student(student_id="S003", name="王雨桐", grade=1, email="s003@campus.example.edu"),
        ]
        session.add_all(students)

        activities = [
            Activity(
                title="程序设计竞赛校内选拔",
                category="学术竞赛",
                start_at=now + timedelta(days=5, hours=9),
                location="湘湖校区图书馆报告厅",
                capacity=2,
                policy_type=PolicyType.DIRECT.value,
            ),
            Activity(
                title="陶艺创作工作坊",
                category="文体活动",
                start_at=now + timedelta(days=8, hours=14),
                location="陶瓷艺术中心 302",
                capacity=15,
                policy_type=PolicyType.APPROVAL.value,
            ),
            Activity(
                title="劳动教育实践中心志愿者招募",
                category="志愿服务",
                start_at=now + timedelta(days=12, hours=10),
                location="学生活动中心一层",
                capacity=20,
                policy_type=PolicyType.APPROVAL.value,
            ),
            Activity(
                title="软件工程课程设计分享会",
                category="学术讲座",
                start_at=now + timedelta(days=2, hours=19),
                location="教学楼 A305",
                capacity=50,
                policy_type=PolicyType.DIRECT.value,
            ),
            # v2 / CR-01：仅大二、大三可报名的年级限定活动
            Activity(
                title="学科竞赛集训营（大二大三专属）",
                category="学术竞赛",
                start_at=now + timedelta(days=6, hours=9),
                location="湘湖校区实训楼 B201",
                capacity=10,
                policy_type=PolicyType.GRADE_DIRECT.value,
                min_grade=2,
                max_grade=3,
            ),
        ]
        session.add_all(activities)
        session.flush()

        # 直接报名活动预置一条已通过记录，便于演示名额占用的边界
        session.add(
            Registration(
                activity_id=activities[0].activity_id,
                student_id="S002",
                status=RegistrationStatus.APPROVED.value,
            )
        )
        # 审核型活动预置一条待审核记录
        session.add(
            Registration(
                activity_id=activities[1].activity_id,
                student_id="S003",
                status=RegistrationStatus.PENDING.value,
            )
        )
        session.add(
            Message(
                student_id="S002",
                activity_id=activities[0].activity_id,
                content="你报名的活动《程序设计竞赛校内选拔》已通过。",
                event_key="demo:approved:1",
            )
        )
        session.commit()
    finally:
        extensions.remove_session()


def ensure_change_demo(session) -> None:
    """v2 幂等补齐：老库缺少年级限定演示活动时补一条，便于直接演示 CR-01。

    * 只在不存在 ``grade_direct`` 活动时插入，重复启动不会产生重复数据；
    * 学生的年级/邮箱由 ``extensions.ensure_schema()`` 负责回填，这里不重复处理。
    """
    exists = session.scalar(
        select(Activity).where(Activity.policy_type == PolicyType.GRADE_DIRECT.value).limit(1)
    )
    if exists is not None:
        return
    session.add(
        Activity(
            title="学科竞赛集训营（大二大三专属）",
            category="学术竞赛",
            start_at=datetime.now() + timedelta(days=6, hours=9),
            location="湘湖校区实训楼 B201",
            capacity=10,
            policy_type=PolicyType.GRADE_DIRECT.value,
            min_grade=2,
            max_grade=3,
        )
    )
    session.commit()
    print("已为既有数据库补齐 v2 演示活动：学科竞赛集训营（大二大三专属）")
