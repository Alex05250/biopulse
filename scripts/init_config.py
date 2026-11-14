"""Reproducible public source directory and topic vocabulary. No credentials."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def save(name, value):
    (ROOT / 'data' / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

topics = [
 ('editing','基因编辑','Gene editing','技术','CRISPR|prime editing|base editing|genome editing|基因编辑|先导编辑','关注编辑精度、递送方式、脱靶及长期随访。体外结果不能直接外推到临床。'),
 ('protein','AI 蛋白质设计','Protein design','技术','protein design|protein engineering|de novo protein|diffusion model|RFdiffusion|AlphaFold|蛋白质设计','区分计算预测、湿实验验证与实际药物开发，优先跟踪可重复的功能测定。'),
 ('cgt','细胞与基因治疗','Cell & gene therapy','技术','gene therapy|cell therapy|CAR-T|CAR T|chimeric antigen receptor|AAV|细胞治疗|基因治疗|CGT','同时追踪产品、适应症、临床分期、生产工艺和监管；试验登记不是获批。'),
 ('bci','脑机接口','Brain–computer interface','技术','brain-computer|brain computer|brain-machine|neural interface|Neuralink|脑机接口','区分侵入式与非侵入式，留意受试者数量、长期稳定性与真实功能终点。'),
 ('synbio','合成生物学','Synthetic biology','技术','synthetic biology|metabolic engineering|biomanufacturing|cell-free|strain engineering|合成生物|生物制造','从实验室产率追到中试、规模化成本和供需，不把产能规划等同于实际产量。'),
 ('delivery','递送系统','Delivery systems','技术','lipid nanoparticle|LNP|delivery system|mRNA delivery|递送|脂质纳米','关注组织靶向、免疫原性、剂量与可制造性；递送成功并不等于临床获益。'),
 ('rna','RNA 药物','RNA therapeutics','技术','mRNA|siRNA|antisense|RNA therapeutic|RNA药物|小核酸','追踪序列设计、递送与安全性，并区分疫苗和治疗性应用。'),
 ('adc','ADC 与多抗','ADCs & multispecifics','技术','antibody-drug conjugate|ADC|bispecific|multispecific|双抗|多抗','区分靶点、连接子、载荷、适应症和临床终点，避免只比较标题里的疗效数字。'),
 ('glp1','GLP-1','GLP-1','靶点与管线','GLP-1|GLP1|semaglutide|tirzepatide|司美格鲁肽','关注适应症扩展、剂型、联合机制及供应；非投资建议。'),
 ('tl1a','TL1A','TL1A','靶点与管线','TL1A|TNFSF15','围绕炎症性肠病等研究，按候选产品和临床证据追踪。'),
 ('cd19','CD19','CD19','靶点与管线','CD19|CD-19','按细胞产品与适应症连接研究和临床登记，不自动推断同靶点产品可比。'),
 ('in-vivo','体内 CAR-T','In vivo CAR-T','靶点与管线','in vivo CAR|in-vivo CAR|体内CAR|体内 CAR','关注体内生成的证据、细胞选择性、可控性与随访数据。'),
 ('generate','Generate Biomedicines','Generate Biomedicines','公司与实验室','Generate Biomedicines|Generate:Biomedicines','公开招聘信息仅说明观察时仍在职位列表中，不代表净增员或行业薪资基准。'),
 ('neuralink','Neuralink','Neuralink','公司与实验室','Neuralink','公开职位与研究记录分别保留来源，提及关系不代表技术效果得到验证。'),
 ('regulation','监管与政策','Regulation','政策与待遇','FDA|CDE|NMPA|regulatory|guidance|监管|指导原则|卫生健康|审评','区分征求意见稿、正式文件与实施日期；指导原则发布不意味着任何具体产品已获批。'),
 ('career','岗位与技能','Careers & skills','政策与待遇','scientist|engineer|director|research associate|招聘|岗位|薪酬','薪资保留原币种、周期与适用地区；招聘报价不是实际收入，匿名爆料不作薪资事实。'),
]
save('topics.json', [dict(id=i,name=n,english=e,kind=k,aliases=a.split('|'),note=t) for i,n,e,k,a,t in topics])

sources=[]
def add(id,name,category,url,mode='manual',adapter=None,**kw):
    sources.append(dict(id=id,name=name,category=category,url=url,mode=mode,adapter=adapter,**kw))

add('epmc-nbt','Nature Biotechnology · PubMed 索引','research','https://www.nature.com/nbt/', 'auto','epmc',query='JOURNAL:"Nature biotechnology"',limit=30)
add('nmeth','Nature Methods · RSS','research','https://www.nature.com/nmeth/','auto','rss',feed='https://www.nature.com/nmeth.rss',limit=25)
add('epmc-core','Cell / Science / Nature · PubMed 索引','research','https://pubmed.ncbi.nlm.nih.gov/','auto','epmc',query='(JOURNAL:"Cell" OR JOURNAL:"Science" OR JOURNAL:"Nature") AND (TITLE_ABS:CRISPR OR TITLE_ABS:"protein design" OR TITLE_ABS:"synthetic biology" OR TITLE_ABS:"gene therapy" OR TITLE_ABS:"brain-computer")',limit=30)
for id,name,q in [('editing','基因编辑','CRISPR OR "prime editing" OR "base editing"'),('protein','AI 蛋白质设计','"protein design" OR "de novo protein"'),('synbio','合成生物学','"synthetic biology" OR "biomanufacturing"'),('bci','脑机接口','"brain-computer interface" OR "neural interface"')]:
    add('epmc-'+id,'PubMed · '+name,'research','https://europepmc.org/','auto','epmc',query='('+' OR '.join('TITLE_ABS:'+a for a in q.split(' OR '))+')',limit=18,topic=id)
for id,name in [('synthetic_biology','合成生物学'),('bioinformatics','生物信息学')]:
    add('biorxiv-'+id,'bioRxiv · '+name,'research','https://www.biorxiv.org/','auto','biorxiv',subject=id,limit=90)
add('trials','ClinicalTrials.gov','clinical','https://clinicaltrials.gov/','auto','trials',limit=60)
add('gen','GEN','industry','https://www.genengnews.com/','auto','rss',feed='https://www.genengnews.com/feed/',limit=25)
add('stat','STAT · Biotech','industry','https://www.statnews.com/category/biotech/','auto','rss',feed='https://www.statnews.com/category/biotech/feed/',limit=25,note='只索引公开题录；STAT+ 正文可能需订阅。')
add('fierce','Fierce Biotech','industry','https://www.fiercebiotech.com/','auto','rss',feed='https://www.fiercebiotech.com/rss/xml',limit=25)
add('fda','FDA · Biologics','policy','https://www.fda.gov/vaccines-blood-biologics','auto','rss',feed='https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/biologics/rss.xml',limit=25)
for id,name in [('generatebiomedicines','Generate Biomedicines'),('neuralink','Neuralink')]:
    add('jobs-'+id,name+' · 官方招聘','career','https://boards-api.greenhouse.io/v1/boards/'+id+'/jobs','auto','greenhouse',board=id,company=name,limit=200,topic='generate' if id.startswith('generate') else 'neuralink',note='海外公开职位样本，不代表国内就业或整体行业薪资。')

directory={
 'research': [('medrxiv','medRxiv','https://www.medrxiv.org/','manual'),('bioart','BioArt','https://www.bioart.cn/','manual'),('singularity','奇点网','https://www.geekheal.com/','manual'),('intellectual','知识分子','https://www.zhishifenzi.com/','manual'),('biodiscover','生物探索','https://www.biodiscover.com/','manual'),('inature','iNature','https://www.inature.com/','manual'),('bioskill','生信技能树','https://www.biotrainee.com/','manual'),('scholar','Google Scholar Alerts','https://scholar.google.com/','account'),('stork','文献鸟 Stork','https://www.storkapp.me/','account'),('rabbit','ResearchRabbit','https://www.researchrabbit.ai/','account')],
 'industry': [('endpoints','Endpoints News','https://endpts.com/','paid'),('cube','医药魔方 / NextPharma','https://www.pharmcube.com/','paid'),('insight','丁香园 Insight','https://db.dxy.cn/','paid'),('yaozh','药智网','https://www.yaozh.com/','paid'),('pharnex','摩熵医药','https://www.pharnexcloud.com/','paid'),('synod','同写意','https://www.tongxieyi.com/','manual'),('rd','研发客','https://www.rdpharm.com/','manual'),('eeo','E药经理人','https://www.yyjlr.com/','manual'),('drugtimes','药时代','https://www.drugtimes.cn/','manual'),('vb','动脉网','https://www.vbdata.cn/','manual'),('synbiobeta','SynBioBeta / 生辉相关报道','https://www.synbiobeta.com/','manual'),('hkex','港交所披露易 · 招股书','https://www.hkexnews.hk/','manual'),('sse','上交所 · 科创板披露','https://www.sse.com.cn/','manual'),('hibor','慧博投研','https://www.hibor.com.cn/','account'),('robo','萝卜投研','https://robo.datayes.com/','account'),('eastmoney','东方财富 · 研报','https://data.eastmoney.com/report/','manual')],
 'policy': [('cde','CDE · 指导原则与公示','https://www.cde.org.cn/','manual'),('nmpa','国家药监局','https://www.nmpa.gov.cn/','manual'),('nhc','国家卫生健康委','https://www.nhc.gov.cn/','manual'),('most','科技部 · 申报指南','https://service.most.gov.cn/','manual'),('ndrc','国家发改委','https://www.ndrc.gov.cn/','manual'),('miit','工业和信息化部','https://www.miit.gov.cn/','manual'),('nhsa','国家医保局','https://www.nhsa.gov.cn/','manual'),('chinatrials','中国药物临床试验登记与信息公示','http://www.chinadrugtrials.org.cn/','manual'),('zj','上海张江','https://www.zjpark.com/','manual'),('biobay','苏州 BioBAY','https://www.biobay.com.cn/','manual'),('zgc','中关村生命科学园','https://www.lifesciencepark.com.cn/','manual'),('pingshan','深圳坪山','https://www.szpsq.gov.cn/','manual'),('tianfu','成都天府国际生物城','https://www.shuangliu.gov.cn/','manual'),('guanggu','武汉光谷生物城','https://www.wehdz.gov.cn/','manual')],
 'career': [('liepin','猎聘','https://www.liepin.com/','account'),('linkedin','LinkedIn','https://www.linkedin.com/jobs/','account'),('boss','BOSS 直聘','https://www.zhipin.com/','account'),('dxyjobs','丁香人才','https://www.jobmd.cn/','manual'),('sciencejobs','科学网','https://talent.sciencenet.cn/','manual'),('gaoxiaojob','高校人才网','https://www.gaoxiaojob.com/','manual'),('careerintl','科锐国际 · 薪酬报告','https://www.careerintlinc.com/','manual'),('page','Michael Page · 薪酬报告','https://www.michaelpage.com.cn/','manual'),('hays','Hays · 薪酬指南','https://www.hays-china.cn/','manual'),('kelly','Kelly Services','https://www.kellyservices.com/','manual'),('maimai','脉脉 · 仅作口碑线索','https://maimai.cn/','account'),('red','小红书 · 仅作口碑线索','https://www.xiaohongshu.com/','account'),('offershow','Offershow · 仅作报价线索','https://www.offershow.cn/','account'),('muchong','小木虫','https://muchong.com/','manual'),('zhihu','知乎','https://www.zhihu.com/','account')]
}
for category,rows in directory.items():
    for id,name,url,mode in rows:
        add(id,name,category,url,mode,note='目录入口，尚未自动接入；每次整理须核验原始来源。地址未全部逐一验证。')
save('sources.json',sources)
if not (ROOT/'data/editorial.json').exists():
    save('editorial.json',{'briefs':[],'annotations':{}})
if not (ROOT/'data/curated.json').exists():
    save('curated.json',[])
print(len(sources),'sources;',len(topics),'topics')
