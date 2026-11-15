"""Cloud checks for reviewed public brochures. A live PDF is NOT a live vacancy."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]


def check(fetch=None):
    config = json.loads((ROOT/'config/career_sources.json').read_text(encoding='utf-8'))
    previous_path = ROOT/'data/document_status.json'
    previous = {s['id']: s for s in json.loads(previous_path.read_text(encoding='utf-8'))} if previous_path.exists() else {}
    now = datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).isoformat()
    output = []
    for s in config['documents']:
        state = dict(id=s['id'], source_id=s['source_id'], url=s['url'], checked_at=now,
                     state='error', last_success=previous.get(s['id'], {}).get('last_success'),
                     note='只检查已核验简章是否仍可读取及文件是否改变；不验证空缺，不发现新岗位。')
        try:
            if fetch:
                raw = fetch(s['url'])
            else:
                encoded = urllib.parse.quote(s['url'], safe=':/?&=%#')
                req = urllib.request.Request(encoded, headers={'User-Agent': 'BioPulse/1.1 public brochure availability check'})
                with urllib.request.urlopen(req, timeout=22) as response:
                    raw = response.read(8_000_001)
            if not raw.startswith(b'%PDF') or len(raw) > 8_000_000:
                raise ValueError('Not a readable PDF within size limit; no wall bypass')
            sha = hashlib.sha256(raw).hexdigest()
            state.update(sha256=sha, state='unchanged' if sha == s['reviewed_sha256'] else 'changed', last_success=now)
            if state['state'] == 'changed': state['note'] = '简章文件已改变，需要重新阅读；旧岗位字段不可视作本次已核验。'
        except Exception as exc:
            state['error'] = str(exc)[:180]
        output.append(state)
        print('DOCUMENT', s['id'], state['state'])
    previous_path.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return output


if __name__ == '__main__': check()
