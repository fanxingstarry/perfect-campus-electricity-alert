#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""定时查询完美校园房间电量，并通过钉钉自定义机器人推送。"""
import json
import os
import signal
import sys
import time
from typing import Any
from zoneinfo import ZoneInfo

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from dingding import send_custom_robot_group_message

SCHOOL_ID = os.environ.get("SCHOOL_ID", "")
STUDENT_ID = os.environ.get("STUDENT_ID", "")
ROOM_VERIFY = os.environ.get("ROOM_VERIFY", "")
DINGTALK_ACCESS_TOKEN = os.environ.get("DINGTALK_ACCESS_TOKEN", "")
DINGTALK_SECRET = os.environ.get("DINGTALK_SECRET", "")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


VERBOSE = env_bool("VERBOSE")
SCHED_TZ = os.environ.get("SCHED_TZ", "Asia/Shanghai")
SCHEDULE_HOUR = int(os.environ.get("SCHEDULE_HOUR", "12"))
SCHEDULE_MINUTE = int(os.environ.get("SCHEDULE_MINUTE", "0"))
RUN_ON_START = env_bool("RUN_ON_START", True)

def log(*args_, **kwargs_):
    if VERBOSE:
        print(*args_, **kwargs_)


def safe_json_loads_once(s: str) -> Any:
    """
    尝试把可能带有额外转义的字符串解析为 JSON。
    只做一次解码（若 body 本身就是 dict/list 会直接返回）。
    """
    if isinstance(s, (dict, list)):
        return s
    if not isinstance(s, str):
        return s
    # 去掉两边可能的引号包裹
    s_strip = s.strip()
    try:
        return json.loads(s_strip)
    except Exception:
        # 可能内部是转义的 JSON 字符串，例如: "\"{...}\"" 或有转义的 \" 等
        # 先替换常见的转义序列，然后再尝试一次 json.loads
        # 这一步尽可能模仿原 bash sed 的处理
        s2 = s_strip.replace('\\"', '"')
        # 如果字符串是以双引号包裹的对象，去掉最外层引号
        if len(s2) >= 2 and s2[0] == '"' and s2[-1] == '"':
            s2 = s2[1:-1]
        try:
            return json.loads(s2)
        except Exception:
            # 解析失败则返回原始字符串
            return s

def fetch_perfect_campus_body(
    school_id: str,
    student_id: str,
    room_verify: str,
    timeout: int = 10,
) -> Any:
    url = "https://xqh5.17wanxiao.com/smartWaterAndElectricityService/SWAEServlet"
    payload = {
        "param": json.dumps(
            {
                "cmd": "h5_getstuindexpage",
                "roomverify": room_verify,
                "account": student_id,
            }
        ),
        "customercode": school_id,
        "method": "h5_getstuindexpage",
        "command": "JBSWaterElecService"
    }
    headers = {
        "User-Agent": "python-requests/3.x",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    log("正在请求完美校园电量接口")
    resp = requests.post(url, data=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    try:
        j = resp.json()
    except ValueError:
        try:
            j = json.loads(resp.text)
        except ValueError as exc:
            raise RuntimeError("无法解析完美校园接口返回的数据为 JSON。") from exc

    body = j.get("body") if isinstance(j, dict) else None
    if body is None:
        body = j

    body_parsed = safe_json_loads_once(body)
    if isinstance(body_parsed, str):
        body_parsed = safe_json_loads_once(body_parsed)

    log("完美校园电量数据获取成功")
    return body_parsed


# ---------- 主流程 ----------
def main_job():
    """
    这个函数会被定时器调用。务必捕获异常并返回（不要 sys.exit），
    否则 BlockingScheduler 也会退出或产生未期望的行为。
    """
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 启动检查任务")
    msg = ""
    try:
        body = fetch_perfect_campus_body(SCHOOL_ID, STUDENT_ID, ROOM_VERIFY)
    except Exception as e:
        print("请求或解析完美校园数据时出错：", e)
        # 记录错误并返回，不退出程序
        return

    try:
        log("返回数据类型：", type(body).__name__)
        odd_value = body['modlist'][1]['odd']
        print(f"odd_value = {odd_value}")

        has_money = (round(0.62 * odd_value, 2))

        msg = f"今天剩余电量：\n{odd_value}度({has_money}元)\n"

        week_use_list = body['modlist'][1].get('weekuselist', [])
        sorted_days = sorted(week_use_list, key=lambda x: x.get('date', ''), reverse=True)
        if sorted_days:
            latest_day = sorted_days[0]
            latest_date = latest_day.get('date', '')
            # 将日期从 "01-25" 格式转换为 "1月25日" 格式
            if latest_date and '-' in latest_date:
                month, day = latest_date.split('-')
                # 去除月份和日期的前导零
                month = str(int(month))  # "01" -> 1
                day = str(int(day))  # "25" -> 25
                formatted_date = f"{month}月{day}日"
            else:
                formatted_date = latest_date  # 如果格式不符，保持原样

            latest_usage = latest_day.get('use', '')
            latest_usage = int(latest_usage)

            money =(round(0.62 * latest_usage, 2))
            print(f"昨天用电量({formatted_date}):\n{latest_usage}度({money}元)")
            used = f"{formatted_date} 用电:\n{latest_usage}度({money}元)"
            msg = "\n".join([msg, used])
        else:
            print("没有找到用电数据")
    except Exception as e:
        print("处理返回数据时出错：", e)
        err = f"获取电量出现错误：{e}"
        msg = "\n".join([msg, err])

    try:
        send_custom_robot_group_message(
            access_token=DINGTALK_ACCESS_TOKEN,
            secret=DINGTALK_SECRET,
            msg=msg,
        )
        print("消息已发送:", msg)
    except Exception as e:
        print("发送钉钉/通知时出错：", e)



def start_scheduler():
    tz = ZoneInfo(SCHED_TZ)
    sched = BlockingScheduler(timezone=tz)

    trigger = CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, timezone=tz)
    sched.add_job(main_job, trigger, id="daily_check_power", replace_existing=True)
    print(
        f"调度器已启动，每天 {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} "
        f"({SCHED_TZ}) 执行 main_job。"
    )
    print("按 Ctrl+C 停止。")

    # 优雅停止处理
    def _shutdown(signum, frame):
        print("收到终止信号，准备停止调度器...")
        try:
            sched.shutdown(wait=False)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("调度器已停止。")


def validate_config() -> None:
    required = {
        "SCHOOL_ID": SCHOOL_ID,
        "STUDENT_ID": STUDENT_ID,
        "ROOM_VERIFY": ROOM_VERIFY,
        "DINGTALK_ACCESS_TOKEN": DINGTALK_ACCESS_TOKEN,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(f"缺少必需的环境变量: {', '.join(missing)}")

    if not 0 <= SCHEDULE_HOUR <= 23:
        raise SystemExit("SCHEDULE_HOUR 必须是 0 到 23 之间的整数")
    if not 0 <= SCHEDULE_MINUTE <= 59:
        raise SystemExit("SCHEDULE_MINUTE 必须是 0 到 59 之间的整数")


if __name__ == "__main__":
    validate_config()
    if RUN_ON_START:
        print("首次立即执行一次检查")
        main_job()
    start_scheduler()
