"""Build portable SQLite, explicit mention graph and Obsidian-compatible Markdown."""
import json
import sqlite3
import urllib.parse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
def read(n): return json.loads((DATA/(n+'.json')).read_text(encoding='utf-8'))
def write(p,content):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix=='.md':content=content.rstrip()+'\n'
    p.write_text(content,encoding='utf-8')
def validate_public_sources(items,sources):
    paid={s['id'] for s in sources if s.get('mode')=='paid'}
    known={s['id'] for s in sources}
    for r in items:
        refs=set(r.get('source_refs',[]))|{r['source_id']}
        assert refs<=known,'Unknown source ID'
        assert not refs & paid,'Licensed database records must stay outside the public build; use a separately authorized private library.'
        assert r.get('visibility','public')=='public','Private record in public build'
def build():
    items=read('items');sources=read('sources');topics=read('topics');history=read('history');editorial=read('editorial');meta=read('meta')
    import career
    documents=read('document_status') if (DATA/'document_status.json').exists() else []
    changed={s['source_id'] for s in documents if s['state']=='changed'}
    unavailable={s['source_id'] for s in documents if s['state']=='error'}
    career_items=[{**r,'source_document_changed':r['source_id'] in changed,'source_document_unavailable':r['source_id'] in unavailable} for r in items]
    write(DATA/'career.json',json.dumps(career.build(career_items,meta,documents),ensure_ascii=False,indent=2)+'\n')
    validate_public_sources(items,sources)
    valid={t['id'] for t in topics}; ids={r['id'] for r in items}
    assert len(ids)==len(items),'Duplicate record ID'
    assert all(set(r['topics'])<=valid for r in items),'Unknown topic'
    assert all(r['url'].startswith(('https://','http://')) for r in items),'Unsafe URL'
    graph={'generated_at':meta['generated_at'],'semantics':'mention-only; not causal, partnership or maturity evidence','nodes':[{**t,'count':sum(t['id'] in r['topics'] for r in items)} for t in topics],'edges':[{'source':t,'target':r['id'],'relation':'mentioned_in'} for r in items for t in r['topics']]}
    write(DATA/'graph.json',json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
    target=DATA/'library.sqlite';tmp=DATA/'library.build.sqlite'
    if tmp.exists():tmp.unlink()
    con=sqlite3.connect(tmp)
    con.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE records(id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL, date TEXT, date_basis TEXT, category TEXT, kind TEXT, source_id TEXT, first_seen TEXT, last_seen TEXT, updated_at TEXT, summary TEXT, payload_json TEXT NOT NULL);
        CREATE TABLE sources(id TEXT PRIMARY KEY, name TEXT, category TEXT, mode TEXT, url TEXT, config_json TEXT);
        CREATE TABLE topics(id TEXT PRIMARY KEY, name TEXT, kind TEXT, english TEXT, note TEXT);
        CREATE TABLE record_topics(record_id TEXT REFERENCES records(id),topic_id TEXT REFERENCES topics(id),relation TEXT DEFAULT 'mentioned_in',PRIMARY KEY(record_id,topic_id));
        CREATE TABLE record_sources(record_id TEXT REFERENCES records(id),source_id TEXT REFERENCES sources(id),PRIMARY KEY(record_id,source_id));
        CREATE TABLE changes(id INTEGER PRIMARY KEY,item_id TEXT REFERENCES records(id),type TEXT,at TEXT,fields_json TEXT);
        CREATE TABLE briefs(date TEXT PRIMARY KEY, payload_json TEXT);
        CREATE INDEX record_date ON records(date DESC);
        CREATE INDEX record_category ON records(category);
        CREATE INDEX topic_record ON record_topics(topic_id);
        CREATE VIRTUAL TABLE record_search USING fts5(id UNINDEXED,title,summary,tokenize='unicode61');
    ''')
    con.executemany('INSERT INTO sources VALUES (?,?,?,?,?,?)',[(s['id'],s['name'],s['category'],s['mode'],s['url'],json.dumps(s,ensure_ascii=False)) for s in sources])
    con.executemany('INSERT INTO topics VALUES (?,?,?,?,?)',[(t['id'],t['name'],t['kind'],t['english'],t['note']) for t in topics])
    for r in items:
        con.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',[r.get(k) for k in ['id','title','url','date','date_basis','category','kind','source_id','first_seen','last_seen','updated_at','summary']]+[json.dumps(r,ensure_ascii=False)])
        con.execute('INSERT INTO record_search VALUES (?,?,?)',(r['id'],r['title'],r['summary']))
        con.executemany('INSERT INTO record_topics(record_id,topic_id) VALUES (?,?)',[(r['id'],t) for t in r['topics']])
        con.executemany('INSERT INTO record_sources VALUES (?,?)',[(r['id'],s) for s in r['source_refs']])
    con.executemany('INSERT INTO changes(item_id,type,at,fields_json) VALUES (?,?,?,?)',[(h['item_id'],h['type'],h['at'],json.dumps(h['fields'],ensure_ascii=False)) for h in history])
    con.executemany('INSERT INTO briefs VALUES (?,?)',[(b['date'],json.dumps(b,ensure_ascii=False)) for b in editorial.get('briefs',[])])
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not con.execute('PRAGMA foreign_key_check').fetchall()
    con.commit();con.close();tmp.replace(target)
    annotations=editorial.get('annotations',{})
    record_dir=(ROOT/'knowledge'/'records').resolve()
    assert record_dir.is_relative_to(ROOT.resolve())
    # Only generated records whose IDs were explicitly removed from the index are pruned.
    if record_dir.exists():
        for p in record_dir.glob('*.md'):
            if p.stem not in ids:p.unlink()
    for r in items:
        a=annotations.get(r['id'],{})
        body='# '+(a.get('title_zh') or r['title'])+'\n\n'+(r['title']+'\n\n' if a.get('title_zh') else '')+'- 原站日期：'+str(r.get('date') or '未提供')+'（'+r['date_basis']+'）\n- 类型：'+r['kind']+'\n- 首次收录：'+r['first_seen']+'\n- 来源：['+r['source']+']('+r['url']+')\n- 记录 ID：'+r['id']+'\n\n'+(a.get('summary') or r['summary'])+'\n\n'+('边界：'+a['caution']+'\n\n' if a.get('caution') else '')+'## 关联节点（仅提及，不代表因果）\n\n'+' '.join('[['+next(t['name'] for t in topics if t['id']==id)+']]' for id in r['topics'])+'\n'
        fields=[('来源范围',r.get('market')),('职级/类型',r.get('job_level')),('公开报价',r.get('salary')),('币种',r.get('salary_currency')),('周期',r.get('salary_period')),('税口径',r.get('salary_tax')),('薪酬包含项',r.get('salary_inclusions')),('核验时间',r.get('verified_at')),('核验范围',r.get('verification_scope')),('核验页面',r.get('verified_url'))]
        details=['- '+k+'：'+str(v) for k,v in fields if v]
        if details:body+='\n## 来源与口径\n\n'+'\n'.join(details)+'\n'
        write(ROOT/'knowledge'/'records'/(r['id']+'.md'),body)
    for t in topics:
        related=[r for r in items if t['id'] in r['topics']]
        links=[]
        for r in related:
            links.append('- [['+r['id']+'|'+(annotations.get(r['id'],{}).get('title_zh') or r['title']).replace('|','／')+']] · '+str(r.get('date') or '日期未提供')+' · '+r['kind'])
        others=[other for other in topics if other['id']!=t['id'] and any(other['id'] in r['topics'] for r in related)]
        write(ROOT/'knowledge'/(t['name']+'.md'),'# '+t['name']+'\n\n'+t['english']+' · '+t['kind']+'\n\n'+t['note']+'\n\n## 提及关联（不是因果）\n\n'+' '.join('[['+o['name']+']]' for o in others)+'\n\n## 相关情报 / '+str(len(related))+' 条\n\n'+'\n'.join(links)+'\n')
    write(ROOT/'knowledge'/'README.md','# BioPulse 知识网络\n\n可把整个 knowledge 文件夹作为 Obsidian 库打开。双链表示共同提及，不代表因果、合作或疗效。文件无插件、无脚本。\n\n'+ '\n'.join('- [['+t['name']+']] · '+t['kind'] for t in topics)+'\n\n数据构建时间：'+meta['generated_at']+'\n')
    for d in read('digests'):
        b=next((b for b in editorial.get('briefs',[]) if b['date']==d['date']),None)
        text='# BioPulse / '+d['date']+' 增量简报\n\n'+d['note']+'\n\n首次收录 '+str(d['new'])+'；字段更新 '+str(d['updated'])+'。\n\n'
        if b:
            text+=b['intro']+'\n\n'
            for p in b['points']:
                source=next((r['url'] for r in items if r['id']==p.get('item_id')),p.get('url',''))
                text+='## '+p['title']+'\n\n'+p['summary']+'\n\n边界：'+p['caution']+'\n\n[核对原文]('+source+')\n\n'
        else:text+='自动索引汇总，尚未进行 AI 评估。\n\n'
        write(ROOT/'knowledge'/'digests'/(d['date']+'.md'),text)
    # Static deploy output contains only public assets, not collector code or local state.
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    import shutil
    shutil.copy2(ROOT/'index.html',dist/'index.html')
    for folder in ('assets','data','knowledge'):
        shutil.copytree(ROOT/folder,dist/folder,dirs_exist_ok=True)
    write(dist/'.nojekyll','')
    print('Built',len(items),'records,',len(topics),'nodes,',len(graph['edges']),'explicit mentions; SQLite integrity OK')

if __name__=='__main__':build()
