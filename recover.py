# -*- coding: utf-8 -*-
"""紧急恢复脚本 - 重置 settings.json / 重置管理员密码"""

import os
import sys
import json
import string
import secrets
import argparse
import tempfile

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
ADMIN_FILE = os.path.join(DATA_DIR, 'admin.json')


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


def reset_settings():
    """重置 settings.json：开放 9191 端口，关闭 HTTPS"""
    try:
        if not os.path.exists(SETTINGS_FILE):
            print("FAILED - settings.json 不存在")
            return False

        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        settings['ports']['web_enabled'] = True
        settings['ports']['https_enabled'] = False

        _atomic_write(SETTINGS_FILE, settings)
        print("SUCCESS - 设置已重置，请执行 docker restart <容器名> 使设置生效")
        return True
    except Exception as e:
        print(f"FAILED - {e}")
        return False


def reset_password():
    """重置管理员密码：解除锁定 + 生成新随机密码"""
    try:
        # 延迟导入（容器环境中才有 werkzeug）
        from werkzeug.security import generate_password_hash

        if not os.path.exists(ADMIN_FILE):
            print("FAILED - admin.json 不存在")
            return False

        with open(ADMIN_FILE, 'r', encoding='utf-8') as f:
            admin = json.load(f)

        # 生成 12 位随机密码
        alphabet = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for _ in range(12))

        admin['password_hash'] = generate_password_hash(new_password)
        admin['locked'] = False
        admin['fail_count'] = 0
        admin['initialized'] = True

        _atomic_write(ADMIN_FILE, admin)
        print(f"SUCCESS - 管理员密码已重置")
        print(f"新密码: {new_password}")
        print("请使用新密码登录后台，登录后可在后台修改为自己想要的密码")
        return True
    except Exception as e:
        print(f"FAILED - {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='ServerStatus-Rabbit 恢复工具')
    parser.add_argument('--reset-password', action='store_true', help='重置管理员密码并解除锁定')
    args = parser.parse_args()

    if args.reset_password:
        reset_password()
    else:
        reset_settings()


if __name__ == '__main__':
    main()
