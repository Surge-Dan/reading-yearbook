"""Deliver the packaged design as a report or standalone book, without model calls.

Preview serves exactly one HTML file on loopback; it never exposes its directory.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from html_contract import atomic_text
from report_reader import load_distillations, reader_page, validated_distillations


def read_report(path):
    page = Path(path).read_text('utf-8-sig')
    match = re.search(r'<script\b(?=[^>]*\bid=["\']reading-data["\'])[^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ValueError('该文件不是年年阅报告；请选择本次用户的报告HTML。')
    data = json.loads(match[1])
    if not isinstance(data, dict) or not isinstance(data.get('books'), list) or not isinstance(data.get('summary'), dict):
        raise ValueError('报告数据不完整，已保留原文件。')
    return data


def merge_books(existing, incoming, source_mode='real'):
    results = copy.deepcopy(validated_distillations(existing, source_mode))
    validated_distillations(incoming, source_mode)
    def identity(bundle):
        book = bundle['analysis']['book']
        return tuple(str(book.get(key, '')).strip().casefold() for key in ('title', 'author', 'edition'))
    for bundle in incoming:
        index = next((i for i, old in enumerate(results) if identity(old) == identity(bundle)), None)
        if index is None:
            results.append(copy.deepcopy(bundle))
        else:
            results[index] = copy.deepcopy(bundle)
    return results


def deliver(output, report=None, packages=None):
    output = Path(output).resolve()
    if output.suffix.lower() not in ('.html', '.htm'):
        raise ValueError('交付文件必须是HTML，不能覆盖数据包或电子书。')
    packages = packages or []
    if report:
        from build_reading_html import build_html
        data = read_report(report)
        from reading_portrait import analysis_state
        if (data.get('portrait_analysis') or {}).get('status')=='pending' and analysis_state(data)['status']=='pending':
            raise ValueError('阅读侧写尚待当前助手分析。先完成 portrait-input 标注并应用，再交付预览；不是用户记录不足。')
        data['distillations'] = merge_books(data.get('distillations'), packages, data.get('source_mode', 'real'))
        # The same packaged builder supplies CSS, fonts, illustration and exports.
        # Validate before atomic replacement; keep all annual data and old books.
        result = build_html(data, output)
        return {**result, 'kind': 'yearbook', 'distillations': len(data['distillations'])}
    if len(packages) != 1:
        raise ValueError('独立蒸馏需提供一本已完成的有效结果；已有报告请传入 --report。')
    validated_distillations(packages, packages[0]['source_mode'])
    atomic_text(output, reader_page(packages[0]))
    return {'output': str(output), 'kind': 'book', 'distillations': 1}


def preview_server(path, port=None):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('预览文件尚未生成。')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            allowed = {'127.0.0.1:'+str(self.server.server_port), 'localhost:'+str(self.server.server_port)}
            if self.headers.get('Host') not in allowed:
                self.send_error(403)
                return
            if urlsplit(self.path).path not in ('/', '/index.html'):
                self.send_error(404)
                return
            body = path.read_bytes()  # Refresh sees the latest atomic update.
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_):
            pass
    # Keep the browser origin stable when reopening the same artifact. A new
    # random port on every launch would silently discard localStorage choices.
    class PreviewHTTPServer(ThreadingHTTPServer):
        # Windows SO_REUSEADDR can bind a second listener to a live server's
        # address. Never allow two reports to share a port unpredictably.
        allow_reuse_address=not hasattr(socket,'SO_EXCLUSIVEADDRUSE')
        def server_bind(self):
            if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
                self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            super().server_bind()
    preferred=49152+int(hashlib.sha256(str(path).encode('utf-8')).hexdigest()[:8],16)%16000 if port is None else port
    try:
        return PreviewHTTPServer(('127.0.0.1', preferred), Handler)
    except OSError:
        if port is not None:raise
        return PreviewHTTPServer(('127.0.0.1', 0), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='当前用户本次已生成的报告；蒸馏自动附到末尾')
    parser.add_argument('--distillation', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, help='默认更新 --report；单独蒸馏需指定HTML路径')
    parser.add_argument('--serve', action='store_true', help='返回本地HTTP预览URL并保持服务运行')
    parser.add_argument('--open', action='store_true', help='在系统默认浏览器打开HTTP预览（隐含--serve）')
    parser.add_argument('--port', type=int, default=None, help='默认复用同一报告的候选端口；0使用临时端口')
    args = parser.parse_args()
    try:
        if not args.output and not args.report:
            raise ValueError('请指定报告或独立HTML输出路径。')
        mode = read_report(args.report).get('source_mode', 'real') if args.report else 'real'
        packages = load_distillations(args.distillation, mode) if args.distillation else []
        result = deliver(args.output or args.report, args.report, packages)
        if not (args.serve or args.open):
            print(json.dumps(result, ensure_ascii=False), flush=True)
            return
        server = preview_server(result['output'], args.port)
        result['preview_url'] = 'http://127.0.0.1:'+str(server.server_port)+'/'
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if args.open:
            webbrowser.open(result['preview_url'])
        try:
            server.serve_forever()
        finally:
            server.server_close()
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, str(error)+'\n')


if __name__ == '__main__':
    main()
