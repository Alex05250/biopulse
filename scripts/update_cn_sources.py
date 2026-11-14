"""Register independently reviewed CN sources without inventing an automatic feed."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def update():
    p=ROOT/'data/sources.json'
    sources=json.loads(p.read_text(encoding='utf-8'))
    updates={
      'insight':dict(url='https://db.dxy.cn/v5/home/open',docs_url='https://db.dxy.cn/v5/home/document',note='官方 API 文档已读：需平台发放 App ID 与 SecretKey，并按文档签名。普通订阅是否含 API、额度和公开再分发权限须另行确认；尚未授权联调。'),
      'cube':dict(note='专业数据库尚未授权连接；不能把可公开阅读的资讯与 NextPharma 结构化专业库混为一谈。需分别确认 API/Data Feed 权限与可公开字段。'),
      'bioart':dict(url='https://mp.weixin.qq.com/',note='公众号目录，不把未经核实的同名独立域名当作官方站。公开文章检索归 wechat-public，须逐篇核验账号与发布时间。'),
      'inature':dict(url='https://mp.weixin.qq.com/',note='公众号目录；独立站归属未核实。公开文章须逐篇核验发布账号和原始论文。'),
      'page':dict(name='Michael Page · 中国公开岗位',category='career',url='https://www.michaelpage.com.cn/jobs/%E7%94%9F%E5%91%BD%E7%A7%91%E5%AD%A6/healthcare-pharmaceutical',mode='review',note='公开列表已核验，可读取部分中国岗位与人民币年薪；未发现页面提供 RSS。由 20:30 本机定时核验补充，不是云端全量抓取。客户未具名时不推断公司；列表仍显示不保证仍有空缺。'),
      'careerintl':dict(mode='review',url='https://www.careerintlinc.com/report/3168.html',note='官方公开报告解读已核验。报告参考区间不等于真实工资；摘要未明确的周期、地区和税口径保留未知，不自行推算年薪。')
    }
    for s in sources:
        if s['id'] in updates:s.update(updates[s['id']])
    new=[
      dict(id='sustech-zhangxm',name='南方科技大学 · 官方科研岗位',category='career',mode='review',adapter=None,url='https://faculty.sustech.edu.cn/?cat=11&go=2&iscss=1&snapid=1&tagid=zhangxm',note='官方教师招聘页已核验；高校科研序列与博士后样本，不代表药企或全行业薪资。保留含补助与税前口径，发布时间未提供则留空。'),
      dict(id='wechat-public',name='公众号 · 公开检索线索',category='research',mode='review',adapter=None,url='https://mp.weixin.qq.com/',note='按关键词定时发现公开文章链接。当前测试文章遇微信滑块，未读正文、未核验账号与发布时间，只收录 lead；不绕过验证码，不代表全量订阅。')
    ]
    ids={s['id'] for s in sources}
    sources.extend(s for s in new if s['id'] not in ids)
    p.write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return sources

if __name__=='__main__':print('CN source registry:',len(update()))
