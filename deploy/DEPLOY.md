# 部署说明（CampusEvent change-v2）

## 1. 已完成的部署（阿里云轻量应用服务器）

| 项 | 值 |
|---|---|
| 主机 | 阿里云轻量应用服务器，公网 IP `47.106.160.76`（Ubuntu 24.04，2 vCPU / 2 GiB） |
| 部署方式 | 解包仓库到 `/opt/campus-event` → `python3 -m venv .venv` → `pip install -r requirements.txt` → 写入 `.env` → systemd 启动 `gunicorn -w 2 -b 0.0.0.0:8000 run:app` |
| 代码位置 | `/opt/campus-event` |
| 进程托管 | systemd 单元 `campus-event.service`（`Restart=always`，开机自启） |
| 验证结果 | 服务器上 `pytest -q` → 36 passed（baseline 23 + v2 变更 13）；`curl 127.0.0.1:8000/login` → HTTP 200；外网访问 → HTTP 200 |
| 公网地址 | <http://47.106.160.76:8000> |
| 运行日志 | `journalctl -u campus-event` |

**关于公网地址**：系统已部署在上述阿里云服务器的 8000 端口，安全组已放行 TCP 8000，
从外部网络实测可正常打开登录页，可直接用浏览器访问，非本机回环地址。

## 2. 迁移到另一台公网云服务器（三步）

```bash
# 1) 上传代码（git clone 或 scp 后解压）
git clone <仓库地址> /opt/campus-event && cd /opt/campus-event

# 2) 一键部署（自动建 venv、跑测试、启动 gunicorn）
bash deploy/deploy.sh 8000

# 3) 放行端口
# 阿里云/腾讯云控制台 → 安全组 → 入方向 → 添加 TCP:8000
# 若用 ufw：sudo ufw allow 8000/tcp
```

访问：`http://<公网IP>:8000`

## 3. 生产化建议（可选）

- 用 systemd 托管：`sudo cp deploy/campus-event.service /etc/systemd/system/ && sudo systemctl enable --now campus-event`
- 前置 nginx 反向代理 80/443，并开启 HTTPS。
- 将 SQLite 换成 MySQL（改 `CAMPUS_EVENT_DB` 为 MySQL 连接串，SQLAlchemy 自动适配）。
- 会话密钥务必用 `.env` 中的随机值，不要使用默认值。

## 4. 常见问题

| 现象 | 排查 |
|---|---|
| 外网 502 / 连接超时 | 安全组未放行端口；或 gunicorn 只监听了 127.0.0.1（确认 `-b 0.0.0.0:PORT`） |
| 页面 500 | 查看 `/var/log/campus-event-error.log` 或 `journalctl -u campus-event` |
| 中文乱码 | 数据库文件编码；确认终端 `LANG=zh_CN.UTF-8` 或 `en_US.UTF-8` |
| 登录后会话丢失 | 多 worker 下需固定 `SECRET_KEY`（通过 `.env` 提供） |
