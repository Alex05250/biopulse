"""Conservative job evidence profiles; never estimate take-home or market wages."""
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
FAMILIES = {
    'wetlab': '实验研发', 'bioinformatics': '生物信息 / 算法',
    'bioprocess': '生产 / 工艺', 'quality': '质量 QA / QC',
    'clinical': '临床 / 医学', 'regulatory': '注册 / 法规',
    'applications': '技术支持 / 应用', 'sales': '销售 / 市场', 'other': '其他 / 待分类',
}
AUDIENCES = {'campus': '应届校招', 'junior': '初级社招', 'experienced': '资深社招', 'academic': '博士后 / 高校序列', 'unknown': '经验要求待核验'}
DEGREES = {'college': '大专', 'bachelor': '本科', 'master': '硕士', 'phd': '博士', 'unknown': '学历未明确'}


def age_days(value, today=None):
    today = today or datetime.now(TZ).date()
    try:
        return max(0, (today - datetime.fromisoformat(value).date()).days)
    except (TypeError, ValueError):
        return None


def profile(record, today=None):
    """Only explicit JD fields support graduate eligibility. Title rules exclude seniors."""
    r = record
    title = (r.get('title', '') + ' ' + r.get('job_level', '')).lower()
    audience = r.get('audience')
    basis = r.get('audience_basis', '')
    if not audience:
        if any(s in title for s in ('博士后', '助理教授', '副教授', 'postdoc', 'professor')):
            audience, basis = 'academic', '按明确高校序列 / 博士后名称排除应届入口'
        elif any(s in title for s in ('director', 'principal', 'head of', ' vp', 'cmo', '总监', '首席')):
            audience, basis = 'experienced', '按明确资深职级排除应届入口；未推断具体工作年限'
        else:
            audience, basis = 'unknown', '尚无可支持经验要求的原文，不能仅凭助理 / 工程师名称认定适合应届'
    reviewed = r.get('verified_at')
    # Re-importing curated.json must NOT renew evidence freshness.
    observed = reviewed or r.get('source_observed_at')
    age = age_days(observed, today)
    deadline = r.get('application_deadline')
    expired = bool(deadline and str(deadline)[:10] < str(today or datetime.now(TZ).date()))
    status = 'expired' if expired else 'closed' if r.get('status') == 'NO_LONGER_LISTED' else 'needs_review' if r.get('source_document_changed') or r.get('source_document_unavailable') else 'stale' if age is None or age > 30 else 'reviewed'
    level = r.get('verification_level', 'list_only' if reviewed else 'api_list' if r.get('source_observed_at') else 'unknown')
    # Reading a complete JD must not override an explicit uncertainty about vacancies.
    vacancy = 'closed' if status in ('expired', 'closed') else 'unconfirmed' if r.get('status') == 'VACANCY_UNCONFIRMED' else 'listed' if level in ('full_jd', 'api_list') and status == 'reviewed' else 'unconfirmed'
    return dict(
        audience=audience, audience_basis=basis,
        education_min=r.get('education_min', 'unknown'),
        education_allowed=r.get('education_allowed', []),
        education_text=r.get('education_text', '原文未核验 / 未提供'),
        experience_text=r.get('experience_text', '原文未明确，不推断'),
        cities=r.get('cities', []), role_family=r.get('role_family', 'other'),
        employer_type=r.get('employer_type', 'unknown'),
        hiring_batch=r.get('hiring_batch', ''), graduation_window=r.get('graduation_window', ''),
        verification_level=level, verified_at=observed, verification_age_days=age,
        freshness=status, vacancy_status=vacancy, application_deadline=deadline,
        quote=salary_quote(r),
    )


def salary_quote(r):
    """No parsing of ambiguous 'K', no guessed 12/13-month salary or tax basis."""
    out = dict(raw=r.get('salary', ''), currency=r.get('salary_currency', 'unknown'),
               period=r.get('salary_period', 'unknown'), tax=r.get('salary_tax_code', 'unknown'),
               component=r.get('salary_component', 'unknown'), scope=r.get('salary_scope', 'job'),
               min=r.get('salary_min'), max=r.get('salary_max'), months=r.get('salary_months'),
               annual_min=None, annual_max=None, conversion='', exclusion=[])
    lo, hi = out['min'], out['max']
    valid = all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0 for v in (lo, hi))
    if not valid:
        out['exclusion'].append('未披露完整、有限的数字上下限')
    elif hi < lo or hi / lo > 5:
        out['exclusion'].append('报价上下限异常，需复核')
        valid = False
    out['numeric'] = bool(valid and out['currency'] == 'CNY' and out['scope'] == 'job' and out['period'] in ('month','year'))
    if out['currency'] != 'CNY': out['exclusion'].append('不是明确人民币报价')
    if out['scope'] != 'job': out['exclusion'].append('招聘批次 / 报告参考，不是单岗位报价')
    if out['tax'] not in ('pre_tax', 'post_tax'): out['exclusion'].append('税前 / 税后口径未明确')
    if out['component'] not in ('base', 'total'): out['exclusion'].append('基本工资 / 总包口径未明确')
    if out['period'] not in ('month', 'year'): out['exclusion'].append('薪酬周期未明确')
    if valid and out['currency'] == 'CNY':
        if out['period'] == 'year':
            out.update(annual_min=lo, annual_max=hi, conversion='原文年薪；不当作每月固定发薪')
        elif out['period'] == 'month' and isinstance(out['months'], int) and 1 <= out['months'] <= 24:
            out.update(annual_min=lo*out['months'], annual_max=hi*out['months'], conversion=f'月报价 × 原文明示 {out["months"]} 薪；不含未注明的额外奖金')
        elif out['period'] == 'month':
            out['conversion'] = '只比较原文月报价；未明确发薪月数，不推算年包'
    return out


def comparison_groups(items, profiles):
    groups = defaultdict(list)
    exclusions = Counter()
    for r in items:
        if r.get('kind') != 'job' or r.get('market') != 'CN': continue
        p = profiles[r['id']]
        reasons = list(p['quote']['exclusion'])
        if p['audience'] not in ('campus', 'junior'): reasons.append('不是已核验应届 / 初级岗位')
        if p['freshness'] != 'reviewed' or p['vacancy_status'] != 'listed': reasons.append('不是近30天可确认的在列岗位')
        if len(p['cities']) != 1: reasons.append('工作城市不唯一 / 未披露')
        if p['education_min'] == 'unknown' or not p['education_allowed']: reasons.append('学历要求不完整')
        if p['role_family'] == 'other': reasons.append('岗位方向待分类')
        employer = r.get('employer_id') or r.get('company', '')
        if not employer or '未披露' in employer: reasons.append('招聘企业未具名')
        if reasons:
            exclusions.update(set(reasons))
            continue
        q = p['quote']
        # Never pool base vs total, month vs year, tax bases, degrees or industries.
        key = (p['cities'][0], p['role_family'], p['audience'], tuple(sorted(p['education_allowed'])),
               p['employer_type'], q['currency'], q['period'], q['tax'], q['component'], q['months'])
        groups[key].append((r, p, employer))
    output = []
    for key, rows in groups.items():
        employers = {employer for _, _, employer in rows}
        enough = len(rows) >= 5 and len(employers) >= 3
        city, family, audience, degrees, employer_type, currency, period, tax, component, months = key
        output.append(dict(id=hashlib.sha256(repr(key).encode()).hexdigest()[:12], city=city,
                           role_family=family, audience=audience, education_allowed=list(degrees), employer_type=employer_type,
                           currency=currency, period=period, tax=tax, component=component, months=months,
                           count=len(rows), employers=len(employers), item_ids=[r['id'] for r, _, _ in rows],
                           sufficient=enough,
                           median_lower=statistics.median(p['quote']['min'] for _, p, _ in rows) if enough else None,
                           median_upper=statistics.median(p['quote']['max'] for _, p, _ in rows) if enough else None,
                           note='岗位报价上下限分别取中位数，不是实际工资或行业均值' if enough else '样本不足：至少5个岗位、3家企业才显示报价中位数'))
    return output, dict(exclusions)


def build(items, meta, document_status=None):
    profiles = {r['id']: profile(r) for r in items if r.get('kind') == 'job'}
    cn = [r for r in items if r.get('kind') == 'job' and r.get('market') == 'CN']
    target = [r for r in cn if profiles[r['id']]['audience'] in ('campus', 'junior')]
    groups, exclusions = comparison_groups(items, profiles)
    return dict(schema_version=1, generated_at=meta['generated_at'], target='本科 / 硕士应届与初级岗位',
                profiles=profiles, families=FAMILIES, audiences=AUDIENCES, degrees=DEGREES,
                counts=dict(cn_jobs=len(cn), target_jobs=len(target),
                            target_employers=len({r.get('employer_id') or r.get('company') for r in target}),
                            disclosed_job_quotes=sum(profiles[r['id']]['quote']['numeric'] for r in target),
                            campaign_references=sum(r.get('salary_scope') == 'campaign' for r in items),
                            verified_open=sum(profiles[r['id']]['vacancy_status'] == 'listed' for r in target)),
                groups=groups, exclusions=exclusions, document_status=document_status or [],
                methodology=dict(minimum_jobs=5, minimum_employers=3, maximum_age_days=30,
                                 warning='公开招聘报价不等于 offer、实际到手或行业均值。简章可读不等于岗位仍有空缺。',
                                 comparison='同城市、岗位方向、校招/初级、学历集合、雇主类型、币种、周期、税口径、基本工资/总包及发薪月数分组；不猜缺失字段。'))
