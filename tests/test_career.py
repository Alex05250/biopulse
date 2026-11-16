import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/(name+'.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
c = module('career')
d = module('check_documents')

class CareerTests(unittest.TestCase):
    def job(self, **changes):
        row = dict(id='test',kind='job',market='CN',title='研发工程师',company='雇主A',
                   audience='campus',education_min='bachelor',education_allowed=['bachelor'],
                   cities=['杭州'],role_family='wetlab',employer_type='enterprise',
                   verified_at='2026-11-15T10:00:00+08:00',verification_level='full_jd',
                   salary='6,000–8,000元/月',salary_min=6000,salary_max=8000,salary_currency='CNY',
                   salary_period='month',salary_tax_code='pre_tax',salary_component='base')
        row.update(changes); return row

    def test_unknown_pay_months_does_not_invent_annual_package(self):
        q=c.salary_quote(self.job())
        self.assertIsNone(q['annual_min']);self.assertIn('不推算年包',q['conversion'])

    def test_explicit_13_months_only(self):
        self.assertEqual(c.salary_quote(self.job(salary_months=13))['annual_min'],78000)

    def test_campaign_not_replicated_as_job_salary(self):
        self.assertTrue(any('单岗位' in s for s in c.salary_quote(self.job(salary_scope='campaign'))['exclusion']))

    def test_unknown_tax_and_components_excluded(self):
        q=c.salary_quote(self.job(salary_tax_code='unknown',salary_component='unknown'))
        self.assertEqual(len(q['exclusion']),2)

    def test_one_sided_infinite_or_inverted_ranges_rejected(self):
        for changes in ({'salary_max':None},{'salary_max':float('inf')},{'salary_min':9000},{'salary_max':1000000}):
            self.assertTrue(c.salary_quote(self.job(**changes))['exclusion'])

    def test_assistant_professor_is_not_entry_level(self):
        self.assertEqual(c.profile(self.job(title='研究助理教授',audience=None))['audience'],'academic')

    def test_title_alone_does_not_make_a_graduate_job(self):
        self.assertEqual(c.profile(self.job(title='研究助理',audience=None))['audience'],'unknown')

    def test_campus_manager_title_keeps_explicit_source_classification(self):
        self.assertEqual(c.profile(self.job(title='销售经理',audience='campus'))['audience'],'campus')

    def test_reimport_does_not_refresh_verification(self):
        p=c.profile(self.job(verified_at='2026-08-01T10:00:00+08:00',last_seen='2026-11-15T10:00:00+08:00'),date(2026,11,15))
        self.assertEqual(p['freshness'],'stale')

    def test_document_read_is_not_vacancy_confirmation(self):
        p=c.profile(self.job(verification_level='document_review'),date(2026,11,15))
        self.assertEqual(p['freshness'],'reviewed');self.assertEqual(p['vacancy_status'],'unconfirmed')

    def test_explicit_unconfirmed_vacancy_overrides_full_jd_review(self):
        row=self.job(status='VACANCY_UNCONFIRMED')
        p=c.profile(row,date(2026,11,15))
        self.assertEqual(p['verification_level'],'full_jd')
        self.assertEqual(p['freshness'],'reviewed')
        self.assertEqual(p['vacancy_status'],'unconfirmed')
        groups,_=c.comparison_groups([row],{row['id']:p})
        self.assertEqual(groups,[])

    def test_deadline_and_document_change_override_recent_review(self):
        self.assertEqual(c.profile(self.job(application_deadline='2026-10-31'),date(2026,11,15))['freshness'],'expired')
        self.assertEqual(c.profile(self.job(source_document_changed=True),date(2026,11,15))['freshness'],'needs_review')
        self.assertEqual(c.profile(self.job(source_document_unavailable=True),date(2026,11,15))['freshness'],'needs_review')

    def test_no_median_for_single_employer_or_small_n(self):
        rows=[self.job(id=str(i)) for i in range(6)]
        groups,_=c.comparison_groups(rows,{r['id']:c.profile(r,date(2026,11,15)) for r in rows})
        self.assertFalse(groups[0]['sufficient']);self.assertIsNone(groups[0]['median_lower'])

    def test_medians_are_quote_bounds_not_imaginary_wages(self):
        rows=[self.job(id=str(i),company='雇主'+str(i%3)) for i in range(6)]
        groups,_=c.comparison_groups(rows,{r['id']:c.profile(r,date(2026,11,15)) for r in rows})
        self.assertTrue(groups[0]['sufficient']);self.assertEqual(groups[0]['median_lower'],6000);self.assertEqual(groups[0]['median_upper'],8000)

    def test_different_city_degree_tax_or_package_not_pooled(self):
        rows=[self.job(id='a'),self.job(id='b',salary_component='total'),self.job(id='c',cities=['广州']),self.job(id='d',salary_tax_code='post_tax'),self.job(id='e',education_allowed=['master'])]
        groups,_=c.comparison_groups(rows,{r['id']:c.profile(r,date(2026,11,15)) for r in rows})
        self.assertEqual(len(groups),5)

    def test_document_watcher_detects_change_without_claiming_new_vacancies(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config').mkdir();(root/'data').mkdir()
            (root/'config/career_sources.json').write_text(json.dumps({'documents':[{'id':'doc','source_id':'s','url':'https://example.org/a.pdf','reviewed_sha256':'different'}]}))
            old=d.ROOT;d.ROOT=root
            try:
                states=d.check(lambda u:b'%PDF changed data')
                self.assertEqual(states[0]['state'],'changed')
                self.assertNotIn('vacancy_confirmed',states[0])
            finally:d.ROOT=old

if __name__=='__main__':unittest.main()
