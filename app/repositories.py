"""数据访问层：把 SQL 细节从业务服务中隔离，服务只依赖仓储接口语义。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .constants import RegistrationStatus
from .errors import ActivityNotFound, HasRegistrations
from .models import Activity, EmailRecord, Message, Registration, Student


class ActivityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, activity_id: int) -> Activity:
        activity = self.session.get(Activity, activity_id)
        if activity is None:
            raise ActivityNotFound()
        return activity

    def list(self, keyword: str | None = None) -> list[Activity]:
        stmt = select(Activity).order_by(Activity.start_at)
        if keyword:
            stmt = stmt.where(Activity.title.contains(keyword.strip()))
        return list(self.session.scalars(stmt))

    def create(self, **fields) -> Activity:
        activity = Activity(**fields)
        self.session.add(activity)
        self.session.commit()
        return activity

    def update(self, activity_id: int, **fields) -> Activity:
        activity = self.get(activity_id)
        for key, value in fields.items():
            setattr(activity, key, value)
        self.session.commit()
        return activity

    def delete(self, activity_id: int) -> None:
        """已有报名的活动拒绝删除（B.2 规则7 的选择方案）。"""
        activity = self.get(activity_id)
        total = self.session.scalar(
            select(func.count())
            .select_from(Registration)
            .where(Registration.activity_id == activity_id)
        )
        if total:
            raise HasRegistrations()
        self.session.delete(activity)
        self.session.commit()


class RegistrationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, registration_id: int) -> Registration | None:
        return self.session.get(Registration, registration_id)

    def count_by_status(self, activity_id: int, status: RegistrationStatus) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(Registration)
                .where(
                    Registration.activity_id == activity_id,
                    Registration.status == status.value,
                )
            )
            or 0
        )

    def active_of(self, activity_id: int, student_id: str) -> Registration | None:
        stmt = select(Registration).where(
            Registration.activity_id == activity_id,
            Registration.student_id == student_id,
            Registration.status.in_(
                [RegistrationStatus.PENDING.value, RegistrationStatus.APPROVED.value]
            ),
        )
        return self.session.scalars(stmt).first()

    def latest_of(self, activity_id: int, student_id: str) -> Registration | None:
        stmt = (
            select(Registration)
            .where(Registration.activity_id == activity_id, Registration.student_id == student_id)
            .order_by(Registration.registration_id.desc())
        )
        return self.session.scalars(stmt).first()

    def list_of_student(self, student_id: str) -> list[Registration]:
        stmt = (
            select(Registration)
            .where(Registration.student_id == student_id)
            .order_by(Registration.registration_id.desc())
        )
        return list(self.session.scalars(stmt))

    def list_by_status(self, status: RegistrationStatus) -> list[Registration]:
        stmt = (
            select(Registration)
            .where(Registration.status == status.value)
            .order_by(Registration.registration_id)
        )
        return list(self.session.scalars(stmt))

    def add(self, registration: Registration) -> Registration:
        self.session.add(registration)
        self.session.commit()
        return registration

    def save(self, registration: Registration) -> Registration:
        self.session.add(registration)
        self.session.commit()
        return registration


class StudentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, student_id: str) -> Student | None:
        return self.session.get(Student, student_id)

    def list_all(self) -> list[Student]:
        return list(self.session.scalars(select(Student).order_by(Student.student_id)))

    def create(self, student_id: str, name: str) -> Student:
        student = Student(student_id=student_id, name=name)
        self.session.add(student)
        self.session.commit()
        return student


class MessageRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_of_student(self, student_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.student_id == student_id)
            .order_by(Message.message_id.desc())
        )
        return list(self.session.scalars(stmt))

    def unread_count(self, student_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.student_id == student_id, Message.is_read == 0)
            )
            or 0
        )

    def mark_all_read(self, student_id: str) -> None:
        messages = self.list_of_student(student_id)
        for message in messages:
            message.is_read = 1
        self.session.commit()


class EmailRepository:
    """v2 / CR-02：模拟邮件发送记录的只读查询。"""

    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> list[EmailRecord]:
        stmt = select(EmailRecord).order_by(EmailRecord.email_id.desc())
        return list(self.session.scalars(stmt))

    def list_of_student(self, student_id: str) -> list[EmailRecord]:
        stmt = (
            select(EmailRecord)
            .where(EmailRecord.student_id == student_id)
            .order_by(EmailRecord.email_id.desc())
        )
        return list(self.session.scalars(stmt))
