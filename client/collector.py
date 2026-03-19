# -*- coding: utf-8 -*-
"""客户端数据采集模块 - psutil 采集宿主机数据"""

import os
import time
import socket
import logging
from collections import deque

# 必须在 import psutil 之前设置环境变量
if os.path.exists('/host/proc'):
    os.environ['PSUTIL_LINUX_PROCFS_PATH'] = '/host/proc'
if os.path.exists('/host/sys'):
    os.environ['PSUTIL_LINUX_SYSFS_PATH'] = '/host/sys'

import psutil

logger = logging.getLogger('collector')

INTERVAL = 1  # 采集间隔（秒）
ROOTFS_PATH = '/host/rootfs' if os.path.exists('/host/rootfs') else '/'


def check_interface(net_name):
    """过滤虚拟网卡"""
    net_name = net_name.strip()
    invalid_name = ['lo', 'tun', 'kube', 'docker', 'vmbr', 'br-', 'vnet', 'veth']
    return not any(name in net_name for name in invalid_name)


def get_uptime():
    """获取运行时长（秒）"""
    return int(time.time() - psutil.boot_time())


def get_memory():
    """获取内存信息（KB）"""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return (
        int(mem.total / 1024.0),
        int(mem.used / 1024.0),
        int(swap.total / 1024.0),
        int(swap.used / 1024.0)
    )


def get_hdd():
    """获取磁盘信息（MB）"""
    valid_fs = [
        'ext4', 'ext3', 'ext2', 'reiserfs', 'jfs', 'btrfs',
        'fuseblk', 'zfs', 'simfs', 'ntfs', 'fat32', 'exfat', 'xfs'
    ]
    disks = dict()
    size = 0
    used = 0
    for disk in psutil.disk_partitions():
        if disk.device not in disks and disk.fstype.lower() in valid_fs:
            disks[disk.device] = disk.mountpoint
    for disk in disks.values():
        try:
            usage = psutil.disk_usage(disk)
            size += usage.total
            used += usage.used
        except Exception:
            pass

    # 如果通过挂载方式采集，优先使用 rootfs 路径
    if ROOTFS_PATH != '/':
        try:
            usage = psutil.disk_usage(ROOTFS_PATH)
            return int(usage.total / 1024.0 / 1024.0), int(usage.used / 1024.0 / 1024.0)
        except Exception:
            pass

    return int(size / 1024.0 / 1024.0), int(used / 1024.0 / 1024.0)


def get_load():
    """获取系统负载"""
    try:
        return round(psutil.getloadavg()[0], 1)
    except Exception:
        return -1.0


def get_cpu():
    """获取 CPU 使用率"""
    return psutil.cpu_percent(interval=INTERVAL)


class Network:
    """网络流量采集"""
    def __init__(self):
        self.rx = deque(maxlen=10)
        self.tx = deque(maxlen=10)
        self._get_traffic()

    def _get_traffic(self):
        net_in = 0
        net_out = 0
        net = psutil.net_io_counters(pernic=True)
        for k, v in net.items():
            if check_interface(k):
                net_in += v[1]  # bytes_recv
                net_out += v[0]  # bytes_sent
        self.rx.append(net_in)
        self.tx.append(net_out)

    def get_speed(self):
        """获取网络速率"""
        self._get_traffic()
        avg_rx = 0
        avg_tx = 0
        queue_len = len(self.rx)
        for x in range(queue_len - 1):
            avg_rx += self.rx[x + 1] - self.rx[x]
            avg_tx += self.tx[x + 1] - self.tx[x]
        if queue_len > 1:
            avg_rx = int(avg_rx / (queue_len - 1) / INTERVAL)
            avg_tx = int(avg_tx / (queue_len - 1) / INTERVAL)
        return avg_rx, avg_tx

    def get_traffic(self):
        """获取累计流量"""
        queue_len = len(self.rx)
        return self.rx[queue_len - 1], self.tx[queue_len - 1]


def get_network(ip_version):
    """检测 IPv4/IPv6 连通性"""
    if ip_version == 4:
        host = 'ipv4.google.com'
    elif ip_version == 6:
        host = 'ipv6.google.com'
    else:
        return False
    try:
        socket.create_connection((host, 80), 2).close()
        return True
    except Exception:
        return False


def collect_all(traffic, check_ip, timer):
    """采集所有系统数据，返回 (data_dict, new_timer)"""
    cpu = get_cpu()
    net_rx, net_tx = traffic.get_speed()
    net_in, net_out = traffic.get_traffic()
    uptime = get_uptime()
    load = get_load()
    mem_total, mem_used, swap_total, swap_used = get_memory()
    hdd_total, hdd_used = get_hdd()

    data = {
        'uptime': uptime,
        'load': load,
        'memory_total': mem_total,
        'memory_used': mem_used,
        'swap_total': swap_total,
        'swap_used': swap_used,
        'hdd_total': hdd_total,
        'hdd_used': hdd_used,
        'cpu': cpu,
        'network_rx': net_rx,
        'network_tx': net_tx,
        'network_in': net_in,
        'network_out': net_out,
    }

    # 定期检测 IP 连通性
    if timer <= 0:
        key = f'online{check_ip}'
        data[key] = get_network(check_ip)
        timer = 150
    else:
        timer -= INTERVAL

    return data, timer
