# -*- coding: utf-8 -*-
"""配置管理模块 - 读写 config.json / admin.json / settings.json，原子写入"""

import os
import json
import logging
import tempfile

logger = logging.getLogger('config_manager')

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
ADMIN_FILE = os.path.join(DATA_DIR, 'admin.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
CERTS_DIR = os.path.join(DATA_DIR, 'certs')

DEFAULT_CONFIG = {"servers": []}

DEFAULT_ADMIN = {
    "password_hash": "",
    "secret_key": "",
    "locked": False,
    "fail_count": 0,
    "initialized": False
}

DEFAULT_SETTINGS = {
    "https": {
        "enabled": False,
        "mode": "letsencrypt",
        "domain": "",
        "email": "",
        "cert_path": "",
        "key_path": ""
    },
    "ports": {
        "web": 9191,
        "tcp": 9192,
        "https": 443,
        "web_enabled": True,
        "https_enabled": False
    },
    "webhook": {
        "enabled": False,
        "url": "",
        "timeout_seconds": 30
    },
    "ui": {
        "header": "Server Status",
        "subHeader": "Servers' Probes Set up with ServerStatus-Rabbit"
    }
}


def _atomic_write(filepath, data):
    """原子写入 JSON 文件"""
    dir_path = os.path.dirname(filepath)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_json(filepath):
    """读取并解析 JSON 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def init_data_dir():
    """首次启动初始化流程：检查并创建 data/ 目录及默认配置文件"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CERTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(CERTS_DIR, 'manual'), exist_ok=True)

    # config.json
    if not os.path.exists(CONFIG_FILE):
        _atomic_write(CONFIG_FILE, DEFAULT_CONFIG)
        logger.info("创建默认 config.json")
    else:
        # 验证文件可解析
        try:
            _read_json(CONFIG_FILE)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("config.json 损坏无法解析: %s", e)
            raise SystemExit("config.json 损坏，拒绝启动。请手动修复或删除该文件。")

    # admin.json
    if not os.path.exists(ADMIN_FILE):
        admin = DEFAULT_ADMIN.copy()
        admin['secret_key'] = os.urandom(32).hex()
        _atomic_write(ADMIN_FILE, admin)
        logger.info("创建默认 admin.json（已生成 secret_key）")
    else:
        try:
            _read_json(ADMIN_FILE)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("admin.json 损坏无法解析: %s", e)
            raise SystemExit("admin.json 损坏，拒绝启动。请手动修复或删除该文件。")

    # settings.json
    if not os.path.exists(SETTINGS_FILE):
        _atomic_write(SETTINGS_FILE, DEFAULT_SETTINGS)
        logger.info("创建默认 settings.json")
    else:
        try:
            _read_json(SETTINGS_FILE)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("settings.json 损坏无法解析: %s", e)
            raise SystemExit("settings.json 损坏，拒绝启动。请手动修复或删除该文件。")


def load_config():
    """加载 config.json"""
    return _read_json(CONFIG_FILE)


def save_config(data):
    """保存 config.json"""
    _atomic_write(CONFIG_FILE, data)
    logger.info("config.json 已保存")


def load_admin():
    """加载 admin.json"""
    return _read_json(ADMIN_FILE)


def save_admin(data):
    """保存 admin.json"""
    _atomic_write(ADMIN_FILE, data)


def load_settings():
    """加载 settings.json"""
    return _read_json(SETTINGS_FILE)


def save_settings(data):
    """保存 settings.json"""
    _atomic_write(SETTINGS_FILE, data)
    logger.info("settings.json 已保存")


def get_servers():
    """获取节点列表"""
    config = load_config()
    return config.get('servers', [])


def add_server(server_data):
    """新增节点"""
    config = load_config()
    config['servers'].append(server_data)
    save_config(config)
    logger.info("新增节点: %s", server_data.get('username', ''))


def update_server(username, updates):
    """更新节点（username 不可更改）"""
    config = load_config()
    for srv in config['servers']:
        if srv['username'] == username:
            for key, value in updates.items():
                if key != 'username':
                    srv[key] = value
            save_config(config)
            logger.info("更新节点: %s", username)
            return True
    return False


def delete_server(username):
    """删除节点"""
    config = load_config()
    original_len = len(config['servers'])
    config['servers'] = [s for s in config['servers'] if s['username'] != username]
    if len(config['servers']) < original_len:
        save_config(config)
        logger.info("删除节点: %s", username)
        return True
    return False


def find_server(username):
    """查找节点"""
    config = load_config()
    for srv in config['servers']:
        if srv['username'] == username:
            return srv
    return None


def get_secret_key():
    """获取 Flask secret_key"""
    admin = load_admin()
    return admin.get('secret_key', '')
