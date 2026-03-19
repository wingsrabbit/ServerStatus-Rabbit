# -*- coding: utf-8 -*-
"""ServerStatus-Rabbit 入口 - 根据命令行参数启动对应模块"""

import sys
import os
import signal
import logging
import threading
import argparse

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('app')

# 禁止 werkzeug 默认的请求日志刷屏
logging.getLogger('werkzeug').setLevel(logging.WARNING)


def run_server():
    """启动服务端模式"""
    from server import config_manager, state, tcp_server, web_server, alert, https_manager

    logger.info("启动服务端模式")

    # 初始化数据目录和配置文件
    config_manager.init_data_dir()

    # 加载配置
    config = config_manager.load_config()
    settings = config_manager.load_settings()

    # 初始化节点状态
    state.init_nodes(config.get('servers', []))

    # 启动 TCP 服务器线程
    tcp_port = settings.get('ports', {}).get('tcp', 9192)
    tcp_thread = threading.Thread(target=tcp_server.start, args=(tcp_port,), daemon=True)
    tcp_thread.start()
    logger.info("TCP 服务器线程已启动")

    # 启动 Web 服务
    web_server.start(settings)
    logger.info("Web 服务已启动")

    # 启动掉线检测线程
    alert.start_checker()

    # 如果 HTTPS 已启用，启动证书续期检查线程
    if settings.get('ports', {}).get('https_enabled', False):
        https_manager.start_renewal_checker(web_server.restart_https)

    logger.info("ServerStatus-Rabbit 服务端已就绪")

    # 主线程等待信号
    stop_event = threading.Event()

    def signal_handler(signum, frame):
        logger.info("收到退出信号 %s，正在关闭...", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    stop_event.wait()
    logger.info("ServerStatus-Rabbit 已关闭")


def run_client(args):
    """启动客户端模式"""
    from client import reporter

    logger.info("启动客户端模式")
    reporter.start(
        server=args.server,
        port=args.port,
        user=args.user,
        password=args.password  # 使用 password 而非 pass（Python 保留字）
    )


def main():
    parser = argparse.ArgumentParser(description='ServerStatus-Rabbit')
    subparsers = parser.add_subparsers(dest='role')

    # 客户端子命令
    client_parser = subparsers.add_parser('client', help='以客户端模式启动')
    client_parser.add_argument('--server', required=True, help='服务端 IP 地址')
    client_parser.add_argument('--port', type=int, default=9192, help='服务端 TCP 端口')
    client_parser.add_argument('--user', required=True, help='认证用户名')
    client_parser.add_argument('--pass', dest='password', required=True, help='认证密码')

    args = parser.parse_args()

    if args.role == 'client':
        run_client(args)
    else:
        run_server()


if __name__ == '__main__':
    main()
