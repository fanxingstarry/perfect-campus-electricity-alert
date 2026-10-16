# !/usr/bin/env python

import base64
import hashlib
import hmac
import time
from typing import Any

import requests

def send_custom_robot_group_message(
    access_token: str,
    msg: str,
    secret: str = "",
    at_user_ids: list[str] | None = None,
    at_mobiles: list[str] | None = None,
    is_at_all: bool = False,
    timeout: int = 10,
) -> dict[str, Any]:
    """
    发送钉钉自定义机器人群消息
    :param access_token: 机器人 webhook 的 access_token
    :param secret: 机器人安全设置的加签secret
    :param msg: 消息内容
    :param at_user_ids: @的用户ID列表
    :param at_mobiles: @的手机号列表
    :param is_at_all: 是否@所有人
    :return: 钉钉API响应
    """
    if not access_token:
        raise ValueError("钉钉机器人的 access_token 不能为空")

    params = {"access_token": access_token}
    if secret:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).digest()
        params.update({
            "timestamp": timestamp,
            "sign": base64.b64encode(hmac_code).decode("utf-8"),
        })

    url = 'https://oapi.dingtalk.com/robot/send'
    body = {
        "at": {
            "isAtAll": str(is_at_all).lower(),
            "atUserIds": at_user_ids or [],
            "atMobiles": at_mobiles or []
        },
        "text": {
            "content": msg
        },
        "msgtype": "text"
    }
    headers = {'Content-Type': 'application/json'}
    resp = requests.post(url, params=params, json=body, headers=headers, timeout=timeout)
    resp.raise_for_status()
    result = resp.json()
    if result.get("errcode") != 0:
        raise RuntimeError(f"钉钉机器人返回错误: {result}")
    return result
