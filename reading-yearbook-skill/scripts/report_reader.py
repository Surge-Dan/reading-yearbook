"""Public report preflight and static reader assembly. No task or provider access."""
from pathlib import Path
import json
import re

from distillation_result import load_bundle, validate_bundle

ROOT = Path(__file__).resolve().parents[1]


def validated_distillations(bundles, source_mode='real'):
    if bundles is None:
        return []
    if not isinstance(bundles, list):
        raise ValueError('蒸馏结果包须为列表；不提供蒸馏结果也能生成年度报告。')
    mode = 'sample' if source_mode == 'sample' else 'real'
    for bundle in bundles:
        try:
            validate_bundle(bundle)
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError('所提供的蒸馏结果包无效；请修复结果包，或移除此参数直接生成报告。') from error
        if bundle['source_mode'] != mode:
            raise ValueError('结果包来源不匹配：真实报告不能混入示例 sample；示例报告仅使用 sample 包。')
    return bundles


def load_distillations(paths, source_mode='real'):
    try:
        bundles = [load_bundle(path) for path in paths]
    except (ValueError, OSError, TypeError) as error:
        raise ValueError('蒸馏结果包无法读取或校验失败；请修复结果包，或移除此参数直接生成报告。') from error
    return validated_distillations(bundles, source_mode)


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def reader_section():
    return (ROOT / 'assets/ebook-reader-section.html').read_text('utf-8')


def reader_page(result=None, yearbook=None):
    """Opening an old report never invokes the new-report preflight or a task."""
    section = reader_section()
    css = '\n'.join((ROOT / 'assets' / name).read_text('utf-8') for name in
                    ('reading-app.css', 'reading-art.css', 'ebook-app.css'))
    app = '<script id="ebook-app-mounted">' + (ROOT / 'assets/ebook-app.js').read_text('utf-8') + '</script>'
    art = '<script id="reading-share-mounted">' + (ROOT / 'assets/reading-share-art.js').read_text('utf-8') + '</script>'
    if yearbook:
        page = Path(yearbook).read_text('utf-8')
        from cover_contract import check_yearbook_page
        try:
            page = check_yearbook_page(page)
        except (ValueError, TypeError):
            notice = '<section role="status" data-yearbook-blocked="true"><h2>年度报告暂未就绪</h2><p>年鉴书目数据无法读取，请让助手修复后重新打开。</p></section>'
            return reader_page(result).replace('<main>', '<main>' + notice, 1)
        if result is None:
            old = re.search(r'window\.EBOOK_RESULT=(.*?);?\s*</script>', page, re.S)
            if old:
                try:
                    result = json.loads(old.group(1))
                except (ValueError, TypeError):
                    pass
        existing = re.search(r'<section\b[^>]*\bid="ebook"[^>]*>', page)
        if existing:
            depth = 0
            for tag in re.finditer(r'<(/?)section\b[^>]*>', page[existing.start():]):
                depth += -1 if tag.group(1) else 1
                if depth == 0:
                    page = page[:existing.start()] + section + page[existing.start()+tag.end():]
                    break
        else:
            page = page.replace('</main>', section + '</main>', 1)
        # Preserve old annual data, replace only task UI/config and current reader assets.
        page = re.sub(r'<script id="ebook-config">.*?</script>', '', page, flags=re.S)
        page = re.sub(r'<script id="ebook-app-mounted">.*?</script>', '', page, flags=re.S)
        if 'id="reading-share-mounted"' in page:
            page = re.sub(r'<script id="reading-share-mounted">.*?</script>',lambda _: art,page,flags=re.S)
        else:
            # Very old reports combined artwork and annual app in one script;
            # preserve that app and initialize the current exporter for the reader.
            page = page.replace('</body>', art + '</body>', 1)
        page = page.replace('</head>', '<style>' + css + '</style></head>', 1)
    else:
        page = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1"><title>年年阅 · 书籍精华</title>'
                '<style>' + css + '</style></head><body class="ebook-standalone"><div class="paper"><main>'
                + section + '</main></div>' + art + '</body></html>')
    injection = '<script id="ebook-config">window.EBOOK_RESULT=' + safe_json(result) + ';</script>'
    return page.replace('</head>', injection + '</head>', 1).replace('</body>', app + '</body>', 1)
