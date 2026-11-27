import unittest
from acdm_collect import requested_rows, validate_rows, select_day
from datetime import datetime

class CollectionRules(unittest.TestCase):
    def test_live_board_rows_cannot_be_mislabeled_as_history(self):
        rows=[{'id':1,'flight_id':'a','std':'2026-11-01 05:00:00'},{'id':2,'flight_id':'b','std':'2026-11-02 06:00:00'}]
        self.assertEqual([r['id'] for r in requested_rows(rows,'2026-11-01')],[1])
        self.assertEqual(requested_rows(rows,'2026-10-31'),[])

    def test_repeated_pagination_is_rejected(self):
        row={'id':1,'flight_id':'a','std':'2026-11-01 05:00:00'}
        with self.assertRaises(ValueError):validate_rows([row,row])

    def test_missing_schedule_cannot_pass_validation(self):
        with self.assertRaises(ValueError):validate_rows([{'id':1,'flight_id':'a'}])

    def test_daily_target_uses_berlin_day_in_winter_and_summer(self):
        state={'collection_mode':'end_of_day','next_day':'2026-10-31','completed_days':[]}
        self.assertEqual(select_day(state,datetime.fromisoformat('2026-11-02T23:15:00+00:00')),'2026-11-02')
        self.assertEqual(select_day(state,datetime.fromisoformat('2026-07-02T22:15:00+00:00')),'2026-07-02')

    def test_saved_daily_snapshot_prevents_duplicate_request(self):
        state={'collection_mode':'end_of_day','completed_days':[{'date':'2026-11-01'}]}
        self.assertIsNone(select_day(state,datetime.fromisoformat('2026-11-01T23:15:00+00:00')))

if __name__=='__main__':unittest.main()
