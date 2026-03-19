# -*- coding: utf-8 -*-
"""TCP 数据接收器 - 替代 C++ sergate，实现完整 TCP 协议"""

import socket
import json
import time
import threading
import logging

from server import state, config_manager

logger = logging.getLogger('tcp_server')

# 当前已连接的用户名 -> 连接线程引用（用于检测重复连接和禁用时断开）
_connected_clients = {}  # {username: threading.Event (stop_event)}
_clients_lock = threading.Lock()


def start(port=9192):
    """启动 TCP 服务器，在独立线程中运行"""
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 允许同时接受 IPv4 和 IPv6 连接
    server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    server_socket.bind(('::', port))
    server_socket.listen(50)
    server_socket.settimeout(1.0)  # 使 accept 可以被中断
    logger.info("TCP 服务器启动，监听端口 %d", port)

    while True:
        try:
            conn, addr = server_socket.accept()
            t = threading.Thread(target=_handle_client, args=(conn, addr), daemon=True)
            t.start()
        except socket.timeout:
            continue
        except Exception as e:
            logger.error("TCP accept 异常: %s", e)
            continue


def _detect_ip_version(addr):
    """检测客户端连接的 IP 版本"""
    ip = addr[0]
    if ip.startswith('::ffff:'):
        return 'IPv4'
    if ':' in ip:
        return 'IPv6'
    return 'IPv4'


def _handle_client(conn, addr):
    """处理单个客户端连接"""
    ip_version = _detect_ip_version(addr)
    client_ip = addr[0]
    logger.info("新连接: %s (%s)", client_ip, ip_version)
    conn.settimeout(5.0)  # 认证阶段 5 秒超时

    username = None
    stop_event = threading.Event()

    try:
        # 步骤 1: 发送认证提示
        conn.sendall(b"Authentication required:")

        # 步骤 2: 接收用户名和密码
        try:
            auth_data = conn.recv(1024).decode('utf-8').strip()
        except socket.timeout:
            logger.warning("认证超时: %s", client_ip)
            return

        if ':' not in auth_data:
            logger.warning("认证格式错误: %s", client_ip)
            return

        username, password = auth_data.split(':', 1)

        # 步骤 3: 验证凭据
        servers = config_manager.get_servers()
        server_entry = None
        for srv in servers:
            if srv.get('username') == username:
                server_entry = srv
                break

        if server_entry is None:
            logger.warning("认证失败 - 用户不存在: %s from %s", username, client_ip)
            conn.close()
            return

        if server_entry.get('password') != password:
            logger.warning("认证失败 - 密码错误: %s from %s", username, client_ip)
            conn.close()
            return

        # 检查节点是否被禁用
        if server_entry.get('disabled', False):
            logger.warning("认证拒绝 - 节点已禁用: %s", username)
            conn.close()
            return

        # 检查重复连接
        with _clients_lock:
            if username in _connected_clients:
                logger.warning("拒绝重复连接: %s from %s", username, client_ip)
                try:
                    conn.sendall(b"Only one connection per user allowed.")
                except Exception:
                    pass
                conn.close()
                return
            _connected_clients[username] = stop_event

        # 步骤 4: 认证成功
        conn.sendall(b"Authentication successful. Access granted.")
        logger.info("认证成功: %s from %s", username, client_ip)

        # 步骤 5: 发送连接方式提示
        conn.sendall(f"You are connecting via: {ip_version}".encode('utf-8'))

        # 步骤 6: 进入数据接收循环
        conn.settimeout(60.0)  # 数据阶段超时
        buffer = ''

        while not stop_event.is_set():
            try:
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    break

                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if line.startswith('update '):
                        json_str = line[7:]
                        try:
                            update_data = json.loads(json_str)
                            # 确保 uptime 是字符串
                            if 'uptime' in update_data:
                                update_data['uptime'] = str(update_data['uptime'])
                            state.update_node(username, update_data)
                        except json.JSONDecodeError:
                            logger.warning("JSON 解析失败: %s from %s", json_str[:100], username)
            except socket.timeout:
                # 检查节点是否被禁用（热加载）
                srv = config_manager.find_server(username)
                if srv and srv.get('disabled', False):
                    logger.info("节点已禁用，断开连接: %s", username)
                    break
                continue
            except Exception as e:
                logger.info("连接异常: %s - %s", username, e)
                break

    except Exception as e:
        logger.error("处理客户端异常: %s - %s", client_ip, e)
    finally:
        # 清理
        if username:
            with _clients_lock:
                _connected_clients.pop(username, None)
            state.set_offline(username)
            logger.info("客户端断开: %s", username)
        try:
            conn.close()
        except Exception:
            pass


def disconnect_user(username):
    """强制断开指定用户的连接（用于禁用节点时）"""
    with _clients_lock:
        stop_event = _connected_clients.get(username)
        if stop_event:
            stop_event.set()
            logger.info("已发送断开信号: %s", username)


def is_user_connected(username):
    """检查用户是否已连接"""
    with _clients_lock:
        return username in _connected_clients
