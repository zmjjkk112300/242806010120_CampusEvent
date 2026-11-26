"""生成 v2 变更版 UML（类图 / 时序图）源文件：在 v1 基础上增补年级限定与邮件通知结构。"""
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs" / "uml"

# ---------------------------------------------------------------- 类图
src = (DOCS / "class-diagram.puml").read_text(encoding="utf-8")

src = src.replace("@startuml CampusEventClassDiagram", "@startuml CampusEventClassDiagramV2")

src = src.replace(
    "    +reject()\n  }",
    "    +reject()\n    +emails()\n  }",
)

src = src.replace(
    """  class PolicyRegistry {
    -policies: dict
    +register(policy)
    +get(policy_type): RegistrationPolicy
  }""",
    """  class PolicyRegistry {
    -policies: dict
    +register(policy)
    +get(policy_type): RegistrationPolicy
  }
  class GradeLimitedDirectPolicy {
    policy_type = grade_direct
    occupies_capacity_on_submit = true
    -inner: DirectRegistrationPolicy
    -rule: GradeRangeRule
    +decide(context): RegistrationDecision
  }
  interface RegistrationRule {
    +check(context)
  }
  class GradeRangeRule {
    +check(context)
  }
  class CompositePolicy <<v2 组合>> {
    -rules: list
    -inner: RegistrationPolicy
    +decide(context): RegistrationDecision
  }""",
)

src = src.replace(
    """  class InAppNotificationObserver <<observer>> {
    -session_factory
    +handle(event)
    +build_content(event): str
  }""",
    """  class InAppNotificationObserver <<observer>> {
    -session_factory
    +handle(event)
    +build_content(event): str
  }
  class EmailNotificationObserver <<observer v2>> {
    -session_factory
    -sender: EmailSender
    +handle(event)
    +default_recipient(event): str
  }
  class EmailSender <<interface v2>> {
    +send(recipient, subject, body)
  }
  class MockEmailSender <<v2 模拟实现>> {
    -fail_times: int
    -sent: list
    +send(recipient, subject, body)
  }""",
)

src = src.replace(
    """    capacity: int
    policy_type: PolicyType
  }""",
    """    capacity: int
    policy_type: PolicyType
    min_grade: int
    max_grade: int
  }""",
)

src = src.replace(
    """  class Student {
    student_id: str
    name: str
  }""",
    """  class Student {
    student_id: str
    name: str
    grade: int
    email: str
  }""",
)

src = src.replace(
    """    event_key: str
    is_read: int
  }
}""",
    """    event_key: str
    is_read: int
  }
  class EmailRecord <<v2>> {
    email_id: int
    student_id: str
    activity_id: int
    recipient: str
    subject: str
    body: str
    status: str
    error: str
    event_key: str
    created_at: datetime
  }
}""",
)

src = src.replace(
    """RegistrationPolicy <|-- ApprovalRegistrationPolicy""",
    """RegistrationPolicy <|-- ApprovalRegistrationPolicy
RegistrationPolicy <|-- GradeLimitedDirectPolicy
RegistrationPolicy <|-- CompositePolicy""",
)

src = src.replace(
    """InAppNotificationObserver ..> Message : 写入""",
    """InAppNotificationObserver ..> Message : 写入
DomainEventBus --> EmailNotificationObserver : 通知（并列观察者）
EmailNotificationObserver --> EmailSender : 委托发送
EmailSender <|.. MockEmailSender
EmailNotificationObserver ..> EmailRecord : 写入
GradeLimitedDirectPolicy --> GradeRangeRule : 组合规则
GradeLimitedDirectPolicy --> DirectRegistrationPolicy : 复用内层策略
GradeRangeRule ..> GradeNotAllowed : 越界抛出""",
)

src = src.replace(
    """Message "0..*" --> "1" Student : 送达""",
    """Message "0..*" --> "1" Student : 送达
EmailRecord "0..*" --> "1" Student : 收件""",
)

src = src.replace(
    """  名额不超限（批准时复查）
end note""",
"""  名额不超限（批准时复查）
  —— v2 未改动本类，年级规则作为策略内规则链接入
end note""",
)

(DOCS / "class-diagram-v2.puml").write_text(src, encoding="utf-8")

# ---------------------------------------------------------------- 时序图
(DOCS / "sequence-register-v2.puml").write_text(
    """@startuml SequenceRegisterV2
skinparam dpi 150
skinparam shadowing false
skinparam sequenceMessageAlign center

actor 学生
participant "StudentRoutes" as R
participant "RegistrationService" as S
participant "PolicyRegistry" as P
participant "GradeLimitedDirectPolicy" as G
participant "GradeRangeRule" as K
participant "DomainEventBus" as B
participant "InAppNotificationObserver" as N1
participant "EmailNotificationObserver" as N2
database "SQLite" as DB

学生 -> R : POST /activities/{id}/register
R -> S : register(activity_id, student_id)
S -> DB : 公共不变量：活动未开始 / 无重复有效报名 / 名额
S -> P : get(activity.policy_type)
P --> S : GradeLimitedDirectPolicy
S -> G : decide(context)
G -> K : check(context)  # 年级 ∈ [min_grade, max_grade]
alt 年级越界
  K --> G : raise GradeNotAllowed("仅面向大二—大三…")
  G --> S : 异常冒泡（未落库）
  S --> R : DomainError
  R --> 学生 : flash「不符合报名条件：…」，不生成报名
else 年级符合
  G --> S : RegistrationDecision(APPROVED)
  S -> DB : 写入 Registration（占用名额）
  S -> B : publish(EVENT_APPROVED)
  par 站内通知
    B -> N1 : handle(event)
    N1 -> DB : 幂等写入 Message
  and 邮件通知
    B -> N2 : handle(event)
    N2 -> DB : EmailRecord 查重（recipient+event_key）
    N2 -> N2 : MockEmailSender.send()
    alt 发送失败
      N2 -> DB : EmailRecord(status=发送失败, error)
      N2 --> B : raise（总线记录 failure，报名不回滚）
    end
  end
  S --> R : registration
  R --> 学生 : flash「报名成功」
end
@enduml
""",
    encoding="utf-8",
)

print("written", (DOCS / "class-diagram-v2.puml").name, (DOCS / "sequence-register-v2.puml").name)
