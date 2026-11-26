"""应用工厂：装配依赖、注册蓝图、初始化演示数据。"""

import os

from flask import Flask

from .constants import APP_VERSION
from . import extensions
from .routes import admin_bp, student_bp
from .seed import seed_demo_data
from .services import RegistrationService


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    instance_path = app.instance_path
    os.makedirs(instance_path, exist_ok=True)
    database_uri = os.environ.get(
        "CAMPUS_EVENT_DB", "sqlite:///" + os.path.join(instance_path, "campus_event.db")
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CAMPUS_EVENT_SECRET", "campus-event-dev-key"),
        DATABASE_URI=database_uri,
        ADMIN_USER=os.environ.get("CAMPUS_EVENT_ADMIN", "admin"),
        ADMIN_PASSWORD=os.environ.get("CAMPUS_EVENT_ADMIN_PASSWORD", "admin123"),
        SEED_DEMO=os.environ.get("CAMPUS_EVENT_SEED", "1") == "1",
        EMAIL_FAIL_TIMES=int(os.environ.get("CAMPUS_EVENT_EMAIL_FAIL_TIMES", "0")),
    )
    if config:
        app.config.update(config)

    extensions.init_engine(app.config["DATABASE_URI"])
    extensions.create_all()
    migrations = extensions.ensure_schema()
    if migrations:
        app.logger.info("v2 结构迁移已执行：%s", "，".join(migrations))
    extensions.init_event_bus(
        logger=app.logger,
        email_fail_times=app.config["EMAIL_FAIL_TIMES"],
    )

    @app.context_processor
    def inject_globals():
        return {
            "app_version": APP_VERSION,
            "policy_labels": {
                "direct": "直接报名",
                "approval": "管理员审核",
                "grade_direct": "年级限定直接报名",
            },
        }

    @app.teardown_appcontext
    def shutdown_session(exception=None):  # noqa: ARG001
        extensions.remove_session()

    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    if app.config.get("SEED_DEMO"):
        seed_demo_data(app)

    return app


def make_service() -> RegistrationService:
    """按请求装配业务服务：仓储 + 策略注册表 + 事件总线。"""
    return RegistrationService(extensions.session(), extensions.event_bus())
