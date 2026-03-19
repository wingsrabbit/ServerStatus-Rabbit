# -*- coding: utf-8 -*-
"""HTTPS 与证书管理模块 - certbot 自动申请 / 手动上传 / 证书续期"""

import os
import ssl
import subprocess
import threading
import time
import logging

from server import config_manager

logger = logging.getLogger('https_manager')

CERTS_DIR = os.path.join(config_manager.DATA_DIR, 'certs')
MANUAL_CERTS_DIR = os.path.join(CERTS_DIR, 'manual')
LETSENCRYPT_DIR = os.path.join(CERTS_DIR, 'letsencrypt')


def request_letsencrypt_cert(domain, email):
    """使用 certbot standalone 模式申请 Let's Encrypt 证书"""
    cmd = [
        'certbot', 'certonly', '--standalone', '--non-interactive', '--agree-tos',
        '--email', email,
        '-d', domain,
        '--config-dir', LETSENCRYPT_DIR,
        '--work-dir', '/tmp/certbot-work',
        '--logs-dir', '/tmp/certbot-logs'
    ]
    logger.info("执行 certbot 申请: %s", ' '.join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            cert_path = os.path.join(LETSENCRYPT_DIR, 'live', domain, 'fullchain.pem')
            key_path = os.path.join(LETSENCRYPT_DIR, 'live', domain, 'privkey.pem')
            if os.path.exists(cert_path) and os.path.exists(key_path):
                logger.info("certbot 申请成功: %s", domain)
                return True, cert_path, key_path
            return False, None, None
        else:
            error_msg = result.stderr or result.stdout or "未知错误"
            logger.error("certbot 申请失败: %s", error_msg)
            return False, None, None
    except subprocess.TimeoutExpired:
        logger.error("certbot 执行超时")
        return False, None, None
    except FileNotFoundError:
        logger.error("certbot 未安装")
        return False, None, None


def renew_letsencrypt():
    """续期 Let's Encrypt 证书"""
    cmd = [
        'certbot', 'renew', '--standalone',
        '--config-dir', LETSENCRYPT_DIR,
        '--work-dir', '/tmp/certbot-work',
        '--logs-dir', '/tmp/certbot-logs'
    ]
    logger.info("执行证书续期")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logger.info("证书续期成功")
            return True
        else:
            logger.warning("证书续期失败: %s", result.stderr or result.stdout)
            return False
    except Exception as e:
        logger.error("证书续期异常: %s", e)
        return False


def validate_cert_key_pair(cert_path, key_path):
    """验证证书和私钥是否匹配"""
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_path, key_path)
        return True
    except ssl.SSLError as e:
        logger.warning("证书私钥不匹配: %s", e)
        return False
    except Exception as e:
        logger.warning("证书验证异常: %s", e)
        return False


def create_ssl_context(cert_path, key_path):
    """创建 SSL 上下文"""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    return ctx


def get_cert_paths(settings):
    """根据 settings 获取证书路径"""
    https_cfg = settings.get('https', {})
    mode = https_cfg.get('mode', 'letsencrypt')

    if mode == 'letsencrypt':
        domain = https_cfg.get('domain', '')
        cert_path = os.path.join(LETSENCRYPT_DIR, 'live', domain, 'fullchain.pem')
        key_path = os.path.join(LETSENCRYPT_DIR, 'live', domain, 'privkey.pem')
    else:
        cert_path = https_cfg.get('cert_path', '')
        key_path = https_cfg.get('key_path', '')

    return cert_path, key_path


def start_renewal_checker(restart_https_callback):
    """启动证书续期定时线程（每 12 小时检查）"""
    def _loop():
        while True:
            time.sleep(12 * 3600)  # 12 小时
            try:
                settings = config_manager.load_settings()
                https_cfg = settings.get('https', {})
                if not https_cfg.get('enabled', False):
                    continue
                if https_cfg.get('mode') != 'letsencrypt':
                    continue

                logger.info("开始检查证书是否需要续期")
                success = renew_letsencrypt()
                if success and restart_https_callback:
                    restart_https_callback()
                    logger.info("证书续期后已重新加载 HTTPS")
            except Exception as e:
                logger.error("证书续期检查异常: %s", e)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info("证书续期检查线程已启动（每12小时）")
