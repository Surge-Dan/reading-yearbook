"""Project checks; never install dependencies, collect account data or call models."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


def run(command):
    subprocess.run([str(x) for x in command],cwd=ROOT,check=True,timeout=600)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick',action='store_true',help='core tests only; explicitly excludes Python UI and browser export suites')
    args=parser.parse_args()
    os.chdir(ROOT)
    vendor=ROOT/'reading-yearbook-skill/.vendor'
    if vendor.is_dir():sys.path.insert(0,str(vendor))
    node=os.environ.get('SHARE_NODE') or shutil.which('node')
    if not args.quick:
        missing=[name for name in ('PIL','fontTools','brotli','pypdf','playwright') if importlib.util.find_spec(name) is None]
        if missing or not node:
            parser.exit(2,'完整检查依赖未齐：'+', '.join(missing+([] if node else ['Node']))+'。请安装requirements-dev.txt及npm开发依赖；快速检查使用--quick。\n')
        try:
            module=subprocess.check_output([node,'-p',"require.resolve('playwright')"],cwd=ROOT,text=True,timeout=15).strip()
        except (subprocess.SubprocessError,OSError):
            parser.exit(2,'缺少Node版Playwright，请先npm install，或设置NODE_PATH。\n')
        os.environ.setdefault('SHARE_PLAYWRIGHT',str(Path(module).parent))
        os.environ.setdefault('SHARE_NODE',node)
        edge=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        browser=os.environ.get('BROWSER_EXECUTABLE') or (str(edge) if edge.is_file() else '')
        if browser:os.environ.setdefault('SHARE_BROWSER',browser)
    sys.path.insert(0,str(ROOT/'tests'))
    suite=unittest.TestSuite();omitted=[]
    for path in sorted((ROOT/'tests').glob('test_*.py')):
        if args.quick and 'from playwright' in path.read_text('utf-8'):
            omitted.append(path.name);continue
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(path.stem))
    if omitted:print('QUICK ONLY: excluded Python browser modules: '+', '.join(omitted),flush=True)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():return 1
    if args.quick:
        print('Core checks completed; browser exports and excluded UI modules were not verified.');return 0
    fixtures=ROOT/'demo-output/project-checks';demo=ROOT/'reading-yearbook-skill/examples/reading-html-demo/index.html'
    run([sys.executable,'-X','utf8',ROOT/'tests/build_reading_experience_fixtures.py',fixtures])
    commands=[['reading_share_art.cjs',demo,fixtures,fixtures/'art'],
        ['reading_html_share_picker.cjs',fixtures,demo],['report_reader_browser.cjs'],
        ['document_exports.cjs',demo,fixtures/'documents'],['pdf_covers.cjs',demo,fixtures/'reading.pdf']]
    for script,*arguments in commands:run([node,ROOT/'tests'/script,*arguments])
    print('Full configured checks passed. This does not verify live APIs or model quality.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
