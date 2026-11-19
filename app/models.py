"""持久化模型（对应附录B.1 领域数据）。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .constants import PolicyType, RegistrationStatus


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)

    registrations: Mapped[list["Registration"]] = relationship(back_populates="student")

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Student {self.student_id} {self.name}>"


class Activity(Base):
    __tablename__ = "activities"

    activity_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_type: Mapped[str] = mapped_column(String(20), nullable=False, default=PolicyType.DIRECT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="activity", cascade="save-update"
    )

    @property
    def policy_label(self) -> str:
        return PolicyType(self.policy_type).label

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Activity {self.activity_id} {self.title}>"


class Registration(Base):
    __tablename__ = "registrations"

    registration_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.activity_id"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default=RegistrationStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    activity: Mapped[Activity] = relationship(back_populates="registrations")
    student: Mapped[Student] = relationship(back_populates="registrations")

    @property
    def status_value(self) -> RegistrationStatus:
        return RegistrationStatus(self.status)

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Registration {self.registration_id} {self.student_id}@{self.activity_id} {self.status}>"


class Message(Base):
    """站内消息。event_key 作为幂等键，保证同一事件只产生一条通知。"""

    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("student_id", "event_key", name="uq_message_event"),)

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False)
    activity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String(255), nullable=False)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    is_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
