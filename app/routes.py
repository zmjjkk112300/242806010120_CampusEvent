"""路由层：只做参数解析、权限判断与页面渲染，业务规则全部下沉到服务层。"""

from datetime import datetime
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import extensions
from .constants import PolicyType, RegistrationStatus
from .errors import DomainError, ValidationError
from .policies import default_registry
from .repositories import ActivityRepository, MessageRepository, RegistrationRepository, StudentRepository
from .services import RegistrationService

student_bp = Blueprint("student", __name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------------------------------------------------------------- 公共装配
def service() -> RegistrationService:
    return RegistrationService(extensions.session(), extensions.event_bus())


def student_login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("student_id"):
            flash("请先以学生身份登录", "error")
            return redirect(url_for("student.login"))
        return view(*args, **kwargs)

    return wrapper


def admin_login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash("请先以管理员身份登录", "error")
            return redirect(url_for("student.login"))
        return view(*args, **kwargs)

    return wrapper


def _student_name() -> str:
    return session.get("student_name", "")


# ---------------------------------------------------------------- 登录
@student_bp.get("/login")
def login():
    students = StudentRepository(extensions.session()).list_all()
    return render_template("login.html", students=students)


@student_bp.post("/login/student")
def login_student():
    student_id = request.form.get("student_id", "").strip()
    student = StudentRepository(extensions.session()).get(student_id)
    if student is None:
        flash("学生账号不存在，请使用演示账号", "error")
        return redirect(url_for("student.login"))
    session.clear()
    session["student_id"] = student.student_id
    session["student_name"] = student.name
    flash(f"欢迎你，{student.name}", "success")
    return redirect(url_for("student.activities"))


@student_bp.post("/login/admin")
def login_admin():
    password = request.form.get("password", "")
    if password != current_app.config["ADMIN_PASSWORD"]:
        flash("管理员密码不正确", "error")
        return redirect(url_for("student.login"))
    session.clear()
    session["is_admin"] = True
    flash("管理员登录成功", "success")
    return redirect(url_for("admin.activities"))


@student_bp.get("/logout")
def logout():
    session.clear()
    flash("已退出登录", "success")
    return redirect(url_for("student.login"))


# ---------------------------------------------------------------- 学生端活动
@student_bp.get("/")
def index():
    return redirect(url_for("student.activities"))


@student_bp.get("/activities")
def activities():
    keyword = request.args.get("q", "").strip()
    rows = ActivityRepository(extensions.session()).list(keyword or None)
    svc = service()
    my_id = session.get("student_id")
    reg_repo = RegistrationRepository(extensions.session())
    view_rows = []
    for activity in rows:
        view_rows.append(
            {
                "activity": activity,
                "stats": svc.stats(activity.activity_id),
                "mine": reg_repo.latest_of(activity.activity_id, my_id) if my_id else None,
            }
        )
    return render_template(
        "activities.html", rows=view_rows, keyword=keyword, is_student=bool(my_id)
    )


@student_bp.get("/activities/<int:activity_id>")
def activity_detail(activity_id: int):
    activity = ActivityRepository(extensions.session()).get(activity_id)
    svc = service()
    my_id = session.get("student_id")
    mine = None
    if my_id:
        mine = RegistrationRepository(extensions.session()).latest_of(activity_id, my_id)
    return render_template(
        "activity_detail.html",
        activity=activity,
        stats=svc.stats(activity_id),
        mine=mine,
    )


@student_bp.post("/activities/<int:activity_id>/register")
@student_login_required
def register(activity_id: int):
    try:
        service().register(activity_id, session["student_id"])
        flash("报名成功", "success")
    except DomainError as exc:
        flash(exc.message, "error")
    return redirect(url_for("student.activity_detail", activity_id=activity_id))


@student_bp.post("/registrations/<int:registration_id>/cancel")
@student_login_required
def cancel(registration_id: int):
    try:
        registration = service().cancel(registration_id, session["student_id"])
        flash("已取消报名", "success")
        return redirect(url_for("student.activity_detail", activity_id=registration.activity_id))
    except DomainError as exc:
        flash(exc.message, "error")
        return redirect(url_for("student.my_registrations"))


@student_bp.get("/my/registrations")
@student_login_required
def my_registrations():
    rows = RegistrationRepository(extensions.session()).list_of_student(session["student_id"])
    return render_template("my_registrations.html", rows=rows)


@student_bp.get("/messages")
@student_login_required
def messages():
    repo = MessageRepository(extensions.session())
    rows = repo.list_of_student(session["student_id"])
    return render_template("messages.html", rows=rows)


@student_bp.post("/messages/read-all")
@student_login_required
def read_all_messages():
    MessageRepository(extensions.session()).mark_all_read(session["student_id"])
    flash("已全部标记为已读", "success")
    return redirect(url_for("student.messages"))


# ---------------------------------------------------------------- 管理端
def _parse_activity_form(form) -> dict:
    title = form.get("title", "").strip()
    if not title:
        raise ValidationError("活动名称不能为空")
    if len(title) > 120:
        raise ValidationError("活动名称不能超过 120 字")
    category = form.get("category", "").strip() or "其他"
    location = form.get("location", "").strip() or "待定"
    raw_start = form.get("start_at", "").strip()
    try:
        start_at = datetime.strptime(raw_start, "%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise ValidationError("活动时间格式不正确") from exc
    raw_capacity = form.get("capacity", "").strip()
    try:
        capacity = int(raw_capacity)
    except ValueError as exc:
        raise ValidationError("人数上限必须为正整数") from exc
    if capacity <= 0 or capacity > 1000:
        raise ValidationError("人数上限必须在 1—1000 之间")
    raw_policy = form.get("policy_type", "").strip()
    try:
        policy_type = PolicyType(raw_policy).value
    except ValueError as exc:
        raise ValidationError("报名方式不合法") from exc
    return {
        "title": title,
        "category": category,
        "start_at": start_at,
        "location": location,
        "capacity": capacity,
        "policy_type": policy_type,
    }


@admin_bp.get("/")
@admin_login_required
def index():
    return redirect(url_for("admin.activities"))


@admin_bp.get("/activities")
@admin_login_required
def activities():
    repo = ActivityRepository(extensions.session())
    svc = service()
    rows = [
        {"activity": activity, "stats": svc.stats(activity.activity_id)}
        for activity in repo.list()
    ]
    return render_template("admin_activities.html", rows=rows)


@admin_bp.route("/activities/new", methods=["GET", "POST"])
@admin_login_required
def activity_new():
    if request.method == "POST":
        try:
            fields = _parse_activity_form(request.form)
            ActivityRepository(extensions.session()).create(**fields)
            flash("活动创建成功", "success")
            return redirect(url_for("admin.activities"))
        except DomainError as exc:
            flash(exc.message, "error")
    return render_template(
        "admin_activity_form.html",
        activity=None,
        policies=default_registry.all,
        default_start="",
    )


@admin_bp.route("/activities/<int:activity_id>/edit", methods=["GET", "POST"])
@admin_login_required
def activity_edit(activity_id: int):
    repo = ActivityRepository(extensions.session())
    activity = repo.get(activity_id)
    if request.method == "POST":
        try:
            fields = _parse_activity_form(request.form)
            repo.update(activity_id, **fields)
            flash("活动已更新", "success")
            return redirect(url_for("admin.activities"))
        except DomainError as exc:
            flash(exc.message, "error")
    return render_template(
        "admin_activity_form.html",
        activity=activity,
        policies=default_registry.all,
        default_start=activity.start_at.strftime("%Y-%m-%dT%H:%M"),
    )


@admin_bp.post("/activities/<int:activity_id>/delete")
@admin_login_required
def activity_delete(activity_id: int):
    try:
        ActivityRepository(extensions.session()).delete(activity_id)
        flash("活动已删除", "success")
    except DomainError as exc:
        flash(exc.message, "error")
    return redirect(url_for("admin.activities"))


@admin_bp.get("/reviews")
@admin_login_required
def reviews():
    repo = RegistrationRepository(extensions.session())
    rows = repo.list_by_status(RegistrationStatus.PENDING)
    return render_template("admin_reviews.html", rows=rows)


@admin_bp.post("/registrations/<int:registration_id>/approve")
@admin_login_required
def approve(registration_id: int):
    try:
        service().approve(registration_id)
        flash("已批准该报名", "success")
    except DomainError as exc:
        flash(exc.message, "error")
    return redirect(url_for("admin.reviews"))


@admin_bp.post("/registrations/<int:registration_id>/reject")
@admin_login_required
def reject(registration_id: int):
    try:
        service().reject(registration_id)
        flash("已拒绝该报名", "success")
    except DomainError as exc:
        flash(exc.message, "error")
    return redirect(url_for("admin.reviews"))


# ---------------------------------------------------------------- 错误页
@student_bp.app_errorhandler(404)
def not_found(error):  # noqa: ARG001
    return render_template("error.html", code=404, message="页面不存在"), 404


@student_bp.app_errorhandler(500)
def server_error(error):  # noqa: ARG001
    return render_template("error.html", code=500, message="系统内部错误"), 500
