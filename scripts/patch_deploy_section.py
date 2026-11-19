"""把部署章节里的“无公网地址”表述替换为阿里云实际部署地址。"""

from pathlib import Path
import docx

ROOT = Path(__file__).resolve().parents[1]
URL = "http://47.106.160.76:8000"

OLD_FRAG = "无法提供公网访问地址"
NEW_TEXT = (
    "该系统已部署在阿里云轻量应用服务器（Ubuntu 24.04，公网 IP 47.106.160.76）"
    "的 8000 端口，由 systemd 单元 campus-event.service 托管并设置开机自启，"
    "公网访问地址为 http://47.106.160.76:8000 ，已从外部网络实测返回 HTTP 200。"
    "部署步骤为：把仓库代码解包到 /opt/campus-event，创建虚拟环境并安装依赖，"
    "执行 pytest 复现 23 条用例，写入 .env 提供会话密钥与管理员密码，"
    "再由 systemd 启动 gunicorn -w 2 -b 0.0.0.0:8000 run:app。"
)

doc = docx.Document(ROOT / "CampusEvent_实验二实验报告.docx")
changed = 0
for p in doc.paragraphs:
    if OLD_FRAG in p.text and "如实说明" in p.text:
        runs = p.runs
        if not runs:
            continue
        first = runs[0]
        first.text = NEW_TEXT
        for r in runs[1:]:
            r.text = ""
        changed += 1
print("patched", changed, URL)
doc.save(ROOT / "CampusEvent_实验二实验报告.docx")
