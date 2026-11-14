import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('collector',Path(__file__).parents[1]/'scripts/collect.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CollectorTests(unittest.TestCase):
    def fixture(self,**kw):
        s={'id':'example','name':'Example','category':'clinical'}
        r=c.record(s,kw.pop('title','A trial'),'https://example.org/study','2026-01-01','trial',status='RECRUITING',phase='PHASE1')
        r.update(kw);return r
    def test_id_and_cross_source_dedup(self):
        a=self.fixture();b=self.fixture(source_refs=['secondary'])
        rows,changes=c.merge([], [a,b], '2026-01-01T08:00:00+08:00')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['source_refs'],['example','secondary']);self.assertEqual(len(changes),1)
    def test_idempotent(self):
        a=self.fixture();old,_=c.merge([], [a], '2026-01-01T08:00:00+08:00')
        new,changes=c.merge(old,[self.fixture()], '2026-01-02T08:00:00+08:00')
        self.assertEqual(changes,[]);self.assertEqual(old[0]['first_seen'],new[0]['first_seen'])
    def test_visible_field_diff(self):
        old,_=c.merge([], [self.fixture()], '2026-01-01T08:00:00+08:00')
        new,changes=c.merge(old,[self.fixture(status='COMPLETED')], '2026-01-02T08:00:00+08:00')
        self.assertEqual(changes[0]['fields'],{'status':{'before':'RECRUITING','after':'COMPLETED'}})
        self.assertEqual(new[0]['updated_at'],'2026-01-02T08:00:00+08:00')
    def test_failures_do_not_delete(self):
        old,_=c.merge([], [self.fixture()]);new,changes=c.merge(old,[])
        self.assertEqual(new,old);self.assertFalse(changes)
    def test_url_sanitizing(self):
        self.assertEqual(c.canonical('javascript:alert(1)'),'')
        self.assertEqual(c.canonical('https://example.org/?utm_source=rss&x=2#f'),'https://example.org/?x=2')
    def test_acronym_boundaries(self):
        self.assertNotIn('adc',c.topic_ids('A CADCAM prototype'))
        self.assertIn('adc',c.topic_ids('New ADC study'))
    def test_no_future_date(self):
        self.assertIsNone(c.day('2099-01-01'))
    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):self.fixture(title='')

if __name__=='__main__':unittest.main()
