# -*- coding: utf-8 -*-
"""Webhook 告警模块 - 掉线通知 + 恢复通知"""

import re
import threading
import logging
import urllib.parse

import requests

from server import state, config_manager

logger = logging.getLogger('alert')

# 内网地址正则
_PRIVATE_IP_RE = re.compile(
    r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)|localhost'
)


def _is_valid_webhook_url(url):
    """校验 Webhook URL 是否合法"""
    if not url:
        return False
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    hostname = parsed.hostname or ''
    if _PRIVATE_IP_RE.match(hostname):
        return False
    return True


def _send_webhook(url, text):
    """在子线程中发送 Webhook 请求"""
    def _do_send():
        try:
            resp = requests.post(
                url,
                json={"text": text},
                timeout=5,
                headers={"Content-Type": "application/json"}
            )
            logger.info("Webhook 发送成功: %s (status=%d)", text, resp.status_code)
        except Exception as e:
            logger.warning("Webhook 发送失败: %s - %s", text, e)

    t = threading.Thread(target=_do_send, daemon=True)
    t.start()


def send_test_webhook(url):
    """发送测试 Webhook"""
    if not _is_valid_webhook_url(url):
        return False, "Webhook URL 不合法"
    try:
        resp = requests.post(
            url,
            json={"text": "这是一条测试消息 - ServerStatus-Rabbit"},
            timeout=5,
            headers={"Content-Type": "application/json"}
        )
        if resp.status_code < 400:
            return True, "测试消息已发送"
        return False, f"目标返回状态码 {resp.status_code}"
    except Exception as e:
        return False, f"发送失败: {e}"


def check_and_alert():
    """掉线检测 + 告警发送（由定时线程调用）"""
    settings = config_manager.load_settings()
    webhook_cfg = settings.get('webhook', {})
    timeout_seconds = webhook_cfg.get('timeout_seconds', 30)

    newly_offline, newly_online = state.check_offline(timeout_seconds)

    if not webhook_cfg.get('enabled', False) or not webhook_cfg.get('url', ''):
        return

    url = webhook_cfg['url']
    if not _is_valid_webhook_url(url):
        return

    servers = config_manager.get_servers()
    # 建立 username -> server info 的映射
    server_map = {s['username']: s for s in servers}

    for username in newly_offline:
        srv = server_map.get(username, {})
        # 禁用的节点不触发告警
        if srv.get('disabled', False):
            continue
        if not state.is_alert_sent(username):
            location = srv.get('location', '未知位置')
            name = srv.get('name', username)
            text = f"在{location}的{name}掉线了"
            _send_webhook(url, text)
            state.mark_alert_sent(username)

    for username in newly_online:
        srv = server_map.get(username, {})
        if srv.get('disabled', False):
            continue
        if state.is_alert_sent(username):
            location = srv.get('location', '未知位置')
            name = srv.get('name', username)
            text = f"在{location}的{name}恢复上线了"
            _send_webhook(url, text)
            state.clear_alert(username)


def start_checker():
    """启动掉线检测定时线程（每 10 秒扫描一次）"""
    def _loop():
        import time
        while True:
            try:
                check_and_alert()
            except Exception as e:
                logger.error("掉线检测异常: %s", e)
            time.sleep(10)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info("掉线检测线程已启动（每10秒扫描）")
