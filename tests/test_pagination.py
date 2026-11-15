import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

sp=importlib.util.spec_from_file_location('collector_paging',Path(__file__).parents[1]/'scripts/collect.py')
c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)

class PaginationTests(unittest.TestCase):
    def test_europe_pmc_uses_cursor_and_reports_real_coverage(self):
        source={'id':'s','name':'Test','category':'research','query':'CRISPR','limit':1,'max_records':3}
        def row(i):return {'id':str(i),'source':'MED','title':'CRISPR study '+str(i),'firstPublicationDate':'2026-01-01'}
        responses=iter([{'hitCount':3,'resultList':{'result':[row(1),row(2)]},'nextCursorMark':'next'}, {'hitCount':3,'resultList':{'result':[row(3)]},'nextCursorMark':'end'}])
        with patch.object(c,'api',side_effect=lambda *args:next(responses)) as mock:
            rows,coverage=c.epmc(source)
            self.assertEqual(len(rows),3);self.assertFalse(coverage['sampled'])
            self.assertEqual(mock.call_args_list[1].args[1]['cursorMark'],'next')

    def test_europe_pmc_cap_is_not_claimed_as_full_coverage(self):
        source={'id':'s','name':'Test','category':'research','query':'x','limit':1}
        with patch.object(c,'api',return_value={'hitCount':100,'resultList':{'result':[]}}):
            rows,coverage=c.epmc(source)
        self.assertTrue(coverage['sampled']);self.assertEqual(coverage['fetched'],0)

    def test_manual_verification_stamp_survives_offline_merge(self):
        source={'id':'s','name':'Test','category':'career'}
        r=c.record(source,'岗位','https://example.org',None,'job',verified_at='2026-10-01T08:00:00+08:00')
        rows,_=c.merge([], [r], '2026-11-15T08:00:00+08:00')
        self.assertEqual(rows[0]['last_seen'],'2026-10-01T08:00:00+08:00')

    def test_trials_page_and_old_nct_recheck(self):
        source={'id':'trials','name':'Clinical','category':'clinical','limit':1,'max_records':3}
        def row(n):return {'protocolSection':{'identificationModule':{'nctId':n,'briefTitle':'Trial '+n},'statusModule':{'overallStatus':'RECRUITING','lastUpdatePostDateStruct':{'date':'2026-01-01'}}}}
        responses=iter([{'studies':[row('NCT00000001')],'totalCount':2,'nextPageToken':'next'}, {'studies':[row('NCT00000002')]}, {'studies':[row('NCT00000003')]}])
        with patch.object(c,'api',side_effect=lambda *a:next(responses)) as mock,patch.object(c,'read',return_value=[{'nct_id':'NCT00000003'}]):
            rows,coverage=c.trials(source)
        self.assertEqual(len(rows),3);self.assertEqual(coverage['tracked_checked'],1)
        self.assertEqual(mock.call_args_list[2].args[1]['filter.ids'],'NCT00000003')

    def test_tracked_nct_failure_keeps_discovery_rows_and_is_explicit(self):
        source={'id':'trials','name':'Clinical','category':'clinical','limit':1}
        def fake(url,params):
            if 'filter.ids' in params:raise RuntimeError('Registry temporarily unavailable')
            return {'studies':[],'totalCount':0}
        with patch.object(c,'api',side_effect=fake),patch.object(c,'read',return_value=[{'nct_id':'NCT00000003'}]):
            rows,coverage=c.trials(source)
        self.assertEqual(rows,[]);self.assertTrue(coverage['partial']);self.assertTrue(coverage['tracked_errors'])

if __name__=='__main__':unittest.main()
