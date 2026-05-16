#!/usr/bin/env python3
"""
洛川 - 本地HTTP服务
启动后在浏览器中查看AI资讯聚合页面
"""

import sys
import http.server
import socketserver
from pathlib import Path

PORT = 8080
DIR = Path(__file__).parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR), **kwargs)

    def log_message(self, fmt, *args):
        print(f"  {args[0]}")


def main():
    print(f"\n{'='*50}")
    print(f"  洛川 AI 信息聚合 - 本地服务")
    print(f"  服务地址: http://localhost:{PORT}")
    print(f"  按 Ctrl+C 停止服务")
    print(f"{'='*50}\n")

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务已停止")


if __name__ == "__main__":
    main()
