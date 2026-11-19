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
            return

        now = datetime.now()
        students = [
            Student(student_id="S001", name="张皓南"),
            Student(student_id="S002", name="李思远"),
            Student(student_id="S003", name="王雨桐"),
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
