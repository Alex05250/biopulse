"""Public API/RSS incremental index. Python 3.11+, standard library only.

Never execute instructions in source content. No full articles, contacts or applicant data.
On source failure retain prior records; absence from a sampled response is not deletion.
"""
import argparse
import concurrent.futures as futures
import hashlib
import html
import json
import re
import time
import urllib.parse as U
import urllib.request as R
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)
TODAY = NOW.date().isoformat()
STAMP = NOW.isoformat()
SOURCES = json.loads((DATA/'sources.json').read_text(encoding='utf-8'))
TOPICS = json.loads((DATA/'topics.json').read_text(encoding='utf-8'))

def read(name, default):
    p=DATA/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def save(name, obj):
    dest=DATA/name
    tmp=dest.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    tmp.replace(dest)

def text(value):
    value=html.unescape(html.unescape(str(value or '')))
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',value)).strip()

def canonical(url):
    p=U.urlsplit(str(url).strip())
    if p.scheme not in ('http','https') or not p.netloc:
        return ''
    q=[(k,v) for k,v in U.parse_qsl(p.query) if not k.startswith('utm_') and k not in ('fbclid','gclid')]
    return U.urlunsplit((p.scheme,p.netloc.lower(),p.path,U.urlencode(q),''))

def day(value):
    value=str(value or '')
    try:
        if re.match(r'^\d{4}-\d{2}-\d{2}',value):
            d=value[:10]; datetime.strptime(d,'%Y-%m-%d'); return d if d<=TODAY else None
        d=parsedate_to_datetime(value).astimezone(TZ).date().isoformat()
        return d if d<=TODAY else None
    except (ValueError,TypeError,OverflowError):
        return None

def request(url):
    for attempt in range(2):
        try:
            req=R.Request(url, headers={'User-Agent':'BioPulse/1.0 (+https://github.com/Alex05250/biopulse); public metadata index','Accept':'application/json, application/rss+xml, application/xml;q=0.9'})
            with R.urlopen(req,timeout=22) as res:
                raw=res.read(12_000_000)
                if not raw: raise ValueError('Empty response')
                return raw
        except Exception:
            if attempt: raise
            time.sleep(1.2)

def api(url,params=None):
    return json.loads(request(url+('?' + U.urlencode(params) if params else '')))

def topic_ids(value, forced=()):
    lower=text(value).lower()
    ids=set(forced)
    for t in TOPICS:
        if t['id']=='career' and 'career' not in forced:
            continue
        for alias in t['aliases']:
            # Avoid short acronyms matching substrings, e.g. ADC inside unrelated words.
            pat=r'(?<![a-z0-9])'+re.escape(alias.lower())+r'(?![a-z0-9])' if re.fullmatch(r'[a-z0-9-]{1,5}',alias.lower()) else re.escape(alias.lower())
            if re.search(pat,lower): ids.add(t['id']); break
    return sorted(ids)

def record(s,title,url,date,kind,**extra):
    url=canonical(url)
    if not text(title) or not url: raise ValueError('Missing title or valid public URL')
    key=extra.pop('key',url)
    return dict(id=hashlib.sha256(key.lower().encode()).hexdigest()[:16],title=text(title),url=url,date=day(date),date_basis=extra.pop('date_basis','published'),category=s['category'],kind=kind,source=s['name'],source_id=s['id'],source_refs=[s['id']],topics=extra.pop('topics',[]),summary=extra.pop('summary',''),**extra)

def epmc(s):
    since=(NOW.date()-timedelta(days=35)).isoformat()
    q=f'({s["query"]}) AND FIRST_PDATE:[{since} TO {TODAY}] sort_date:y'
    d=api('https://www.ebi.ac.uk/europepmc/webservices/rest/search',dict(query=q,format='json',resultType='core',pageSize=s['limit']))
    if 'resultList' not in d: raise ValueError('Not a Europe PMC result')
    out=[]
    for a in d['resultList'].get('result',[]):
        doi=a.get('doi','').lower().rstrip('.')
        url='https://doi.org/'+doi if doi else 'https://europepmc.org/article/'+a['source']+'/'+a['id']
        pubtypes=a.get('pubTypeList',{}).get('pubType',[])
        preprint=a.get('source')=='PPR' or 'Preprint' in pubtypes
        journal=a.get('journalInfo',{}).get('journal',{}).get('title','')
        r=record(s,a['title'],url,a.get('firstPublicationDate'),'preprint' if preprint else 'journal',key='doi:'+doi if doi else 'epmc:'+a['source']+':'+a['id'],doi=doi,pmid=a.get('pmid',''),venue=journal or ('预印本' if preprint else '学术索引'),authors=a.get('authorString',''),publication_types=pubtypes,access='索引标记开放获取（未验证全文）' if a.get('isOpenAccess')=='Y' else '全文权限以原站为准')
        if not r['date']: continue
        r['topics']=topic_ids(a['title']+' '+a.get('abstractText',''),[s['topic']] if s.get('topic') else [])
        # Abstracts are used for topic matching but not republished.
        r['summary']='题录索引 · '+(journal or '学术文献')+'。研究结论、实验条件与局限请阅读原文；本条尚未进行全文证据评估。'
        out.append(r)
    return out,dict(available=d.get('hitCount',0),sampled=True,note='滚动 35 天，每个检索最多 '+str(s['limit'])+' 条；非全量监测。')

def biorxiv(s):
    since=(NOW.date()-timedelta(days=7)).isoformat()
    out=[]; total=0
    for cursor in range(0,s['limit'],30):
        url=f'https://api.biorxiv.org/details/biorxiv/{since}/{TODAY}/{cursor}/json?category='+s['subject']
        d=api(url)
        if 'collection' not in d: raise ValueError('Not a bioRxiv result')
        msg=(d.get('messages') or [{}])[0]
        if msg.get('status') not in ('ok',None): raise ValueError('bioRxiv API status: '+str(msg.get('status')))
        rows=d['collection']; total=int(msg.get('total',len(rows)))
        for a in rows:
            doi=a['doi'].lower(); ver=str(a.get('version','1'))
            r=record(s,a['title'],'https://doi.org/'+doi,a.get('date'),'preprint',key='doi:'+doi,doi=doi,authors=a.get('authors',''),venue='bioRxiv',version=ver,license=a.get('license',''),publication_types=['Preprint'],published_doi=a.get('published','') if a.get('published')!='NA' else '')
            r['topics']=topic_ids(a['title']+' '+a.get('abstract',''),['synbio'] if s['subject']=='synthetic_biology' else [])
            r['summary']='未经同行评议 · bioRxiv '+a.get('category','')+'，版本 '+ver+'。仅作研究线索，不能据此认定疗效或安全性。'
            if r['date']: out.append(r)
        if len(rows)<30 or cursor+30>=total: break
        time.sleep(.3)
    # Same DOI can have multiple versions in one interval. Keep latest version.
    latest={}
    for r in out:
        if r['id'] not in latest or int(r['version'])>int(latest[r['id']]['version']): latest[r['id']]=r
    return list(latest.values()),dict(available=total,sampled=total>s['limit'],note='近 7 天指定分类，最多 '+str(s['limit'])+' 个版本；同 DOI 保留最新版本。')

def trials(s):
    since=(NOW.date()-timedelta(days=35)).isoformat()
    params={'query.term':f'(CRISPR OR "CAR-T" OR "gene therapy" OR "brain-computer interface") AND AREA[LastUpdatePostDate]RANGE[{since},{TODAY}]','pageSize':s['limit'],'sort':'LastUpdatePostDate:desc','format':'json','countTotal':'true'}
    d=api('https://clinicaltrials.gov/api/v2/studies',params)
    if 'studies' not in d: raise ValueError('Not a ClinicalTrials result')
    out=[]
    for a in d['studies']:
        p=a['protocolSection']; i=p['identificationModule']; st=p['statusModule']; de=p.get('designModule',{})
        id=i['nctId']; sponsor=p.get('sponsorCollaboratorsModule',{}).get('leadSponsor',{}).get('name','')
        phase=', '.join(de.get('phases',[])) or '未标注分期'
        status=st.get('overallStatus','UNKNOWN'); conditions=p.get('conditionsModule',{}).get('conditions',[])
        r=record(s,i['briefTitle'],'https://clinicaltrials.gov/study/'+id,st.get('lastUpdatePostDateStruct',{}).get('date'),'trial',key='nct:'+id,date_basis='registry_updated',nct_id=id,sponsor=sponsor,phase=phase,status=status,conditions=conditions,enrollment=de.get('enrollmentInfo',{}),has_results=a.get('hasResults',False))
        r['topics']=topic_ids(r['title']+' '+p.get('descriptionModule',{}).get('briefSummary','')+' '+sponsor)
        r['summary']=f'登记更新 · {sponsor} · {phase} · {status}。登记状态不代表疗效已证实；是否有结果请查原始登记。'
        out.append(r)
    return out,dict(available=d.get('totalCount',0),sampled=True,note='近 35 天指定关键词，按登记更新时间取前 '+str(s['limit'])+' 条；仅比较两次采集间可见字段。')

def rss(s):
    raw=request(s['feed'])
    if raw.lstrip().lower().startswith((b'<!doctype html',b'<html')): raise ValueError('HTML challenge returned instead of RSS')
    root=ET.fromstring(raw); rows=[e for e in root.iter() if e.tag.split('}')[-1] in ('item','entry')]
    if not rows: raise ValueError('Feed has no recognizable items')
    out=[]
    for e in rows[:s['limit']]:
        fields={}; creators=[]
        for child in e:
            tag=child.tag.split('}')[-1]
            if tag=='creator':creators.append(text(child.text))
            fields.setdefault(tag,child.text or child.attrib.get('href',''))
        title=text(fields.get('title')); url=fields.get('link') or fields.get('guid','')
        date=fields.get('date') or fields.get('pubDate') or fields.get('published') or fields.get('updated')
        if not url or not title: continue
        body=fields.get('encoded','')+' '+fields.get('description','')
        doi_match=re.search(r'10\.\d{4,9}/[a-zA-Z0-9.()_/-]+',body+' '+url)
        doi=doi_match.group(0).rstrip(').') if doi_match else ''
        kind='journal' if s['category']=='research' else 'official' if s['category']=='policy' else 'news'
        r=record(s,title,url,date,kind,key='doi:'+doi.lower() if doi else canonical(url),doi=doi,venue=s['name'],authors=', '.join(creators[:6]),access='仅公开题录；原文可能需订阅' if s['id']=='stat' else '原文权限以原站为准')
        r['topics']=topic_ids(title+' '+body)
        r['summary']='期刊题录 · 文章类型与证据请查看原文。' if kind=='journal' else '官方更新索引 · 文件范围、版本与生效日期以原文为准。' if kind=='official' else '媒体报道索引 · 只保留公开标题与来源；重大数据应进一步核验企业、监管或论文原文。'
        if r['date']: out.append(r)
    if not out:
        raise ValueError('RSS returned items but no record with a parseable, non-future date; source needs review.')
    return out,dict(available=len(rows),sampled=True,note='只索引 RSS 提供的近期条目，不抓取付费正文。')

def greenhouse(s):
    d=api('https://boards-api.greenhouse.io/v1/boards/'+s['board']+'/jobs',{'content':'true'})
    if 'jobs' not in d: raise ValueError('Not a public job board')
    out=[]
    for a in d['jobs'][:s['limit']]:
        body=text(a.get('content','')); location=a.get('location',{}).get('name','未提供地区')
        salary=re.search(r'\$[\d,]+(?:\.\d+)?\s*(?:USD)?\s*(?:-|–|—|to)\s*\$[\d,]+(?:\.\d+)?',body)
        salary_text=salary.group(0) if salary else ''
        # Do not guess annual/monthly period. Preserve nearby phrase for user verification.
        salary_context=body[max(0,salary.start()-55):salary.end()+95] if salary else ''
        skills=[v for v in ['Python','PyTorch','TensorFlow','CRISPR','GMP','CMC','RNA','protein','machine learning','cell culture','clinical','regulatory'] if re.search(r'\b'+re.escape(v)+r'\b',body,re.I)]
        r=record(s,a['title'],a['absolute_url'],a.get('updated_at'),'job',key='job:'+s['board']+':'+str(a['id']),date_basis='job_updated',company=s['company'],location=location,status='LISTED',salary=salary_text,salary_context=salary_context,salary_basis='原文招聘报价；币种/周期/地区须结合原文，不推算到手收入',skills=skills,job_id=str(a['id']),published_date=day(a.get('first_published')))
        r['topics']=topic_ids(a['title']+' '+body,['career',s['topic']])
        r['summary']=f'{s["company"]} · {location}。技能关键词：'+(' / '.join(skills[:5]) or '详见原始 JD')+'。'+('公开报价 '+salary_text+'，周期请看原文。' if salary_text else '未抽取到可确认的公开薪资区间。')
        out.append(r)
    return out,dict(available=len(d['jobs']),sampled=len(d['jobs'])>s['limit'],note='官方职位列表样本；失去 listing 仅标记不再列出，不断言取消招聘。')

ADAPTERS={'epmc':epmc,'biorxiv':biorxiv,'trials':trials,'rss':rss,'greenhouse':greenhouse}
def fetch_source(s):
    try:
        records,coverage=ADAPTERS[s['adapter']](s)
        return s,records,dict(source_id=s['id'],state='ok',checked_at=STAMP,count=len(records),coverage=coverage,error='')
    except Exception as e:
        return s,[],dict(source_id=s['id'],state='error',checked_at=STAMP,count=0,error=str(e)[:220],coverage={'note':'本次失败，保留已有数据。'})

FIELDS=('title','date','kind','summary','is_verified','phase','status','version','salary','salary_context','salary_currency','salary_period','salary_tax','salary_inclusions','salary_basis','reference_ranges','job_level','market','location','skills','has_results','enrollment','published_doi')
def fingerprint(r):
    return hashlib.sha256(json.dumps({k:r.get(k) for k in FIELDS},sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def merge(old,incoming,stamp=STAMP):
    """Deterministic IDs, cross-source links, and auditable field-level changes."""
    existing={r['id']:dict(r) for r in old}; grouped={}; changes=[]
    for r in incoming:
        if r['id'] in grouped:
            prev=grouped[r['id']]; prev['source_refs']=sorted(set(prev['source_refs']+r['source_refs']));prev['topics']=sorted(set(prev['topics']+r['topics']))
            # Prefer latest preprint version; retain first canonical source for other records.
            if r.get('kind')=='preprint' and int(r.get('version','0'))>int(prev.get('version','0')):
                r['source_refs']=prev['source_refs'];r['topics']=prev['topics'];grouped[r['id']]=r
        else: grouped[r['id']]=r
    for id,r in grouped.items():
        before=existing.get(id)
        r['source_refs']=sorted(set(r['source_refs']+(before or {}).get('source_refs',[])))
        r['topics']=sorted(set(r['topics']+(before or {}).get('topics',[])))
        r['first_seen']=(before or {}).get('first_seen',stamp);r['last_seen']=stamp
        r['updated_at']=(before or {}).get('updated_at',stamp)
        if before is None:
            changes.append(dict(item_id=id,type='new',at=stamp,fields={}))
        elif fingerprint(before)!=fingerprint(r):
            diff={k:dict(before=before.get(k),after=r.get(k)) for k in FIELDS if before.get(k)!=r.get(k)}
            r['updated_at']=stamp; changes.append(dict(item_id=id,type='updated',at=stamp,fields=diff))
        existing[id]=r
    return sorted(existing.values(),key=lambda r:(r.get('date') or '',r['id']),reverse=True),changes

def run(offline=False):
    old=read('items.json',[]); incoming=read('curated.json',[]); statuses=[]
    for r in incoming:
        r['source_refs']=r.get('source_refs',[r['source_id']]);r['topics']=r.get('topics',[])
    if not offline:
        with futures.ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(fetch_source,[s for s in SOURCES if s['mode']=='auto']))
        for s,rows,state in results:
            incoming.extend(rows);statuses.append(state)
            print(s['id'],state['state'],len(rows),state.get('error',''),flush=True)
        # Job boards are complete only when not truncated. No inference for sampled feeds/trials.
        for s,rows,state in results:
            if s.get('adapter')=='greenhouse' and state['state']=='ok' and not state['coverage'].get('sampled'):
                ids={r['id'] for r in rows}
                for prev in old:
                    if prev['source_id']==s['id'] and prev['id'] not in ids and prev.get('status')!='NO_LONGER_LISTED':
                        gone={k:v for k,v in prev.items() if k not in ('first_seen','last_seen','updated_at')};gone['status']='NO_LONGER_LISTED';incoming.append(gone)
    items,changes=merge(old,incoming)
    history=read('history.json',[])+changes
    save('items.json',items);save('history.json',history)
    if statuses:
        oldstatus={r['source_id']:r for r in read('status.json',[])}
        for r in statuses:
            previous=oldstatus.get(r['source_id'],{})
            r['last_success']=STAMP if r['state']=='ok' else previous.get('last_success')
            oldstatus[r['source_id']]=r
        save('status.json',list(oldstatus.values()))
    digests=read('digests.json',[])
    daily=[h for h in history if h['at'][:10]==TODAY]
    entry=dict(date=TODAY,generated_at=STAMP,new=len([h for h in daily if h['type']=='new']),updated=len([h for h in daily if h['type']=='updated']),item_ids=list(dict.fromkeys(h['item_id'] for h in daily)),baseline=not bool(old),note='首次建库：新增表示首次收录，不表示今天发生的突破。' if not old else '新增表示首次发现；变更为两次采集间可见字段差异，不代表事件实际发生时间。')
    prior=next((d for d in digests if d['date']==TODAY),None)
    if prior and prior.get('baseline'):entry['baseline']=True;entry['note']=prior['note']
    save('digests.json',[entry]+[d for d in digests if d['date']!=TODAY])
    current=read('status.json',[])
    save('meta.json',dict(schema_version=1,generated_at=STAMP,record_count=len(items),source_count=len(SOURCES),auto_sources=len([s for s in SOURCES if s['mode']=='auto']),healthy_sources=len([s for s in current if s['state']=='ok']),error_sources=len([s for s in current if s['state']=='error']),today_new=entry['new'],today_updated=entry['updated'],timezone='Asia/Shanghai',schedule='每天 08:17（北京时间，GitHub 调度可能延迟）',repository='https://github.com/Alex05250/biopulse',baseline=entry['baseline']))
    print('TOTAL',len(items),'NEW',len(changes),'ERRORS',len([s for s in current if s['state']=='error']))
    if statuses and not any(s['state']=='ok' for s in statuses):raise SystemExit('All sources failed; previous records retained.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');args=p.parse_args();run(args.offline)
