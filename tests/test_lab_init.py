import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import lab


class InitTest(unittest.TestCase):
    def test_add_bi_credentials_without_rotating_existing_passwords(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config').mkdir()
            for name in ('flink-conf.yaml.template', 'gravitino.conf.template',
                         'trino-iceberg.properties.template'):
                (root / 'config' / name).write_text('')
            (root / 'versions.env').write_text('JAVA_RELEASE=17\n')
            (root / '.env.example').write_text(
                'APP_PASSWORD=placeholder\nSUPERSET_ADMIN_USERNAME=admin\n'
                'SUPERSET_ADMIN_PASSWORD=placeholder\nSUPERSET_SECRET_KEY=placeholder\n'
            )
            (root / '.env').write_text('APP_PASSWORD=keep_existing_password\n')
            with patch.object(lab, 'ROOT', root), patch.dict('os.environ', {}, clear=True), \
                    contextlib.redirect_stdout(io.StringIO()):
                lab.init()
                first = lab.read_env(root / '.env')
                lab.init()
                second = lab.read_env(root / '.env')
            self.assertEqual(first, second)
            self.assertEqual(first['APP_PASSWORD'], 'keep_existing_password')
            self.assertEqual(first['SUPERSET_ADMIN_USERNAME'], 'admin')
            for key in ('SUPERSET_ADMIN_PASSWORD', 'SUPERSET_SECRET_KEY'):
                self.assertEqual(len(first[key]), 64)
                self.assertNotEqual(first[key], 'placeholder')
