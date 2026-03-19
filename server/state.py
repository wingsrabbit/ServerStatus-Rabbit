# -*- coding: utf-8 -*-
"""状态管理模块 - 全局节点状态字典 + Lock 封装"""

import time
import threading
import logging

logger = logging.getLogger('state')

_lock = threading.Lock()
_nodes = {}  # {username: {last_seen, online, alert_sent, connected_since, data}}
_newly_online_queue = []  # 新上线节点队列，由 update_node 写入，check_and_alert 消费


def init_nodes(config_servers):
    """根据 config.json 的 servers 列表初始化所有节点状态（全部离线）"""
    with _lock:
        _nodes.clear()
        for srv in config_servers:
            username = srv.get('username', '')
            _nodes[username] = _make_default_node()
        logger.info("初始化 %d 个节点状态", len(config_servers))


def _make_default_node():
    return {
        'last_seen': 0,
        'online': False,
        'alert_sent': False,
        'connected_since': 0,
        'data': {
            'uptime': '0',
            'load': 0.0,
            'memory_total': 0,
            'memory_used': 0,
            'swap_total': 0,
            'swap_used': 0,
            'hdd_total': 0,
            'hdd_used': 0,
            'cpu': 0.0,
            'cpu_cores': 1,
            'network_rx': 0,
            'network_tx': 0,
            'network_in': 0,
            'network_out': 0,
            'online4': False,
            'online6': False,
        }
    }


def update_node(username, data):
    """更新指定节点的实时数据，同时更新 last_seen 时间戳"""
    with _lock:
        if username not in _nodes:
            _nodes[username] = _make_default_node()
        node = _nodes[username]
        node['last_seen'] = time.time()
        if not node['online']:
            node['connected_since'] = time.time()
            _newly_online_queue.append(username)
        node['online'] = True
        # 合并上报的数据字段
        for key in data:
            if key in node['data']:
                node['data'][key] = data[key]


def get_all_stats(config_servers):
    """返回完整的 stats JSON 结构（合并配置信息 + 实时状态 + online 标记）"""
    servers = []
    with _lock:
        for srv in config_servers:
            username = srv.get('username', '')
            node = _nodes.get(username, _make_default_node())
            entry = {
                'name': srv.get('name', ''),
                'type': srv.get('type', ''),
                'host': srv.get('host', ''),
                'location': srv.get('location', ''),
                'region': srv.get('region', ''),
                'group': srv.get('group', ''),
                'disabled': srv.get('disabled', False),
                'online': node['online'] if not srv.get('disabled', False) else False,
                'online4': node['data'].get('online4', False) if node['online'] else False,
                'online6': node['data'].get('online6', False) if node['online'] else False,
                'uptime': str(int(node['last_seen'] - node['connected_since'])) if node['online'] and node.get('connected_since', 0) > 0 and node['last_seen'] > node['connected_since'] else '0',
                'load': node['data'].get('load', 0.0),
                'cpu': node['data'].get('cpu', 0.0),
                'cpu_cores': node['data'].get('cpu_cores', 1),
                'network_rx': node['data'].get('network_rx', 0),
                'network_tx': node['data'].get('network_tx', 0),
                'network_in': node['data'].get('network_in', 0),
                'network_out': node['data'].get('network_out', 0),
                'memory_total': node['data'].get('memory_total', 0),
                'memory_used': node['data'].get('memory_used', 0),
                'swap_total': node['data'].get('swap_total', 0),
                'swap_used': node['data'].get('swap_used', 0),
                'hdd_total': node['data'].get('hdd_total', 0),
                'hdd_used': node['data'].get('hdd_used', 0),
                'custom': '',
            }
            servers.append(entry)
    return {
        'servers': servers,
        'updated': int(time.time())
    }


def check_offline(timeout_seconds):
    """扫描所有节点，返回新增掉线的节点列表"""
    now = time.time()
    newly_offline = []
    with _lock:
        for username, node in _nodes.items():
            if node['last_seen'] == 0:
                # 从未上报过，跳过
                continue
            if now - node['last_seen'] > timeout_seconds:
                if node['online']:
                    node['online'] = False
                    node['connected_since'] = 0
                    newly_offline.append(username)
    return newly_offline


def pop_newly_online():
    """取出并清空新上线节点列表（由 update_node 写入）"""
    with _lock:
        result = list(_newly_online_queue)
        _newly_online_queue.clear()
        return result


def mark_alert_sent(username):
    """标记某节点已发送掉线告警"""
    with _lock:
        if username in _nodes:
            _nodes[username]['alert_sent'] = True


def clear_alert(username):
    """节点恢复上线时清除告警标记"""
    with _lock:
        if username in _nodes:
            _nodes[username]['alert_sent'] = False


def is_alert_sent(username):
    """检查某节点是否已发送告警"""
    with _lock:
        if username in _nodes:
            return _nodes[username]['alert_sent']
        return False


def reload_nodes(config_servers):
    """配置热加载时调用，新增节点初始化、删除节点清理状态、已有节点保留实时数据不丢"""
    new_usernames = {srv.get('username', '') for srv in config_servers}
    with _lock:
        # 删除不再存在的节点
        to_delete = [u for u in _nodes if u not in new_usernames]
        for u in to_delete:
            del _nodes[u]
            logger.info("清理已删除节点状态: %s", u)
        # 新增节点初始化
        for srv in config_servers:
            username = srv.get('username', '')
            if username not in _nodes:
                _nodes[username] = _make_default_node()
                logger.info("初始化新节点状态: %s", username)


def is_online(username):
    """返回指定节点是否在线"""
    with _lock:
        if username in _nodes:
            return _nodes[username]['online']
        return False


def set_offline(username):
    """将指定节点设置为离线（用于禁用节点时断开连接后更新状态）"""
    with _lock:
        if username in _nodes:
            _nodes[username]['online'] = False
            _nodes[username]['connected_since'] = 0


def get_connected_usernames():
    """返回当前在线的用户名集合"""
    with _lock:
        return {u for u, n in _nodes.items() if n['online']}
