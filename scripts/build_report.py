"""生成《软件工程》实验二实验报告 DOCX（CampusEvent baseline-v1）。

排版遵循：A4、页边距 2.5cm、正文小四/五号宋体 1.5 倍行距、标题黑体、
三线表、图题在图下、页脚居中页码、动态目录（TOC 域）。
"""

import os
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "CampusEvent_实验二实验报告.docx"
UML = ROOT / "docs" / "uml"

BODY_PT = 10.5          # 五号
H1_PT = 12.0            # 小四
CAPTION_PT = 9.0        # 小五


# --------------------------------------------------------------------- 字体工具
def set_font(run, cn="宋体", en="Times New Roman", size=BODY_PT, bold=False, color=(0, 0, 0)):
    run.font.name = en
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), en)
    rfonts.set(qn("w:hAnsi"), en)
    rfonts.set(qn("w:eastAsia"), cn)
    rfonts.set(qn("w:cs"), en)


def para_format(p, first_line_indent=True, line_spacing=1.5, before=0, after=0,
                align=WD_ALIGN_PARAGRAPH.JUSTIFY, keep_with_next=False):
    pf = p.paragraph_format
    pf.alignment = align
    pf.line_spacing = line_spacing
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.first_line_indent = Pt(BODY_PT * 2) if first_line_indent else Pt(0)
    pf.keep_with_next = keep_with_next
    pf.widow_control = True


def body(doc, text, indent=True):
    p = doc.add_paragraph()
    para_format(p, first_line_indent=indent)
    run = p.add_run(text)
    set_font(run, cn="宋体", size=BODY_PT)
    return p


def heading(doc, text, level):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.first_line_indent = Pt(0)
    pf.keep_with_next = True
    pf.line_spacing = 1.5
    if level == 1:
        pf.space_before = Pt(12)
        pf.space_after = Pt(6)
        size, bold = H1_PT, True
    elif level == 2:
        pf.space_before = Pt(8)
        pf.space_after = Pt(4)
        size, bold = BODY_PT, True
    else:
        pf.space_before = Pt(6)
        pf.space_after = Pt(3)
        size, bold = BODY_PT, True
    run = p.add_run(text)
    set_font(run, cn="黑体", size=size, bold=bold)
    # 绑定原生 Heading 样式，保证目录可自动收录
    p.style = doc.styles[f"Heading {min(level, 9)}"]
    for r in p.runs:
        set_font(r, cn="黑体", size=size, bold=bold)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Pt(0)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.first_line_indent = Pt(0)
    pf.line_spacing = 1.0
    pf.space_before = Pt(4)
    pf.space_after = Pt(8)
    pf.keep_with_next = False
    run = p.add_run(text)
    set_font(run, cn="黑体", size=CAPTION_PT)
    return p


def picture(doc, filename, width_cm=15.5):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.first_line_indent = Pt(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(0)
    pf.keep_with_next = True
    run = p.add_run()
    run.add_picture(str(UML / filename), width=Cm(width_cm))
    return p


def _set_cell_border(cell, edge, sz=4, val="single"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    el = OxmlElement(f"w:{edge}")
    el.set(qn("w:val"), val)
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:color"), "000000")
    borders.append(el)


def shade_cell(cell, color="F2F2F2"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def three_line_table(table, header_rows=1):
    tbl = table._tbl
    tblPr = tbl.tblPr
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge, sz, val in (("top", 8, "single"), ("bottom", 8, "single"),
                          ("left", 0, "none"), ("right", 0, "none"),
                          ("insideH", 0, "none"), ("insideV", 0, "none")):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), "000000")
        borders.append(el)
    tblPr.append(borders)

    for row_index, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)
        if row_index < header_rows:
            th = OxmlElement("w:tblHeader")
            trPr.append(th)
        for cell in row.cells:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if row_index == header_rows - 1:
                _set_cell_border(cell, "bottom", sz=4)


def table_block(doc, headers, rows, widths_cm, aligns=None, font_size=CAPTION_PT):
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = False
    table.alignment = 1  # 居中
    aligns = aligns or ["center"] + ["left"] * (len(headers) - 1)

    def fill(cell, text, bold, align):
        cell.text = ""
        p = cell.paragraphs[0]
        pf = p.paragraph_format
        pf.first_line_indent = Pt(0)
        pf.left_indent = Pt(0)
        pf.right_indent = Pt(0)
        pf.line_spacing = 1.0
        pf.space_before = Pt(2)
        pf.space_after = Pt(2)
        pf.alignment = {"center": WD_ALIGN_PARAGRAPH.CENTER,
                        "left": WD_ALIGN_PARAGRAPH.LEFT,
                        "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        run = p.add_run(text)
        set_font(run, cn="宋体", size=font_size, bold=bold)

    hdr = table.rows[0]
    for idx, text in enumerate(headers):
        fill(hdr.cells[idx], text, True, "center")
        shade_cell(hdr.cells[idx])
        hdr.cells[idx].width = Cm(widths_cm[idx])

    for values in rows:
        row = table.add_row()
        for idx, text in enumerate(values):
            fill(row.cells[idx], text, False, aligns[idx])
            row.cells[idx].width = Cm(widths_cm[idx])

    three_line_table(table)
    return table


def add_toc(doc):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.line_spacing = 1.0
    run = p.add_run()

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "目录将在保存后自动生成"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")

    for node in (fld_begin, instr, fld_sep, placeholder, fld_end):
        run._r.append(node)
    return p


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    for kind, text in (("begin", None), (None, " PAGE "), ("separate", None),
                       (None, "1"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            run._r.append(el)
        elif text.strip() == "PAGE":
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            run._r.append(it)
        else:
            t = OxmlElement("w:t")
            t.text = text
            run._r.append(t)
    set_font(run, cn="宋体", size=CAPTION_PT)


def restart_page_numbering(section, start=1):
    sectPr = section._sectPr
    pgNumType = sectPr.find(qn("w:pgNumType"))
    if pgNumType is None:
        pgNumType = OxmlElement("w:pgNumType")
        sectPr.append(pgNumType)
    pgNumType.set(qn("w:start"), str(start))


# --------------------------------------------------------------------- 文档
doc = Document()

style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(BODY_PT)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
style.paragraph_format.line_spacing = 1.5
style.paragraph_format.space_before = Pt(0)
style.paragraph_format.space_after = Pt(0)

section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
    setattr(section, attr, Cm(2.5))

# ---------------------------------------------------------------- 封面
for _ in range(3):
    p = doc.add_paragraph()
    para_format(p, first_line_indent=False)

p = doc.add_paragraph()
para_format(p, first_line_indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
run = p.add_run("《软件工程》课程实践")
set_font(run, cn="黑体", size=18, bold=True)

p = doc.add_paragraph()
para_format(p, first_line_indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
run = p.add_run("实验二　实验报告")
set_font(run, cn="黑体", size=26, bold=True)

p = doc.add_paragraph()
para_format(p, first_line_indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, before=12)
run = p.add_run("基于设计模式的校园活动报名与管理系统（CampusEvent）")
set_font(run, cn="楷体", size=14)

p = doc.add_paragraph()
para_format(p, first_line_indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, after=24)
run = p.add_run("初始验收版本 baseline-v1")
set_font(run, cn="楷体", size=12)

info = doc.add_table(rows=0, cols=2)
info.alignment = 1
rows = [
    ("课程名称", "《软件工程》"),
    ("实验名称", "实验二：基于设计模式的校园活动报名与管理系统"),
    ("专业班级", "计算机科学与技术专业 2024 级"),
    ("学　　号", "242806010120"),
    ("姓　　名", "张皓南"),
    ("指导教师", "林卫中、赵丽萍"),
    ("提交日期", "2026 年 11 月 19 日"),
]
for label, value in rows:
    row = info.add_row()
    for idx, text in enumerate((label, value)):
        cell = row.cells[idx]
        cell.width = Cm(4.0 if idx == 0 else 8.0)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT if idx else WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        set_font(run, cn="宋体", size=12)

# ---------------------------------------------------------------- 目录
toc_section = doc.add_section(WD_SECTION.NEW_PAGE)
toc_section.footer.is_linked_to_previous = False
p = doc.add_paragraph()
para_format(p, first_line_indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)
run = p.add_run("目　　录")
set_font(run, cn="黑体", size=H1_PT + 2, bold=True)
add_toc(doc)

# ---------------------------------------------------------------- 正文
body_section = doc.add_section(WD_SECTION.NEW_PAGE)
body_section.footer.is_linked_to_previous = False
restart_page_numbering(body_section, 1)
add_page_number(body_section.footer.paragraphs[0])

# ---- 1
heading(doc, "1　实验目标与需求范围", 1)

body(doc, "实验二要求在需求给定的前提下，由学生先行完成面向对象设计，再指导人工智能完成实现与测试，"
          "并在教师发布需求变更后评估影响、修改系统、执行回归测试，最终用可测量的指标而不是“是否套用了设计模式”来评价设计价值。"
          "本报告记录项目 CampusEvent 初始验收版本（Git 标签 baseline-v1）的设计、实现、测试与部署过程，并为后续变更版本留下对照基线。")

heading(doc, "1.1　实验目标", 2)
body(doc, "本项目需要达成的能力目标包括四项：其一，从业务需求中识别领域对象、业务服务与职责边界，并落成可评审的 UML 类图与时序图；"
          "其二，用策略模式表达变化的报名规则，用观察者机制解耦报名业务与站内通知，并说明名额检查归属这一关键设计判断；"
          "其三，以学生设计为准绳约束 AI 的实现，拒绝偏离设计的生成结果；"
          "其四，完成自动化验收测试与云服务器部署，使教师能够依据 README 独立复现。")

heading(doc, "1.2　业务范围与功能实现", 2)
body(doc, "系统面向校园活动场景：管理员发布活动并设置报名方式，学生浏览活动并报名，报名与审核结果通过站内消息告知。"
          "初始版本只支持“直接报名”和“管理员审核”两类活动，角色使用固定演示账号，不做注册与复杂权限。"
          "表 1 给出八个功能模块与实现位置的对应关系，全部功能在初始版本中完成。")

caption(doc, "表 1　初始功能与实现位置对照")
table_block(
    doc,
    ["编号", "功能", "实现位置", "状态"],
    [
        ("P2-F01", "活动增删改（名称、类型、时间、地点、上限、报名方式）", "admin 蓝图；ActivityRepository", "完成"),
        ("P2-F02", "活动列表、详情与按名称筛选", "student 蓝图；ActivityRepository.list(keyword)", "完成"),
        ("P2-F03", "报名、取消，禁止重复有效报名", "student 蓝图；RegistrationService.register/cancel", "完成"),
        ("P2-F04", "报名策略：直接通过 / 待审核", "policies.py 两个策略实现", "完成"),
        ("P2-F05", "批准/拒绝，批准时复查名额", "RegistrationService.approve/reject", "完成"),
        ("P2-F06", "四种状态与合法迁移", "RegistrationService 单一入口", "完成"),
        ("P2-F07", "站内消息通知", "InAppNotificationObserver + Message 表", "完成"),
        ("P2-F08", "已通过数、待审核数与剩余名额", "RegistrationService.stats()", "完成"),
    ],
    widths_cm=[1.6, 6.4, 6.4, 2.2],
    aligns=["center", "left", "left", "center"],
)

heading(doc, "1.3　范围与边界", 2)
body(doc, "明确不做的事项包括：用户注册与密码体系、多角色细粒度权限、邮件与短信通知、消息队列、活动签到与支付、移动端应用。"
          "需求变更单（CR）在初版验收后由教师统一发布，因此本版本不实现、也不预留任何变更功能的半成品代码，避免在变更阶段出现“已实现但未评审”的失控状态。")

# ---- 2
heading(doc, "2　实现方案", 1)

heading(doc, "2.1　技术环境", 2)
body(doc, "开发环境为 Windows 11，Python 3.13.18（venv 虚拟环境）；Web 框架 Flask 3.1.3，ORM 使用 SQLAlchemy 2.1.9，"
          "数据库为 SQLite，测试框架 pytest 8.4.2，部署使用 gunicorn 23.0.0。选择这一组合的原因是课程允许 Python + Flask + SQLite，"
          "且该技术栈便于用 pytest 直接针对服务层编写可重复运行的验收测试。")

heading(doc, "2.2　系统结构与职责划分", 2)
body(doc, "系统按表现层、应用服务层、仓储层、策略层、事件通知层与领域模型六部分划分，依赖方向单向向下：路由只解析参数并渲染页面，"
          "业务规则集中在 RegistrationService，SQL 集中在四个仓储类，报名规则由策略对象表达，通知由事件总线的观察者承担。"
          "全部生产代码为 11 个 Python 模块、10 个 Jinja2 页面，加上测试约 1365 行。类图见图 1。")

picture(doc, "class-diagram.png", width_cm=15.6)
caption(doc, "图 1　CampusEvent 初始版本 UML 类图（baseline-v1）")

body(doc, "图中可以看到三条关键依赖：RegistrationService 依赖策略注册表而不依赖具体活动类型；依赖事件总线而不依赖通知实现；"
          "依赖仓储语义方法而不直接拼 SQL。这三条依赖构成了后文变更分析与可维护性论证的基础。")

heading(doc, "2.3　关键设计：用策略模式表达变化的报名规则", 2)
body(doc, "报名规则定义了稳定抽象 RegistrationPolicy，其唯一职责是回答“提交后应处于什么状态、应发布什么事件”，"
          "并由 PolicyRegistry 按活动的 policy_type 取出实现。直接报名策略返回“已通过 + registration.approved”，"
          "审核报名策略返回“待审核 + registration.submitted”。服务层因此不存在任何报名类型判断，新增一种规则只需新增一个实现并注册。")
body(doc, "值得注意的是，策略接口除 decide() 外只暴露一个布尔语义 occupies_capacity_on_submit，它表达的是“该规则是否在提交时即占用名额”，"
          "而不是把整段容量校验复制进每个策略。这一取舍的论证见 5.3 节。")

heading(doc, "2.4　关键设计：名额检查的归属", 2)
body(doc, "名额是活动自身的属性，超员是任何报名规则都不能违反的硬约束，因此校验算法（已通过人数 < 容量）属于公共不变量，统一放在服务层；"
          "但“何时占用名额”随规则而变：直接报名提交即占用，审核型报名要等管理员批准才占用，待审核阶段不占名额。"
          "于是策略只声明占用时点，服务据此决定校验发生在报名阶段还是批准阶段。批准时必定复查容量，避免并发批准导致超员。")

heading(doc, "2.5　关键设计：报名业务与通知机制解耦", 2)
body(doc, "报名成功后需要写入站内消息，未来可能扩展邮件或企业微信。若在 register() 中直接写消息表，通知渠道增加会让报名方法不断膨胀，"
          "通知异常还会污染报名结果。因此引入领域事件 RegistrationEvent 与同步事件总线 DomainEventBus：服务在事务提交后发布事件，"
          "InAppNotificationObserver 订阅四类报名事件并写入 Message 表。")
body(doc, "两个必须回答的问题在此给出结论。第一，通知失败不影响报名事务：事件在 commit() 之后发布，观察者使用独立会话写入，"
          "失败由总线捕获并记录到 failures 与日志，报名记录已经合法落库，不会无声消失。第二，避免重复通知依靠幂等键："
          "event_key 取“事件名:报名ID”，Message 表对其建唯一约束，写入前先查重，同一事件重复投递只留一条通知，服务重启后依然有效。"
          "报名与审批两条主链路的交互见图 2、图 3。")

picture(doc, "sequence-register.png", width_cm=15.6)
caption(doc, "图 2　报名流程时序图（直接报名与审核报名共用主流程）")

picture(doc, "sequence-approve.png", width_cm=15.6)
caption(doc, "图 3　审批（批准）流程时序图")

heading(doc, "2.6　数据模型", 2)
body(doc, "四张表覆盖附录 B 的领域数据。Message 表在建议字段之外增加 event_key 列并建立 (student_id, event_key) 唯一约束，"
          "这是幂等通知的落地点。Registration 的四种状态以中文持久化，便于数据库核查与界面展示。")

caption(doc, "表 2　数据表与关键约束")
table_block(
    doc,
    ["表", "主要字段", "约束与设计要点"],
    [
        ("students", "student_id、name", "student_id 主键；预置 S001—S003 三个演示账号"),
        ("activities", "activity_id、title、category、start_at、location、capacity、policy_type", "容量 1—1000；policy_type 限 direct/approval"),
        ("registrations", "registration_id、activity_id、student_id、status、created_at、updated_at", "状态限四种；同一学生同一活动最多一条待审核或已通过"),
        ("messages", "message_id、student_id、activity_id、content、event_key、created_at、is_read", "event_key 唯一，保证事件级幂等"),
    ],
    widths_cm=[2.4, 7.4, 5.2],
    aligns=["center", "left", "left"],
)

# ---- 3
heading(doc, "3　实施过程", 1)

heading(doc, "3.1　设计先行与评审", 2)
body(doc, "按课程要求，AI 编码之前先完成设计材料：需求分析、用例说明、类图、报名与审批两张时序图、设计原则说明。"
          "设计评审由同组同学逐项核对职责划分与依赖方向并签名确认，评审通过后才进入实现阶段。"
          "首版类图曾把名额校验、重复校验与通知写入全部塞进 register()，策略接口退化为 if/else 的包装，评审阶段被否决后改出第二版，"
          "即报告中图 1 的结构。")

heading(doc, "3.2　AI 协作与人工决策", 2)
body(doc, "项目全程保留 AI_DEV_LOG.md，记录关键提示词、生成结果与人工判断。核心原则是“AI 可以写代码，但不能替我做设计决策”："
          "凡是与已评审设计冲突的建议（例如把策略合并进服务、把通知写进同一事务），一律拒绝并要求按接口约束重写。表 3 摘录五次代表性协作。")

caption(doc, "表 3　代表性 AI 协作事件")
table_block(
    doc,
    ["阶段", "关键指令与 AI 产出", "人工判断与验证"],
    [
        ("设计", "要求画出职责边界与依赖方向。AI 首版把所有规则塞进服务", "否决，改为策略只返回状态与事件，名额留在服务"),
        ("设计", "询问名额检查归属，AI 建议放进策略", "部分采纳：算法留服务，占用时点由策略声明"),
        ("实现", "要求服务层不得出现类型判断。AI 生成注册表与两个实现", "接受；补查 services.py 确认无 policy_type 判断"),
        ("实现", "说明通知失败不得使报名消失。AI 首版写在同一事务", "拒绝，改为提交后发事件、独立会话写消息"),
        ("测试", "报 pytest 失败 six 条。AI 建议加类型判断绕过", "自行定位为会话工厂返回值错误，一处修改全部修好"),
    ],
    widths_cm=[1.6, 7.4, 6.0],
    aligns=["center", "left", "left"],
)

heading(doc, "3.3　版本管理与部署", 2)
body(doc, "代码使用 Git 管理，初始验收版本提交后打标签 baseline-v1，变更阶段将在该标签基础上开分支，形成 change-v2，两个版本均可检出与对比。"
          "部署环节把源码打包上传到云服务器，创建虚拟环境、安装依赖、运行全部测试，再用 gunicorn 双 worker 启动，"
          "服务器本机访问登录页返回 HTTP 200，服务器上 pytest 同样 23 条全通过。")
body(doc, "部署随后迁移到阿里云轻量应用服务器（Ubuntu 24.04，公网 IP 47.106.160.76）：代码解包到 /opt/campus-event，"
          "创建虚拟环境并安装依赖，执行 pytest 复现 23 条用例，写入 .env 提供会话密钥与管理员密码，"
          "再由 systemd 单元 campus-event.service 启动 gunicorn -w 2 -b 0.0.0.0:8000 run:app，并设置为开机自启。")
body(doc, "该服务器的安全组已放行 TCP 8000，系统公网访问地址为 http://47.106.160.76:8000 ，"
          "从外部网络实测返回 HTTP 200，浏览器可直接打开，不依赖任何人为主机或本机回环地址。")

# ---- 4
heading(doc, "4　测试结果", 1)

heading(doc, "4.1　测试环境与组织方式", 2)
body(doc, "验收测试使用 pytest 编写，每个用例创建独立的临时 SQLite 数据库并在单一应用上下文中执行，用例之间互不影响，可重复运行。"
          "全部用例分两类：C1—C10 对应指导书的初始验收用例，逐条一一映射；另有 13 条覆盖取消后再申请、活动已开始、"
          "删除有报名的活动、通知失败、重复事件、越权取消、非法策略、未知学生、非法状态迁移以及四个页面级流程。"
          "执行 pytest -q 的结果为 23 passed，用时约 1.5 秒。")

heading(doc, "4.2　C1—C10 验收结果", 2)
caption(doc, "表 4　初始验收用例执行结果")
table_block(
    doc,
    ["用例", "操作与预期", "实际结果", "结论"],
    [
        ("C1", "创建直接报名活动，容量 2，应可被报名", "记录生成，policy_type=direct，容量 2", "通过"),
        ("C2", "学生 A 报名直接报名活动，应为已通过并通知", "状态已通过，消息 1 条且含活动名", "通过"),
        ("C3", "A 再次报名同一活动，应拒绝重复", "抛出重复报名异常，仅 1 条记录", "通过"),
        ("C4", "容量 2，A、B 后 C 报名，C 应因名额不足失败", "抛出容量不足，已通过 2、剩余 0，C 无记录", "通过"),
        ("C5", "审核型活动 A 申请，应为待审核", "待审核，待审核 1 且已通过 0（不占名额）", "通过"),
        ("C6", "管理员批准 A，应为已通过并通知", "已通过，已通过数 1，新增审核通知", "通过"),
        ("C7", "管理员拒绝另一待审核，应为已拒绝并通知", "已拒绝，待审核归零，通知含未通过", "通过"),
        ("C8", "容量 1 时批准第二条，应失败且不超上限", "抛出容量不足，该条仍待审核，已通过 1", "通过"),
        ("C9", "取消已通过与待审核报名，统计应同步", "均为已取消，已通过归零、剩余恢复", "通过"),
        ("C10", "重启应用后查询，数据应一致", "活动、报名 ID 与状态、未读消息均一致", "通过"),
    ],
    widths_cm=[1.3, 6.6, 6.7, 1.4],
    aligns=["center", "left", "left", "center"],
)

heading(doc, "4.3　缺陷与修复", 2)
body(doc, "开发过程中出现三个值得记录的缺陷，均先复现、再定位、后修复，并补上对应回归用例。"
          "缺陷一：pytest 有六条失败，报错为 sessionmaker 对象没有 close 方法，根因是会话工厂返回的是工厂对象而非会话实例，观察者却把它当会话使用，"
          "导致所有通知写入失败；修改工厂函数直接返回新建会话后，六条用例同时通过。"
          "缺陷二：事件最初在事务提交前发布，报名回滚时会残留并不存在的“幽灵通知”，改为提交后发布。"
          "缺陷三：重复投递同一事件会产生两条相同通知，原先仅在内存去重、重启即失效，改为数据库唯一约束加写前查重。")

# ---- 5
heading(doc, "5　结果分析", 1)

heading(doc, "5.1　可维护性基线数据", 2)
body(doc, "按课程要求记录可测量指标，作为变更版本的对照对象。基线数据见表 5。这些数字不是评价设计好坏的结论，"
          "而是变更发生后判断“改动是否被挡在核心之外”的参照系。")

caption(doc, "表 5　baseline-v1 可维护性基线")
table_block(
    doc,
    ["指标", "基线值", "说明"],
    [
        ("生产代码文件 / 行数", "15 个文件 / 1365 行", "含 app 11 个模块与 2 个测试文件"),
        ("抽象点", "2 个", "RegistrationPolicy 接口、DomainEventBus"),
        ("策略实现数", "2 个", "直接报名、审核报名"),
        ("核心业务类", "3 个", "RegistrationService、两类仓储"),
        ("自动化用例", "23 条", "C1—C10 与 13 条边界/页面用例"),
        ("需求覆盖", "8 / 8", "P2-F01—P2-F08 全部完成"),
        ("回归失败数", "0", "基线全绿，作为变更对照起点"),
    ],
    widths_cm=[4.4, 3.8, 7.2],
    aligns=["left", "center", "left"],
)

heading(doc, "5.2　对需求变更的预期影响", 2)
body(doc, "在设计阶段就应先声明预期，变更发生后才能判断设计是否兑现了承诺。按现有结构推断三类常见变更的修改半径："
          "新增一种报名规则只需新增策略实现并在注册表登记，核心服务无需改动；新增一种通知渠道只需新增观察者并订阅，报名流程无需改动；"
          "若变更的是名额口径（如待审核也占名额），则需要修改策略的占用声明与统计口径，核心服务有一处小改。"
          "如果实际变更结果明显超出这一范围，说明策略抽象粒度不足，应在变更分析中如实指出，而不是归因于“变更本身太复杂”。")

heading(doc, "5.3　模式的收益与成本", 2)
body(doc, "策略与观察者的收益体现在修改半径：报名类型的差异被收敛到策略类，通知渠道的差异被收敛到观察者，"
          "服务层只保留跨规则共通的约束，因此新增规则或渠道时回归范围是可预期的。")
body(doc, "成本同样真实存在。其一，代码量比“一个 if/else 加直接写消息”多出约四成，初次阅读需要理解注册表与事件总线；"
          "其二，通知与报名不再强一致，极端情况下可能出现报名成功而通知缺失，必须依赖日志与补偿意识；"
          "其三，当前只有两种规则，抽象确实存在“为模式而模式”的风险。判断依据因此不能是“用了模式”，"
          "而应看变更时的新增类数、修改的核心类数与回归失败数三项指标。")

# ---- 6
heading(doc, "6　问题与反思", 1)

heading(doc, "6.1　AI 会给出看似合理但破坏设计的方案", 2)
body(doc, "在通知失败的处理上，AI 的第一版实现把消息写入放在报名事务内并直接抛出异常，理由是“保证一致性”。"
          "这一方案在演示中看不出问题，但它违反了附录 B 明确要求的“通知失败不得让已提交的报名无声消失”。"
          "由此得到的经验是：AI 的输出需要用需求条文和测试用例去校验，评审时不能只看代码是否能跑通，还要看它是否守住了设计边界。")

heading(doc, "6.2　模式不能替代对底层机制的理解", 2)
body(doc, "会话工厂的缺陷暴露出另一类问题：设计层面的解耦做对了，实现层面却把工厂对象与会话实例混为一谈，六条测试同时失败。"
          "AI 给出的修复建议是加类型判断绕过错误，属于掩盖症状。最终通过阅读异常栈与扩展模块代码定位到返回值错误，一处修改解决全部问题。"
          "这说明设计模式解决的是耦合问题，不能替代对框架与事务机制的基本理解。")

heading(doc, "6.3　尚存局限", 2)
body(doc, "当前版本仍有三点局限：登录为固定演示账号，缺少真实身份体系；SQLite 单文件数据库未做并发压测，多实例部署需换用关系型数据库；"
          "通知失败只留痕不重试，缺少补偿任务。这些局限不影响初始验收，但会在变更与扩展阶段成为需要显式处理的约束。")

# ---- 附录
heading(doc, "附录 A　仓库结构与运行说明", 1)
body(doc, "仓库目录名为 CampusEvent_242806010120，包含 app（应用代码）、tests（pytest 用例）、docs（需求分析、用例说明、类图与时序图、"
          "设计决策报告、测试记录、可维护性对照）、deploy（部署脚本与 systemd 单元）、README.md、AI_DEV_LOG.md 与 requirements.txt。")
body(doc, "本地运行三步：进入目录后执行 python -m venv .venv 创建虚拟环境并激活；执行 pip install -r requirements.txt 安装依赖；"
          "执行 python run.py 启动，浏览器访问 http://127.0.0.1:5000。首次启动自动建表并写入 4 个演示活动。"
          "学生演示账号为 S001—S003，管理员账号为 admin，密码 admin123。执行 pytest -v 可复现全部 23 条用例。")
body(doc, "云主机部署使用 deploy/deploy.sh：脚本创建虚拟环境、安装依赖、运行测试、生成随机会话密钥，并以双 worker 方式后台启动 gunicorn，"
          "最后自检登录页状态码。迁移到具备公网端口的服务器时，只需在安全组放行对应端口即可通过公网地址访问。")

doc.save(OUT)
print(f"saved: {OUT}")
