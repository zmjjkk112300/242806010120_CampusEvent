"""pytest 公共夹具：每个测试使用独立 SQLite 文件库，并保持单一应用上下文。"""

from datetime import datetime, timedelta

import pytest

from app import create_app, extensions
from app.constants import PolicyType
from app.models import Activity, Student
from app.services import RegistrationService


@pytest.fixture
def app(tmp_path):
    database_uri = f"sqlite:///{tmp_path / 'test.db'}"
    application = create_app(
        {
            "TESTING": True,
            "DATABASE_URI": database_uri,
            "SECRET_KEY": "test-secret",
            "SEED_DEMO": False,
            "ADMIN_PASSWORD": "admin123",
        }
    )
    context = application.app_context()
    context.push()
    session = extensions.session()
    session.add_all(
        [
            # grade：1 大一、2 大二、3 大三、4 大四
            Student(student_id="S001", name="张皓南", grade=3, email="s001@campus.example.edu"),
            Student(student_id="S002", name="李思远", grade=2, email="s002@campus.example.edu"),
            Student(student_id="S003", name="王雨桐", grade=1, email="s003@campus.example.edu"),
            Student(student_id="S004", name="赵一鸣", grade=4, email="s004@campus.example.edu"),
        ]
    )
    session.commit()
    yield application
    context.pop()


@pytest.fixture
def db(app):
    return extensions.session()


@pytest.fixture
def service(app):
    return RegistrationService(extensions.session(), extensions.event_bus())


@pytest.fixture
def make_activity(app):
    """创建活动的工厂：默认 3 天后开始，容量 2，直接报名。"""

    def _make(
        title="测试活动",
        capacity=2,
        policy_type=PolicyType.DIRECT,
        start_in_days=3,
        category="文体活动",
        location="学生活动中心",
        min_grade=None,
        max_grade=None,
    ):
        activity = Activity(
            title=title,
            category=category,
            location=location,
            capacity=capacity,
            policy_type=PolicyType(policy_type).value,
            start_at=datetime.now() + timedelta(days=start_in_days),
            min_grade=min_grade,
            max_grade=max_grade,
        )
        session = extensions.session()
        session.add(activity)
        session.commit()
        return activity

    return _make


@pytest.fixture
def client(app):
    return app.test_client()
