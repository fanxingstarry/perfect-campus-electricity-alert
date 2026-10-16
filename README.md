# 完美校园电量提醒

定时查询完美校园房间电量，并通过钉钉自定义机器人发送消息。支持直接运行和 Docker Compose 部署。

## 功能

- 启动时可立即查询一次，之后按每天固定时间执行
- 推送剩余电量和最近一天的用电量
- 支持钉钉机器人加签
- 所有账号、房间和机器人凭据均从环境变量读取

## 使用 Docker Compose 部署

1. 创建本地配置文件：

   ```powershell
   Copy-Item .env.example .env
   ```

2. 编辑 `.env`，填写学校、学号、房间验证编号和钉钉机器人配置。`.env` 已加入 `.gitignore` 和 `.dockerignore`，不会进入 Git 或 Docker 构建上下文。

3. 构建并启动：

   ```powershell
   docker compose up -d --build
   ```

4. 查看运行日志：

   ```powershell
   docker compose logs -f electricity-alert
   ```

默认在容器启动时立即检查一次，之后每天北京时间 12:00 执行。可以通过 `.env` 中的 `RUN_ON_START`、`SCHEDULE_HOUR`、`SCHEDULE_MINUTE` 和 `SCHED_TZ` 调整。

停止服务：

```powershell
docker compose down
```

更新代码后重新部署：

```powershell
docker compose up -d --build
```

## 配置项

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `SCHOOL_ID` | 是 | 完美校园学校编号 |
| `STUDENT_ID` | 是 | 查询电量所用的学号 |
| `ROOM_VERIFY` | 是 | 完美校园接口使用的房间验证编号 |
| `DINGTALK_ACCESS_TOKEN` | 是 | 钉钉自定义机器人 access token |
| `DINGTALK_SECRET` | 否 | 机器人启用“加签”时填写 `SEC...` secret |
| `SCHED_TZ` | 否 | 调度时区，默认 `Asia/Shanghai` |
| `SCHEDULE_HOUR` | 否 | 每天执行的小时，默认 `12` |
| `SCHEDULE_MINUTE` | 否 | 每天执行的分钟，默认 `0` |
| `RUN_ON_START` | 否 | 容器启动时是否立即执行，默认 `true` |
| `VERBOSE` | 否 | 是否输出详细日志，默认 `false` |

## 直接运行

需要 Python 3.10 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env` 后，将变量载入当前终端再运行 `python main.py`。也可以使用支持 `.env` 文件的进程管理工具。

## 隐私与安全

- 不要提交 `.env`、日志、接口响应或截图；这些内容可能包含学号、房间信息和机器人凭据。
- 建议为钉钉机器人启用“加签”，并限制机器人所在群及可发送内容。
- 如果凭据曾被提交到 Git、粘贴到公开页面或出现在共享日志中，请立即在对应平台轮换凭据。

安全问题请参阅 [SECURITY.md](SECURITY.md)。

## 许可证

本项目使用 [MIT License](LICENSE)。
