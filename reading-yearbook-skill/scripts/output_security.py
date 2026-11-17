"""Credential checks and network restrictions for static public deliverables."""
import json
import os
import re


STATIC_CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
              "img-src data: blob:; font-src data:; connect-src 'none'; "
              "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def ensure_no_credentials(value):
    """Fail without echoing the offending text; never silently edit a quotation."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, allow_nan=False)
    key = os.environ.get('WEREAD_API_KEY', '').strip()
    if re.search(r'wrk-[A-Za-z0-9_-]{8,}', text) or (len(key) >= 8 and key in text):
        raise ValueError('交付内容中检测到密钥，请移除后重试；原文件保持不变。')
