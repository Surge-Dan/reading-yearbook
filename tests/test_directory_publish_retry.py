import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reading-yearbook-skill/scripts'))
import run_yearbook


class DirectoryRetryTests(unittest.TestCase):
    def locked(self):
        error = PermissionError('directory temporarily locked')
        error.winerror = 5
        return error

    def test_transient_lock_retries_only_replace(self):
        with patch.object(run_yearbook.os, 'replace', side_effect=[self.locked(), None]) as move, patch.object(run_yearbook.time, 'sleep') as sleep:
            run_yearbook._replace_directory(Path('stage'), Path('output'))
        self.assertEqual(move.call_count, 2)
        sleep.assert_called_once_with(0.02)

    def test_persistent_lock_is_bounded(self):
        with patch.object(run_yearbook.os, 'replace', side_effect=self.locked()) as move, patch.object(run_yearbook.time, 'sleep'), self.assertRaises(PermissionError):
            run_yearbook._replace_directory(Path('stage'), Path('output'))
        self.assertEqual(move.call_count, 8)

    def test_other_errors_are_not_retried(self):
        with patch.object(run_yearbook.os, 'replace', side_effect=PermissionError('denied')), patch.object(run_yearbook.time, 'sleep') as sleep, self.assertRaises(PermissionError):
            run_yearbook._replace_directory(Path('stage'), Path('output'))
        sleep.assert_not_called()
