import os
import shutil
import subprocess
import unittest
from pathlib import Path


class CalendarTests(unittest.TestCase):
    def test_calendar_dates_and_missingness(self):
        node=os.environ.get('SHARE_NODE') or shutil.which('node')
        if not node:self.skipTest('Node is required for the renderer data contract')
        result=subprocess.run([node,str(Path(__file__).with_name('reading_calendar_data.cjs'))],capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
