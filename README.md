# CampusEvent · 校园活动报名与管理系统（实验二 · change-v2）

软件工程课程实践 实验二：基于设计模式的校园活动报名与管理系统。
本仓库现在是 **change-v2**：在初始验收版本 `baseline-v1` 的基础上完成 CR-01（年级限定报名）与 CR-02（邮件通知）。

- 姓名：张皓南　学号：242806010120　班级：计算机科学与技术 2024 级
- 技术栈：Python 3.11+ / Flask 3.1 / SQLAlchemy 2.x / SQLite / pytest
- 代码仓库：<https://github.com/zmjjkk112300/242806010120_CampusEvent>
- 在线访问：<http://47.106.160.76:8000>（正式部署地址，systemd 托管、开机自启）
- 版本标识：页脚显示 `change-v2`；`git tag` 可对照 `baseline-v1` 与 `change-v2`

## 一、快速开始（本地）

```bash
# 1. 进入项目目录
cd CampusEvent_242806010120

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# 3. 启动（首次启动自动建表、补齐 v2 新增列并写入演示数据）
python run.py
```

浏览器打开 http://127.0.0.1:5000

## 二、演示账号

| 角色 | 账号 | 密码 | 说明 |
|---|---|---|---|
| 学生 | `S001` 张皓南（大三）、`S002` 李思远（大二）、`S003` 王雨桐（大一） | 无需密码 | 登录页可直接选择 |
| 管理员 | `admin` | `admin123` | 可创建/编辑/删除活动、审核报名、查看邮件记录 |

演示数据包含 5 个活动：直接报名 2 个（容量 2 与 50）、审核型 2 个（容量 15 与 20）、
年级限定 1 个（「学科竞赛集训营（大二大三专属）」，容量 10，限 2—3 年级），
并预置一条已通过报名与一条待审核报名，便于直接演示名额、审核与年级拒绝流程。

## 三、v2 变更内容

| 变更单 | 能力 | 关键设计 |
|---|---|---|
| CR-01 | 年级限定直接报名 | 新增 `PolicyType.grade_direct`；策略内组合 `GradeRangeRule`，`RegistrationService` 零改动 |
| CR-02 | 报名结果邮件通知 | `MockEmailSender` + `EmailNotificationObserver` 与站内观察者并列订阅；失败只留痕不回滚 |

- 年级比对取 `Activity.min_grade / max_grade` 闭区间，NULL 表示不限；越界抛 `GradeNotAllowed`，提示含允许区间与当前年级。
- 邮件只订阅“通过 / 拒绝”两类事件，记录收件人、主题、内容、状态、时间与失败原因，`(recipient, event_key)` 唯一约束保证同一事件只发一次。
- 管理员端新增「邮件记录」页（`/admin/emails`），可直接看到发送成功/失败明细。
- 影响分析、设计理由与回归证据见 `docs/09`、`docs/10`、`docs/11`；交付与回滚见 `docs/12`；类图与时序图见 `docs/uml/*-v2.*`。

## 四、自动化测试

```bash
pytest -q
```

- **36 条用例全部通过**：原有 23 条（C1—C10 + 13 条边界/页面流程）+ v2 新增 13 条（CR1-01—05、年级拒绝页面、CR2-01—05、结构迁移）。
- 每个用例使用独立临时 SQLite 文件，互不影响，可重复运行。
- 只跑变更用例：`pytest tests/test_change_v2.py -v`。

## 五、云服务器部署

```bash
# 服务器上（Linux）一键部署：建 venv、装依赖、跑测试、后台启动 gunicorn
bash deploy/deploy.sh 8000
```

部署记录见 `deploy/DEPLOY.md`，要点如下。

- 已部署主机：阿里云轻量应用服务器（Ubuntu 24.04，公网 IP `47.106.160.76`），代码位于
  `/opt/campus-event`；`gunicorn -w 2 -b 0.0.0.0:8000 run:app` 由 systemd 单元
  `campus-event.service` 托管并设置开机自启，服务器上 `pytest` 36 passed。
- 公网访问：<http://47.106.160.76:8000>，已从外部网络实测返回 HTTP 200，浏览器可直接打开。
- 旧库升级：应用启动时 `ensure_schema()` 自动补 `students.grade/email`、`activities.min_grade/max_grade`，无需删库重建。

## 六、配置项（环境变量）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `CAMPUS_EVENT_DB` | `instance/campus_event.db` | SQLite 连接串 |
| `CAMPUS_EVENT_SECRET` | 开发默认值 | Flask 会话密钥，部署须替换 |
| `CAMPUS_EVENT_ADMIN_PASSWORD` | `admin123` | 管理员演示密码 |
| `CAMPUS_EVENT_SEED` | `1` | 首次启动是否写入演示数据 |
| `CAMPUS_EVENT_EMAIL_FAIL_TIMES` | `0` | 模拟邮件前 N 次强制失败（演示/测试故障路径） |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | `python run.py` 的监听地址 |

## 七、目录结构

```
CampusEvent_242806010120/
├── app/
│   ├── __init__.py          # 应用工厂：装配引擎、迁移、事件总线、蓝图
│   ├── constants.py         # 状态、报名方式、事件名、邮件状态、版本
│   ├── models.py            # Student / Activity / Registration / Message / EmailRecord
│   ├── repositories.py      # 五类仓储，隔离 SQL
│   ├── services.py          # RegistrationService：唯一的状态流转入口（v2 零改动）
│   ├── policies.py          # 策略模式 + 规则链：direct / approval / grade_direct
│   ├── events.py            # 领域事件 + 同步事件总线
│   ├── notifications.py     # 站内通知观察者 + 邮件通知观察者
│   ├── mailer.py            # EmailSender 端口 + MockEmailSender 模拟实现
│   ├── errors.py            # 业务异常
│   ├── routes.py            # 学生端 / 管理端蓝图（含邮件记录页）
│   ├── seed.py              # 演示数据（含年级与邮箱）
│   ├── templates/           # 11 个 Jinja2 页面
│   └── static/style.css
├── tests/                   # pytest 用例（36 条）
├── docs/                    # 需求、用例、类图、时序图、设计决策、测试记录、变更文档
├── AI_DEV_LOG.md            # AI 协作过程记录
└── run.py                   # 启动入口
```

## 八、已知限制（如实说明）

1. 登录为固定演示账号，无注册、无密码体系，不做细粒度权限（课程要求范围内）。
2. 邮件为模拟发送，不外发真实邮件；替换 `EmailSender` 实现即可接入 SMTP，观察者与表结构无需改动。
3. 邮件发送同步阻塞且不自动重试，失败只留记录；重复投递靠 `event_key` 幂等。
4. 年级限定仅支持连续区间，不支持离散年级组合。
5. 活动删除采用“有报名则拒绝删除”，未做软删除。
6. 单进程 SQLite，未做并发压测；生产多实例需换 MySQL 并引入任务队列。
