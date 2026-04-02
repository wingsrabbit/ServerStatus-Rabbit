# -*- coding: utf-8 -*-
"""Flask Web 服务 - werkzeug make_server，端口 9191 + 可选 443"""

import os
import re
import shlex
import time
import threading
import logging
from datetime import timedelta
from functools import wraps

from flask import (Flask, request, session, jsonify, send_from_directory,
                   redirect, make_response)
from werkzeug.serving import make_server
from werkzeug.security import generate_password_hash, check_password_hash

from server import state, config_manager, alert, https_manager, tcp_server

logger = logging.getLogger('web_server')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, 'web', 'status')
ADMIN_DIR = os.path.join(BASE_DIR, 'web', 'admin')

app = Flask(__name__, static_folder=None)

# 全局 server 引用
_http_server = None
_https_server = None
_http_thread = None
_https_thread = None

INSTALL_BRANCH = os.environ.get('SSR_INSTALL_BRANCH', 'ServerStatus-Rabbit-NG')
INSTALL_SCRIPT_BASE = (
    'https://raw.githubusercontent.com/'
    f'wingsrabbit/ServerStatus-Rabbit/{INSTALL_BRANCH}/scripts'
)


def _curl_bootstrap(script_name, env_items):
    assignments = ' '.join(
        f'{key}={shlex.quote(str(value))}' for key, value in env_items.items()
    )
    return (
        "bash -lc 'set -e; "
        "if ! command -v curl >/dev/null 2>&1; then "
        "if command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y curl; "
        "elif command -v dnf >/dev/null 2>&1; then dnf install -y curl; "
        "elif command -v yum >/dev/null 2>&1; then yum install -y curl; "
        "else echo \"请先安装 curl\"; exit 1; fi; fi; "
        f"curl -fsSL {INSTALL_SCRIPT_BASE}/{script_name} | env {assignments} bash'"
    )


def init_app():
    """初始化 Flask app 配置"""
    admin = config_manager.load_admin()
    app.secret_key = admin.get('secret_key', os.urandom(32).hex())
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False  # HTTPS 开启后动态切换
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=86400)
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB


# ──────────────────── 辅助函数 ────────────────────

def _is_https_active():
    """检查 HTTPS 是否已激活"""
    settings = config_manager.load_settings()
    return settings.get('ports', {}).get('https_enabled', False)


def _get_https_domain():
    settings = config_manager.load_settings()
    return settings.get('https', {}).get('domain', '')


def _require_login(f):
    """要求管理员登录的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify(ok=False, message="未登录或 Session 已过期"), 401
        return f(*args, **kwargs)
    return decorated


def _require_https_for_admin(f):
    """HTTPS 开启后，管理 API 必须通过 HTTPS 访问"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if _is_https_active() and not request.is_secure:
            return jsonify(ok=False, message="此接口要求 HTTPS 访问"), 403
        return f(*args, **kwargs)
    return decorated


def _validate_username(username):
    """校验 username 格式"""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))


def _validate_password(password):
    """校验密码（不允许冒号和换行符）"""
    return ':' not in password and '\n' not in password and '\r' not in password


def _validate_region(region):
    """校验 region 格式"""
    return bool(re.match(r'^[A-Z]{2}$', region))


# ──────────────────── 公开路由 ────────────────────

@app.route('/')
def index():
    """监控展示页"""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    """监控展示页静态资源"""
    # 防止路径遍历（send_from_directory 已内置安全检查）
    if filename.startswith('admin') or filename.startswith('api'):
        return '', 404
    return send_from_directory(STATIC_DIR, filename)


@app.route('/api/stats')
def api_stats():
    """返回 stats 数据（供前端轮询），公开接口"""
    servers = config_manager.get_servers()
    stats = state.get_all_stats(servers)
    return jsonify(stats)


# ──────────────────── 后台页面路由 ────────────────────

@app.route('/admin')
@app.route('/admin/')
def admin_page():
    """后台管理页面"""
    if _is_https_active() and not request.is_secure:
        domain = _get_https_domain()
        return redirect(f"https://{domain}/admin", code=301)
    return send_from_directory(ADMIN_DIR, 'index.html')


# ──────────────────── 认证路由 ────────────────────

@app.route('/admin/setup', methods=['POST'])
def admin_setup():
    """首次设置管理员密码"""
    admin = config_manager.load_admin()
    if admin.get('initialized', False):
        return jsonify(ok=False, message="管理员密码已设置，请直接登录"), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify(ok=False, message="请求体不合法"), 400

    password = data.get('password', '')
    confirm = data.get('confirm', '')

    if not password or len(password) < 6:
        return jsonify(ok=False, message="密码不能为空且至少6位"), 400
    if password != confirm:
        return jsonify(ok=False, message="两次输入的密码不一致"), 400

    admin['password_hash'] = generate_password_hash(password)
    admin['initialized'] = True
    admin['fail_count'] = 0
    admin['locked'] = False
    config_manager.save_admin(admin)

    session.permanent = True
    session['logged_in'] = True
    logger.info("管理员密码已设置")
    return jsonify(ok=True, message="管理员密码设置成功")


@app.route('/admin/login', methods=['POST'])
def admin_login():
    """后台登录"""
    admin = config_manager.load_admin()

    if not admin.get('initialized', False):
        return jsonify(ok=False, message="请先设置管理员密码"), 400

    if admin.get('locked', False):
        return jsonify(ok=False, message="登录已锁定，请通过服务器命令行重置"), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify(ok=False, message="请求体不合法"), 400

    password = data.get('password', '')

    if check_password_hash(admin['password_hash'], password):
        admin['fail_count'] = 0
        config_manager.save_admin(admin)
        session.permanent = True
        session['logged_in'] = True
        logger.info("管理员登录成功")
        return jsonify(ok=True, message="登录成功")
    else:
        admin['fail_count'] = admin.get('fail_count', 0) + 1
        if admin['fail_count'] >= 10:
            admin['locked'] = True
            logger.warning("登录失败次数过多，已锁定")
        config_manager.save_admin(admin)
        logger.warning("管理员登录失败（第 %d 次）", admin['fail_count'])
        remaining = 10 - admin['fail_count']
        if remaining > 0:
            return jsonify(ok=False, message=f"密码错误，还剩 {remaining} 次尝试机会"), 401
        return jsonify(ok=False, message="登录已锁定，请通过服务器命令行重置"), 403


@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    """登出"""
    session.clear()
    return jsonify(ok=True, message="已登出")


@app.route('/admin/status')
def admin_status():
    """获取管理员状态（前端判断是否初始化、是否已登录）"""
    admin = config_manager.load_admin()
    return jsonify(ok=True, data={
        'initialized': admin.get('initialized', False),
        'locked': admin.get('locked', False),
        'logged_in': bool(session.get('logged_in'))
    })


# ──────────────────── 节点管理 API ────────────────────

@app.route('/api/servers', methods=['GET'])
@_require_login
@_require_https_for_admin
def get_servers():
    """获取节点列表"""
    servers = config_manager.get_servers()
    result = []
    for srv in servers:
        entry = dict(srv)
        entry['online'] = state.is_online(srv['username'])
        result.append(entry)
    return jsonify(ok=True, data=result)


@app.route('/api/servers', methods=['POST'])
@_require_login
@_require_https_for_admin
def add_server():
    """新增节点"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify(ok=False, message="请求体不合法"), 400

    # 校验必填字段
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    name = data.get('name', '').strip()
    type_ = data.get('type', '').strip()
    location = data.get('location', '').strip()
    region = data.get('region', '').strip()

    if not username:
        return jsonify(ok=False, message="用户名不能为空"), 400
    if not _validate_username(username):
        return jsonify(ok=False, message="用户名只允许字母、数字、下划线、短横线"), 400
    if config_manager.find_server(username):
        return jsonify(ok=False, message="用户名已存在"), 400
    if not password:
        return jsonify(ok=False, message="密码不能为空"), 400
    if not _validate_password(password):
        return jsonify(ok=False, message="密码不允许包含冒号或换行符"), 400
    if not name:
        return jsonify(ok=False, message="节点名称不能为空"), 400
    if not type_:
        return jsonify(ok=False, message="类型不能为空"), 400
    if not location:
        return jsonify(ok=False, message="位置不能为空"), 400
    if not region:
        return jsonify(ok=False, message="区域代码不能为空"), 400
    if not _validate_region(region):
        return jsonify(ok=False, message="区域代码必须为2位大写字母"), 400

    server_data = {
        'username': username,
        'password': password,
        'name': name,
        'type': type_,
        'host': data.get('host', '').strip(),
        'location': location,
        'region': region,
        'group': data.get('group', '').strip() if data.get('group') is not None else '',
        'disabled': bool(data.get('disabled', False))
    }

    config_manager.add_server(server_data)
    state.reload_nodes(config_manager.get_servers())

    settings = config_manager.load_settings()
    tcp_port = settings.get('ports', {}).get('tcp', 9192)
    deploy_cmd = _curl_bootstrap('install-client.sh', {
        'SSR_SERVER': '你的服务端IP',
        'SSR_PORT': tcp_port,
        'SSR_USER': username,
        'SSR_PASS': password,
    })

    return jsonify(ok=True, message="节点已创建", data={
        'username': username,
        'deploy_command': deploy_cmd
    })


@app.route('/api/servers/<username>', methods=['PUT'])
@_require_login
@_require_https_for_admin
def update_server(username):
    """修改节点（username 不可更改）"""
    if not config_manager.find_server(username):
        return jsonify(ok=False, message="节点不存在"), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify(ok=False, message="请求体不合法"), 400

    updates = {}
    if 'password' in data:
        password = data['password'].strip()
        if not password:
            return jsonify(ok=False, message="密码不能为空"), 400
        if not _validate_password(password):
            return jsonify(ok=False, message="密码不允许包含冒号或换行符"), 400
        updates['password'] = password

    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify(ok=False, message="节点名称不能为空"), 400
        updates['name'] = name

    if 'type' in data:
        type_ = data['type'].strip()
        if not type_:
            return jsonify(ok=False, message="类型不能为空"), 400
        updates['type'] = type_

    if 'location' in data:
        location = data['location'].strip()
        if not location:
            return jsonify(ok=False, message="位置不能为空"), 400
        updates['location'] = location

    if 'region' in data:
        region = data['region'].strip()
        if not region:
            return jsonify(ok=False, message="区域代码不能为空"), 400
        if not _validate_region(region):
            return jsonify(ok=False, message="区域代码必须为2位大写字母"), 400
        updates['region'] = region

    if 'host' in data:
        updates['host'] = data['host'].strip() if data['host'] else ''

    if 'group' in data:
        updates['group'] = data['group'].strip() if data['group'] is not None else ''

    if 'disabled' in data:
        was_disabled = config_manager.find_server(username).get('disabled', False)
        updates['disabled'] = bool(data['disabled'])
        # 如果节点被禁用，断开其 TCP 连接
        if updates['disabled'] and not was_disabled:
            tcp_server.disconnect_user(username)
            state.set_offline(username)

    config_manager.update_server(username, updates)
    state.reload_nodes(config_manager.get_servers())

    return jsonify(ok=True, message="节点已更新")


@app.route('/api/servers/<username>', methods=['DELETE'])
@_require_login
@_require_https_for_admin
def delete_server(username):
    """删除节点"""
    if not config_manager.find_server(username):
        return jsonify(ok=False, message="节点不存在"), 404

    # 断开 TCP 连接并清理状态
    tcp_server.disconnect_user(username)
    state.set_offline(username)
    config_manager.delete_server(username)
    state.reload_nodes(config_manager.get_servers())

    return jsonify(ok=True, message="节点已删除")


# ──────────────────── 系统设置 API ────────────────────

@app.route('/api/dns-check')
@_require_login
def dns_check():
    """检测域名 DNS 解析结果"""
    import socket as _socket
    domain = request.args.get('domain', '').strip()
    if not domain:
        return jsonify(ok=False, message="域名不能为空")
    try:
        ip = _socket.gethostbyname(domain)
        return jsonify(ok=True, ip=ip)
    except _socket.gaierror:
        return jsonify(ok=True, ip="无指向")


@app.route('/api/settings/https', methods=['POST'])
@_require_login
@_require_https_for_admin
def settings_https():
    """开启/关闭 HTTPS"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify(ok=False, message="请求体不合法"), 400

    enabled = data.get('enabled', False)
    settings = config_manager.load_settings()
    backup_settings = dict(settings)  # 回退快照

    if not enabled:
        # 关闭 HTTPS
        settings['https']['enabled'] = False
        settings['ports']['https_enabled'] = False
        config_manager.save_settings(settings)
        _stop_https_server()
        app.config['SESSION_COOKIE_SECURE'] = False
        return jsonify(ok=True, message="HTTPS 已关闭")

    mode = data.get('mode', 'letsencrypt')
    domain = data.get('domain', '').strip()
    email = data.get('email', '').strip()

    if mode == 'letsencrypt':
        if not domain:
            return jsonify(ok=False, message="域名不能为空"), 400
        if not email:
            return jsonify(ok=False, message="邮箱不能为空"), 400

        success, cert_path, key_path, cert_error = https_manager.request_letsencrypt_cert(domain, email)
        if not success:
            return jsonify(ok=False, message=f"certbot 申请失败：{cert_error}"), 500

        settings['https'] = {
            'enabled': True,
            'mode': 'letsencrypt',
            'domain': domain,
            'email': email,
            'cert_path': cert_path,
            'key_path': key_path
        }
    elif mode == 'manual':
        cert_path = settings['https'].get('cert_path', '')
        key_path = settings['https'].get('key_path', '')
        if not cert_path or not key_path or not os.path.exists(cert_path) or not os.path.exists(key_path):
            return jsonify(ok=False, message="请先上传证书和私钥文件"), 400
        if not https_manager.validate_cert_key_pair(cert_path, key_path):
            return jsonify(ok=False, message="证书与私钥不匹配"), 400
        settings['https']['enabled'] = True
        settings['https']['mode'] = 'manual'
        settings['https']['domain'] = domain
    else:
        return jsonify(ok=False, message="不支持的证书模式"), 400

    # 尝试启动 HTTPS
    try:
        cert_p, key_p = https_manager.get_cert_paths(settings)
        _start_https_server(cert_p, key_p)
        settings['ports']['https_enabled'] = True
        config_manager.save_settings(settings)
        app.config['SESSION_COOKIE_SECURE'] = True
        return jsonify(ok=True, message="HTTPS 已开启，443 端口已启动")
    except Exception as e:
        # 回退
        config_manager.save_settings(backup_settings)
        logger.error("HTTPS 启动失败，已回退: %s", e)
        return jsonify(ok=False, message=f"HTTPS 启动失败: {e}"), 500


@app.route('/api/settings/port9191', methods=['POST'])
@_require_login
@_require_https_for_admin
def settings_port9191():
    """开启/关闭 9191 端口"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify(ok=False, message="请求体不合法"), 400

    enabled = data.get('enabled', True)
    settings = config_manager.load_settings()

    if not enabled:
        if not settings.get('ports', {}).get('https_enabled', False):
            return jsonify(ok=False, message="HTTPS 未开启，不能关闭 9191 端口"), 400
        settings['ports']['web_enabled'] = False
        config_manager.save_settings(settings)
        _stop_http_server()
        return jsonify(ok=True, message="9191 端口已关闭")
    else:
        settings['ports']['web_enabled'] = True
        config_manager.save_settings(settings)
        _start_http_server()
        return jsonify(ok=True, message="9191 端口已开启")


@app.route('/api/settings/ui', methods=['GET'])
def get_ui_settings():
    """获取 UI 配置（公开接口，前端需要读取标题）"""
    settings = config_manager.load_settings()
    return jsonify(ok=True, data=settings.get('ui', {}))


@app.route('/api/settings/ui', methods=['POST'])
@_require_login
@_require_https_for_admin
def set_ui_settings():
    """设置 UI 配置"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify(ok=False, message="请求体不合法"), 400

    settings = config_manager.load_settings()
    ui = settings.get('ui', {})
    if 'header' in data:
        ui['header'] = str(data['header']).strip()[:100]
    if 'subHeader' in data:
        ui['subHeader'] = str(data['subHeader']).strip()[:200]
    settings['ui'] = ui
    config_manager.save_settings(settings)
    return jsonify(ok=True, message="页面设置已保存")


@app.route('/api/settings/webhook', methods=['GET'])
@_require_login
@_require_https_for_admin
def get_webhook():
    """获取 Webhook 配置"""
    settings = config_manager.load_settings()
    return jsonify(ok=True, data=settings.get('webhook', {}))


@app.route('/api/settings/webhook', methods=['POST'])
@_require_login
@_require_https_for_admin
def set_webhook():
    """设置 Webhook"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify(ok=False, message="请求体不合法"), 400

    settings = config_manager.load_settings()
    settings['webhook'] = {
        'enabled': bool(data.get('enabled', False)),
        'url': data.get('url', '').strip(),
        'timeout_seconds': max(10, min(300, int(data.get('timeout_seconds', 30))))
    }
    config_manager.save_settings(settings)
    return jsonify(ok=True, message="Webhook 设置已保存")


@app.route('/api/settings/webhook/test', methods=['POST'])
@_require_login
@_require_https_for_admin
def test_webhook():
    """测试 Webhook"""
    data = request.get_json(silent=True)
    url = ''
    if data:
        url = data.get('url', '').strip()
    if not url:
        settings = config_manager.load_settings()
        url = settings.get('webhook', {}).get('url', '')
    if not url:
        return jsonify(ok=False, message="Webhook URL 未设置"), 400

    success, msg = alert.send_test_webhook(url)
    if success:
        return jsonify(ok=True, message=msg)
    return jsonify(ok=False, message=msg), 400


@app.route('/api/settings/cert-upload', methods=['POST'])
@_require_login
def cert_upload():
    """手动上传证书"""
    if 'cert' not in request.files or 'key' not in request.files:
        return jsonify(ok=False, message="必须同时上传证书文件(cert)和私钥文件(key)"), 400

    cert_file = request.files['cert']
    key_file = request.files['key']

    # 检查文件名后缀
    allowed_ext = {'.pem', '.crt', '.key'}
    cert_ext = os.path.splitext(cert_file.filename)[1].lower() if cert_file.filename else ''
    key_ext = os.path.splitext(key_file.filename)[1].lower() if key_file.filename else ''

    if cert_ext not in allowed_ext:
        return jsonify(ok=False, message="证书文件后缀不合法，允许 .pem/.crt/.key"), 400
    if key_ext not in allowed_ext:
        return jsonify(ok=False, message="私钥文件后缀不合法，允许 .pem/.crt/.key"), 400

    # 检查文件大小 (1MB)
    cert_data = cert_file.read()
    key_data = key_file.read()
    if len(cert_data) > 1024 * 1024:
        return jsonify(ok=False, message="证书文件超过 1MB 限制"), 400
    if len(key_data) > 1024 * 1024:
        return jsonify(ok=False, message="私钥文件超过 1MB 限制"), 400

    # 保存到临时位置验证
    manual_dir = os.path.join(config_manager.CERTS_DIR, 'manual')
    os.makedirs(manual_dir, exist_ok=True)

    cert_path = os.path.join(manual_dir, 'fullchain.pem')
    key_path = os.path.join(manual_dir, 'privkey.pem')

    with open(cert_path, 'wb') as f:
        f.write(cert_data)
    with open(key_path, 'wb') as f:
        f.write(key_data)

    # 验证证书和私钥匹配
    if not https_manager.validate_cert_key_pair(cert_path, key_path):
        os.unlink(cert_path)
        os.unlink(key_path)
        return jsonify(ok=False, message="证书与私钥不匹配"), 400

    # 更新 settings
    settings = config_manager.load_settings()
    settings['https']['mode'] = 'manual'
    settings['https']['cert_path'] = cert_path
    settings['https']['key_path'] = key_path
    config_manager.save_settings(settings)

    return jsonify(ok=True, message="证书已上传并验证通过")


# ──────────────────── HTTP/HTTPS Server 管理 ────────────────────

def _start_http_server(port=9191):
    """启动 HTTP 服务器"""
    global _http_server, _http_thread
    if _http_server:
        return
    _http_server = make_server('0.0.0.0', port, app, threaded=True)
    _http_thread = threading.Thread(target=_http_server.serve_forever, daemon=True)
    _http_thread.start()
    logger.info("HTTP 服务器启动，端口 %d", port)


def _stop_http_server():
    """停止 HTTP 服务器"""
    global _http_server, _http_thread
    if _http_server:
        _http_server.shutdown()
        _http_server = None
        _http_thread = None
        logger.info("HTTP 服务器已停止")


def _start_https_server(cert_path, key_path, port=443):
    """启动 HTTPS 服务器"""
    global _https_server, _https_thread
    _stop_https_server()  # 先停止旧的
    ssl_ctx = https_manager.create_ssl_context(cert_path, key_path)
    _https_server = make_server('0.0.0.0', port, app, threaded=True, ssl_context=ssl_ctx)
    _https_thread = threading.Thread(target=_https_server.serve_forever, daemon=True)
    _https_thread.start()
    logger.info("HTTPS 服务器启动，端口 %d", port)


def _stop_https_server():
    """停止 HTTPS 服务器"""
    global _https_server, _https_thread
    if _https_server:
        _https_server.shutdown()
        _https_server = None
        _https_thread = None
        logger.info("HTTPS 服务器已停止")


def restart_https():
    """重新加载 HTTPS（证书续期后调用）"""
    settings = config_manager.load_settings()
    if settings.get('ports', {}).get('https_enabled', False):
        cert_path, key_path = https_manager.get_cert_paths(settings)
        if os.path.exists(cert_path) and os.path.exists(key_path):
            _start_https_server(cert_path, key_path)


def start(settings):
    """根据 settings 启动 Web 服务"""
    init_app()

    ports = settings.get('ports', {})

    # 启动 HTTP
    if ports.get('web_enabled', True):
        _start_http_server(ports.get('web', 9191))

    # 启动 HTTPS
    if ports.get('https_enabled', False):
        try:
            cert_path, key_path = https_manager.get_cert_paths(settings)
            if os.path.exists(cert_path) and os.path.exists(key_path):
                _start_https_server(cert_path, key_path, ports.get('https', 443))
                app.config['SESSION_COOKIE_SECURE'] = True
        except Exception as e:
            logger.error("HTTPS 启动失败: %s", e)
