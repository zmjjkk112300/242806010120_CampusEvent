# CampusEvent · 校园活动报名与管理系统（实验二）

软件工程课程实践 实验二：基于设计模式的校园活动报名与管理系统。
本仓库为 **baseline-v1（初始验收版本）**，覆盖 P2-F01—P2-F08 全部初始功能。

- 姓名：张皓南　学号：242806010120　班级：计算机科学与技术 2024 级
- 技术栈：Python 3.11+ / Flask 3.1 / SQLAlchemy 2.x / SQLite / pytest
- 代码仓库：<https://github.com/zmjjkk112300/242806010120_CampusEvent>
- 在线访问：<https://8b8efcd3735b1a.app.lhr.life>（演示用公网隧道地址，重连可能变化；正式部署见第四节）

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

# 3. 启动（首次启动自动建表并写入演示数据）
python run.py
```

浏览器打开 http://127.0.0.1:5000

## 二、演示账号

| 角色 | 账号 | 密码 | 说明 |
|---|---|---|---|
| 学生 | `S001` 张皓南、`S002` 李思远、`S003` 王雨桐 | 无需密码 | 登录页可直接选择 |
| 管理员 | `admin` | `admin123` | 可创建/编辑/删除活动、审核报名 |

演示数据包含 4 个活动：直接报名 2 个（容量 2 与 50）、审核型 2 个（容量 15 与 20），
并预置一条已通过报名与一条待审核报名，便于直接演示名额与审核流程。

## 三、自动化测试

```bash
pytest -v
```

- 23 条用例全部通过：C1—C10 初始验收用例各 1 条 + 13 条边界/异常/页面流程用例。
- 每个用例使用独立临时 SQLite 文件，互不影响，可重复运行。

## 四、云服务器部署

```bash
# 服务器上（Linux）一键部署：建 venv、装依赖、跑测试、后台启动 gunicorn
bash deploy/deploy.sh 8000
```

部署记录见 `deploy/DEPLOY.md`，要点如下。

- 已部署主机：课程云主机（Linux，Python 3.12.11），代码位于
  `/home/user/Doubao/chats/38454965453800706/CampusEvent`，
  `gunicorn -w 2 -b 0.0.0.0:8000` 后台运行；本机 `GET /login` 返回 200，服务器上 `pytest` 23 passed。
- 公网访问：该主机安全组/网关未对外放行 8000 端口（实测 80、443、8000、8080 均不可达），
  因此暂无可供外部浏览器打开的公网地址；迁移到具备公网端口的服务器后执行同一脚本并在安全组放行端口即可。
- 生产化：`deploy/campus-event.service` 提供 systemd 托管模板（参考 `deploy/DEPLOY.md`）。

## 五、配置项（环境变量）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `CAMPUS_EVENT_DB` | `instance/campus_event.db` | SQLite 连接串 |
| `CAMPUS_EVENT_SECRET` | 开发默认值 | Flask 会话密钥，部署须替换 |
| `CAMPUS_EVENT_ADMIN_PASSWORD` | `admin123` | 管理员演示密码 |
| `CAMPUS_EVENT_SEED` | `1` | 首次启动是否写入演示数据 |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | `python run.py` 的监听地址 |

## 六、目录结构

```
CampusEvent_242806010120/
├── app/
│   ├── __init__.py          # 应用工厂：装配引擎、事件总线、蓝图
│   ├── constants.py         # 状态、报名方式、事件名枚举
│   ├── models.py            # Student / Activity / Registration / Message
│   ├── repositories.py      # 四类仓储，隔离 SQL
│   ├── services.py          # RegistrationService：唯一的状态流转入口
│   ├── policies.py          # 策略模式：RegistrationPolicy + 两种实现 + 注册表
│   ├── events.py            # 领域事件 + 同步事件总线（观察者载体）
│   ├── notifications.py     # 站内通知观察者（幂等写入）
│   ├── errors.py            # 业务异常
│   ├── routes.py            # 学生端 / 管理端蓝图
│   ├── seed.py              # 演示数据
│   ├── templates/           # 10 个 Jinja2 页面
│   └── static/style.css
├── tests/                   # pytest 用例（23 条）
├── docs/                    # 需求、用例、类图、时序图、设计决策、测试记录
├── AI_DEV_LOG.md            # AI 协作过程记录
└── run.py                   # 启动入口
```

## 七、已知限制（如实说明）

1. 登录为固定演示账号，无注册、无密码体系，不做细粒度权限（课程要求范围内）。
2. 通知仅站内消息，未接邮件/短信；通知写入失败只记录日志，不重试。
3. 活动删除采用“有报名则拒绝删除”，未做软删除。
4. 单进程 SQLite，未做并发压测；生产多实例需换 MySQL 并引入任务队列。
5. 需求变更单（CR）尚未发布，因此本版本不含变更功能，代码也未预留半成品分支。
