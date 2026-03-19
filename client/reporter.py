# -*- coding: utf-8 -*-
"""客户端 TCP 上报模块 - 连接、认证、发送数据、断线重连"""

import socket
import json
import time
import logging

from client import collector

logger = logging.getLogger('reporter')

RECONNECT_INTERVAL = 5  # 重连间隔（秒）


def start(server, port, user, password):
    """启动客户端上报循环"""
    socket.setdefaulttimeout(30)
    report_count = 0

    while True:
        s = None
        try:
            print(f"[ServerStatus-Rabbit] 正在连接 {server}:{port} ...")
            s = socket.create_connection((server, port))

            # 步骤 1: 接收认证提示
            data = s.recv(1024).decode('utf-8')
            if 'Authentication required' not in data:
                print(f"[ServerStatus-Rabbit] 未收到认证提示: {data}")
                raise socket.error("未收到认证提示")

            # 步骤 2: 发送认证信息
            s.send(f"{user}:{password}\n".encode('utf-8'))

            # 步骤 3: 接收认证结果
            data = s.recv(1024).decode('utf-8')
            if 'Authentication successful' not in data:
                print(f"[ServerStatus-Rabbit] 认证失败: {data}")
                raise socket.error("认证失败")

            print(f"[ServerStatus-Rabbit] 认证成功，开始上报数据")

            # 步骤 4: 接收连接方式提示
            if 'You are connecting via' not in data:
                data = s.recv(1024).decode('utf-8')

            # 判断需要探测的 IP 版本
            check_ip = 0
            if 'IPv4' in data:
                check_ip = 6  # 通过 IPv4 连接，探测 IPv6
            elif 'IPv6' in data:
                check_ip = 4  # 通过 IPv6 连接，探测 IPv4

            # 步骤 5: 数据采集和上报循环
            traffic = collector.Network()
            timer = 0

            while True:
                collect_data, timer = collector.collect_all(traffic, check_ip, timer)
                payload = "update " + json.dumps(collect_data) + "\n"
                s.send(payload.encode('utf-8'))
                report_count += 1
                print(f"[ServerStatus-Rabbit] 上报 #{report_count} 成功")

        except KeyboardInterrupt:
            print("[ServerStatus-Rabbit] 收到退出信号")
            break
        except socket.error as e:
            print(f"[ServerStatus-Rabbit] 连接断开，{RECONNECT_INTERVAL}秒后重连...")
            logger.warning("连接断开: %s", e)
        except Exception as e:
            print(f"[ServerStatus-Rabbit] 异常: {e}")
            logger.error("客户端异常: %s", e)
        finally:
            if s:
                try:
                    s.close()
                except Exception:
                    pass

        time.sleep(RECONNECT_INTERVAL)
