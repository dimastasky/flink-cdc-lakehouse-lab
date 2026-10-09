import sys,unittest
from decimal import Decimal
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify import difference,normalize,expected_state
class ReconciliationTest(unittest.TestCase):
    def test_snapshot_reads_multiline_json_without_rounding_money(self):
        payload='''{"customers": [], "accounts": [], "payments": [
            {"payment_id": 1, "amount": 1234567890123456.78}
        ]}'''
        with patch('verify.pg',return_value=payload) as read:
            result=expected_state()
        self.assertEqual(result['payments'][0]['amount'],Decimal('1234567890123456.78'))
        self.assertIn('REPEATABLE READ READ ONLY',read.call_args.args[0])
    def test_invalid_snapshot_has_actionable_error(self):
        for payload in ('', 'COMMIT', '{}', '{"customers": null,"accounts": [],"payments": []}'):
            with self.subTest(payload=payload),patch('verify.pg',return_value=payload):
                with self.assertRaisesRegex(RuntimeError,'PostgreSQL snapshot'):
                    expected_state()
    def test_count_does_not_hide_replaced_key(self):
        self.assertIsNotNone(difference([{'id':1}],[{'id':2}],'id'))
    def test_nulls_money_and_timezone(self):
        self.assertIsNone(difference([{'id':1,'amount':'1.20','country_code':None,'event_time':'2026-01-01T01:00:00.123+01:00'}],[{'id':1,'amount':'1.2','country_code':None,'event_time':'2026-01-01 00:00:00.123 UTC'}],'id'))
    def test_duplicate_and_stale_version(self):
        self.assertIsNotNone(difference([{'id':1}],[{'id':1},{'id':1}],'id'))
        self.assertIsNotNone(difference([{'id':1,'row_version':3}],[{'id':1,'row_version':2}],'id'))
    def test_precision_not_silently_truncated(self):
        with self.assertRaises(AssertionError):normalize({'event_time':'2026-01-01T00:00:00.123456Z'})
        with self.assertRaises(AssertionError):normalize({'event_time':'2026-01-01T00:00:00.1230001Z'})
    def test_short_postgres_fractions_on_python39(self):
        for short,full in [('1','100'),('13','130'),('0','000')]:
            with self.subTest(fraction=short):
                self.assertEqual(normalize({'event_time':f'2026-01-01T00:00:00.{short}+00:00'}),
                                 normalize({'event_time':f'2026-01-01 00:00:00.{full} UTC'}))
