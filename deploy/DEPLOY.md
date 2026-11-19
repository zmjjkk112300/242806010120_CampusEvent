# 部署说明（CampusEvent baseline-v1）

## 1. 已完成的部署（课程提供的云主机）

| 项 | 值 |
|---|---|
| 主机 | 课程云主机（Linux，Python 3.12.11） |
| 部署方式 | `git archive` 打包 → 解包 → venv → `pip install -r requirements.txt` → `gunicorn -w 2 -b 0.0.0.0:8000 run:app --daemon` |
| 代码位置 | `/home/user/Doubao/chats/38454965453800706/CampusEvent` |
| 本机验证 | `curl 127.0.0.1:8000/login` → HTTP 200；服务器上 `pytest -q` → 23 passed |
| 运行日志 | `/tmp/ce-access.log`、`/tmp/ce-error.log` |

**关于公网地址（如实说明）**：该云主机的安全组/网关未对外放行 8000 端口（实测本机到
`9.163.246.29` 的 80/443/8000/8080 均不可达；该主机对外端口由平台网关占用 8080）。
因此系统已在云主机上实际运行，但无法给出可被外部浏览器访问的公网地址。
若课程要求必须公网可访问，请在自购云服务器（阿里云/腾讯云等）执行 `deploy/deploy.sh`，
并在安全组放行对应端口，README 第三节「五、配置项」无需修改。

## 2. 迁移到公网云服务器（三步）

```bash
# 1) 上传代码（git clone 或 scp 后解压）
git clone <仓库地址> /opt/CampusEvent && cd /opt/CampusEvent

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
