'use strict';
const CAREER_FAMILIES={wetlab:'实验研发',bioinformatics:'生信 / 算法',bioprocess:'生产 / 工艺',quality:'质量 QA / QC',clinical:'临床 / 医学',regulatory:'注册 / 法规',applications:'技术支持 / 应用',sales:'销售 / 市场',other:'其他 / 待核验'};
const CAREER_AUDIENCES={campus:'应届校招',junior:'初级社招',experienced:'资深社招',academic:'博士后 / 高校序列',unknown:'经验待核验'};
const CAREER_DEGREES={college:'大专',bachelor:'本科',master:'硕士',phd:'博士',unknown:'未明确'};
const CAREER_FRESHNESS={reviewed:'近30天核对过来源',stale:'超过30天 / 核验时间不明',needs_review:'来源变化 / 不可读 · 待复核',expired:'原文截止日期已过',closed:'原列表已不再列出'};
const CAREER_LEVELS={document_review:'已读原版简章',full_jd:'已读完整JD',list_only:'仅列表观察',api_list:'官方接口在列',unknown:'核验范围不明'};
const careerFilter={q:'',city:'all',degree:'all',audience:'target',family:'all',fresh:'recent',salary:false,saved:false,page:1};
const watchBaselines=storageGet('biopulse-job-watch',{});
function careerProfile(r){
  const p={audience:'unknown',education_min:'unknown',education_allowed:[],cities:[],role_family:'other',freshness:'stale',vacancy_status:'unconfirmed',verification_level:'unknown',quote:{exclusion:[]},...(state.career?.profiles?.[r.id]||{})};
  const stamp=p.verified_at||r.verified_at||r.source_observed_at;
  const age=stamp?Math.max(0,Math.floor((Date.now()-new Date(stamp).getTime())/864e5)):Infinity;
  if(p.freshness==='reviewed'&&age>30){p.freshness='stale';p.vacancy_status='unconfirmed'}
  const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date());
  if(p.application_deadline&&p.application_deadline.slice(0,10)<today){p.freshness='expired';p.vacancy_status='closed'}
  return p;
}
function cnJobRows(){return state.items.filter(r=>r.kind==='job'&&r.market==='CN')}
function careerCorpus(r){const p=careerProfile(r);return [r.title,r.company,r.summary,r.location,r.major_requirements,p.education_text,p.experience_text,...(r.skills||[])].join(' ')}
function filteredCareer(){
  const f=careerFilter;
  return cnJobRows().filter(r=>{const p=careerProfile(r);return (!f.saved||state.saved.has(r.id))&&
    (f.audience==='all'||(f.audience==='target'?['campus','junior'].includes(p.audience):p.audience===f.audience))&&
    (f.city==='all'||p.cities.includes(f.city))&&(f.degree==='all'||p.education_allowed.includes(f.degree))&&
    (f.family==='all'||p.role_family===f.family)&&(f.fresh==='all'||(f.fresh==='recent'?p.freshness==='reviewed':p.freshness===f.fresh))&&
    (!f.salary||!!p.quote.numeric)&&matchesSearch(careerCorpus(r),f.q)
  }).sort((a,b)=>String(careerProfile(b).verified_at||'').localeCompare(String(careerProfile(a).verified_at||''))||a.company.localeCompare(b.company));
}
function careerSelect(id,label,choices,current){return '<label class="career-field"><span>'+label+'</span><select id="career-'+id+'" data-career-filter="'+id+'" aria-label="'+label+'">'+choices.map(([value,name])=>'<option value="'+esc(value)+'" '+(value===current?'selected':'')+'>'+esc(name)+'</option>').join('')+'</select></label>'}
function careerControls(){
  const f=careerFilter,cities=[...new Set(cnJobRows().flatMap(r=>careerProfile(r).cities))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
  return '<div class="career-toolbar"><div class="career-query"><label for="career-query">职位、企业、专业或技能</label><input id="career-query" data-career-filter="q" type="search" placeholder="如 质检、生信、细胞培养、注册…" value="'+esc(f.q)+'" autocomplete="off"></div><div class="career-filters">'+
    careerSelect('city','工作城市',[['all','全部城市'],...cities.map(v=>[v,v])],f.city)+
    careerSelect('degree','简章接受的学历',[['all','本科 / 硕士优先，不限学历筛选'],['bachelor','接受本科'],['master','接受硕士'],['college','接受大专'],['phd','接受博士']],f.degree)+
    careerSelect('family','岗位方向',[['all','全部方向'],...Object.entries(CAREER_FAMILIES)],f.family)+
    careerSelect('audience','求职阶段',[['target','应届 + 初级（默认）'],...Object.entries(CAREER_AUDIENCES),['all','全部中国岗位']],f.audience)+
    careerSelect('fresh','来源核验时间',[['recent','近30天核对过来源'],['all','包含历史 / 待核验'],['stale','超过30天 / 时间不明'],['needs_review','来源已改变'],['expired','已过截止日期'],['closed','已不再列出']],f.fresh)+
    '<button class="button secondary" data-career-reset>重置</button></div><div class="career-toggles"><label><input type="checkbox" data-career-filter="salary" '+(f.salary?'checked':'')+'> 仅看单岗位公开数字报价</label><label><input type="checkbox" data-career-filter="saved" '+(f.saved?'checked':'')+'> 仅看已收藏中国岗位</label><span>常见中英词可互搜；不宣称自动翻译或全量收录。</span></div></div>';
}
function careerStats(){const c=state.career?.counts||{},target=cnJobRows().filter(r=>['campus','junior'].includes(careerProfile(r).audience));return '<div class="career-stats"><div><span>应届 / 初级线索</span><strong>'+target.length+'<small>条</small></strong><p>不是已确认空缺数</p></div><div><span>对应雇主</span><strong>'+new Set(target.map(r=>r.employer_id||r.company)).size+'<small>家</small></strong><p>不是行业代表性样本</p></div><div><span>单岗位数字报价</span><strong>'+target.filter(r=>careerProfile(r).quote.numeric).length+'<small>条</small></strong><p>未知不估算、不代填</p></div><div><span>确认仍在列</span><strong>'+target.filter(r=>careerProfile(r).vacancy_status==='listed').length+'<small>条</small></strong><p>简章可读不等于仍在招</p></div></div>'}
function careerTitle(salary=false){return pageHeading('CHINA / EARLY CAREER',salary?'先对齐口径，再比较薪资。':'从第一份工作，开始看清选择。','面向生命科学本科 / 硕士应届与初级岗位。国内、海外、资深、高校序列分开。', '<a class="button secondary" href="'+(salary?'#career':'#salary')+'">'+(salary?'返回国内求职':'查看薪资证据')+' '+icon('arrow')+'</a>')}
function watchSnapshot(r){return JSON.stringify([r.salary,r.salary_min,r.salary_max,r.status,r.location,r.cities,r.education_text,r.experience_text,r.application_deadline,r.hiring_batch])}
function watchChanged(r){const b=watchBaselines[r.id];return !!b&&b.snapshot!==watchSnapshot(r)}
function captureJobWatch(r){if(!r||r.kind!=='job')return;watchBaselines[r.id]={snapshot:watchSnapshot(r),at:new Date().toISOString()};try{localStorage.setItem('biopulse-job-watch',JSON.stringify(watchBaselines))}catch{}}
function careerCard(r){
  const p=careerProfile(r),ref=r.compensation_reference&&state.items.find(x=>x.id===r.compensation_reference),changed=watchChanged(r);
  return '<article class="career-card"><div class="career-card-top"><span class="badge outline">'+esc(CAREER_AUDIENCES[p.audience])+'</span><span class="badge '+(p.freshness==='reviewed'?'':'warn')+'">'+esc(p.vacancy_status==='listed'?'采集时官方在列':p.freshness==='reviewed'?'空缺待确认':CAREER_FRESHNESS[p.freshness])+'</span>'+(changed?'<span class="badge warn">收藏后字段有变化</span>':'')+'</div><p class="career-company">'+esc(r.company||'企业未披露')+'</p><h2><button class="title-button" data-open="'+r.id+'">'+esc(r.title)+'</button></h2><div class="career-pay"><strong>'+esc(r.salary||'本岗位薪资未公开')+'</strong>'+(ref?'<button class="text-link" data-open="'+ref.id+'">另有整批校招参考 ↗</button>':'')+'</div><dl class="career-facts"><div><dt>城市</dt><dd>'+esc(p.cities.join(' / ')||r.location||'待确认')+'</dd></div><div><dt>学历</dt><dd>'+esc(p.education_text||'未明确')+'</dd></div><div><dt>经验 / 批次</dt><dd>'+esc(p.hiring_batch||p.experience_text||'未明确')+'</dd></div><div><dt>方向</dt><dd>'+esc(CAREER_FAMILIES[p.role_family])+'</dd></div></dl>'+(r.major_requirements?'<p class="career-majors">专业要求：'+esc(r.major_requirements)+'</p>':'')+'<p class="career-scope">'+esc(CAREER_LEVELS[p.verification_level])+' · 核对于 '+localDate(p.verified_at)+'<br>'+esc(p.vacancy_status==='unconfirmed'?'尚未确认当前空缺、截止日期及实际 offer。':'在列状态也不保证面试或录用。')+'</p><div class="career-card-actions"><button class="button secondary" data-open="'+r.id+'">查看证据与详情</button><button class="button ghost" data-save="'+r.id+'" aria-pressed="'+state.saved.has(r.id)+'">'+(state.saved.has(r.id)?'已收藏':'收藏并追踪')+'</button><a class="career-original" href="'+safeUrl(r.url)+'" target="_blank" rel="noopener noreferrer">原文 ↗</a></div>'+(state.saved.has(r.id)&&!watchBaselines[r.id]?'<button class="button ghost" data-watch-sync="'+r.id+'">为已有收藏建立当前追踪基线</button>':'')+'</article>';
}
function careerScope(){return '<div class="career-scope-bar"><span class="career-scope-mark">说明</span><p><b>近30天核对过来源 ≠ 岗位仍在招聘。</b> 企业原版校招简章由高校就业网公开托管；未向招聘方确认的空缺明确标注。整批年薪范围不分摊给每个岗位。</p></div>'}
function renderCareer(salary=false){
  $('#view').innerHTML=careerTitle(salary)+careerStats()+careerScope()+careerControls()+'<div id="career-results"></div>'+(salary?'':careerPreparation())+careerDocumentHealth();
  updateCareerResults(salary);
}
function updateCareerResults(salary=location.hash.startsWith('#salary')){
  const rows=filteredCareer();
  if(salary){$('#career-results').innerHTML=salaryEvidence(rows);return}
  const pages=Math.max(1,Math.ceil(rows.length/12));careerFilter.page=Math.min(careerFilter.page,pages);
  const saved=cnJobRows().filter(r=>state.saved.has(r.id)),changed=saved.filter(watchChanged);
  $('#career-results').innerHTML='<div class="career-result-head"><p aria-live="polite">当前筛选 <b>'+rows.length+'</b> 条中国岗位线索 · '+new Set(rows.map(r=>r.employer_id||r.company)).size+' 家雇主</p><button class="button secondary" data-career-export>'+icon('download')+' 导出当前岗位</button></div>'+(saved.length?'<div class="scope-notice">已收藏 '+saved.length+' 个中国岗位；'+changed.length+' 个与本浏览器追踪基线不同。<button class="text-link" data-career-watch>只看收藏</button>　只在再次打开网站时比较，不会后台监控或发送通知。</div>':'')+
    (rows.length?'<div class="career-grid">'+rows.slice((careerFilter.page-1)*12,careerFilter.page*12).map(careerCard).join('')+'</div><div class="pagination"><span>第 '+careerFilter.page+' / '+pages+' 页 · 不含未核验的应届适用性推断</span><div><button class="button secondary" data-career-page="-1" '+(careerFilter.page<=1?'disabled':'')+'>上一页</button><button class="button secondary" data-career-page="1" '+(careerFilter.page>=pages?'disabled':'')+'>下一页</button></div></div>':'<div class="career-empty"><h2>这组条件还没有足够的已核验线索。</h2><p>没有结果不代表没有岗位。可放宽城市或切换“包含历史 / 待核验”；薪资未公开的岗位不会被估算后填入。</p><button class="button secondary" data-career-reset>恢复默认筛选</button></div>');
}
function salaryEvidence(rows){
  const ids=new Set(rows.map(r=>r.id)),groups=(state.career?.groups||[]).filter(g=>g.item_ids.every(id=>ids.has(id))),quotes=rows.filter(r=>careerProfile(r).quote.numeric);
  const references=state.items.filter(r=>r.market==='CN'&&r.salary_scope==='campaign');
  return '<section class="salary-summary"><div><div class="eyebrow">EVIDENCE, NOT AVERAGES</div><h2>'+((groups.some(g=>g.sufficient))?'已有可对齐的岗位报价组':'暂不输出“应届行业平均工资”。')+'</h2><p>当前筛选有 '+rows.length+' 条岗位线索、'+quotes.length+' 条单岗位数字报价。只有同城市、方向、学历集合、求职阶段、雇主类型、周期、税口径及工资构成一致，且至少 <b>5 个岗位 / 3 家企业</b>，才展示报价上下限的中位数。这个门槛是本工具的保守展示规则，不代表统计代表性。</p></div><span class="salary-evidence-count">'+quotes.length+'<small>可见单岗报价</small></span></section>'+
    (groups.length?'<div class="salary-group-grid">'+groups.map(g=>'<article class="side-panel"><div class="eyebrow">'+esc(g.city)+' / '+esc(CAREER_FAMILIES[g.role_family])+'</div><h3>'+g.count+' 个岗位 · '+g.employers+' 家企业</h3><p>'+esc(g.education_allowed.map(v=>CAREER_DEGREES[v]).join(' / '))+' · '+esc(g.period==='month'?'原文月报价':'原文年报价')+' · '+esc(g.tax==='pre_tax'?'税前':'税后')+' · '+esc(g.component==='base'?'基本工资':'综合总包')+'</p>'+(g.sufficient?'<strong class="salary-range">¥'+fmt(g.median_lower)+'–'+fmt(g.median_upper)+'</strong>':'<strong>样本不足，不计算中位数</strong>')+'<p>'+esc(g.note)+'</p></article>').join('')+'</div>':'')+
    '<div class="section-head"><div><h2>招聘批次的薪酬参考</h2><p>单独保存，不计成多个岗位报价；不能拿来推断每个职位、城市或学历的收入。</p></div></div><div class="salary-reference-grid">'+(references.length?references.map(r=>'<article class="salary-reference"><span class="badge warn">整批校招参考 · 非单岗位报价</span><h3>'+esc(r.company)+'</h3><strong>'+esc(r.salary)+'</strong><p>'+esc(r.salary_inclusions)+'</p><p>税口径：'+esc(r.salary_tax)+'。不推算固定月薪，不叠加已经包含的补贴。</p><button class="button secondary" data-open="'+r.id+'">查看简章证据</button></article>').join(''):'<p>尚无经原文核对的批次薪酬参考。</p>')+'</div>'+
    '<div class="section-head"><div><h2>当前筛选的单岗位数字报价</h2><p>招聘报价 ≠ offer ≠ 实际到手；缺失字段会影响可比性。</p></div><button class="button secondary" data-career-export>导出岗位与缺失口径</button></div>'+(quotes.length?'<div class="career-grid">'+quotes.map(careerCard).join('')+'</div>':'<div class="scope-notice">这些目标岗位目前没有公开到单岗位的完整数字报价。保留这个缺口，比用高管、博士后或海外收入凑一个“本科起薪”更可靠。</div>')+
    '<section class="career-method"><h2>拿到报价时，先核对这六件事</h2><ol><li>这是基本工资，还是包含绩效、补贴、奖金的总包？</li><li>明确税前 / 税后、币种和月薪 / 年薪；不要把实习日薪与转正月薪混比。</li><li>“13薪 / 14薪”是否保证？年终奖的条件和发放时间是什么？</li><li>试用期工资、合同主体、劳务派遣与正式雇佣是否明确？</li><li>五险一金缴纳基数、倒班、加班与住宿条件需单独问清，不折算成虚构到手数。</li><li>同城市、学历、经验和方向比较；招聘机构参考与企业岗位报价不能混成行业均值。</li></ol></section>';
}
function careerPreparation(){
  const guides=[['wetlab','实验研发','用一页项目复盘说明实验目的、对照、重复、异常处理与个人贡献。'],['quality','质量 QA / QC','先理解SOP、原始记录、偏差与CAPA；具体检测方法以每份JD为准。'],['bioprocess','生产 / 工艺','整理一次放大或流程实验经历；面试前确认倒班、生产环境与安全要求。'],['bioinformatics','生信 / 算法','准备可复现的小项目，说明数据来源、方法选择、验证集与局限。'],['regulatory','注册 / 法规','练习把一个公开产品的注册路径和资料目录讲清；不把读过法规当实务经验。'],['applications','技术支持 / 应用','练习向非同专业的人解释一种检测方法，并给出排错思路。']];
  return '<section class="career-preparation"><div class="section-head"><div><h2>从岗位方向，倒推准备材料</h2><p>下面是本站的准备建议，不是统计出的雇主硬性门槛；专业要求和技能要求分开保存。</p></div></div><div class="career-guide-grid">'+guides.map(([id,title,text])=>'<article><span>'+esc(title)+'</span><p>'+text+'</p><button class="text-link" data-career-family="'+id+'">看这个方向的岗位 ↗</button></article>').join('')+'</div></section>';
}
function exportCareer(){
  const rows=filteredCareer();if(!rows.length){toast('当前没有可导出的中国岗位');return}
  const cell=v=>'"'+String(v??'').replace(/^[\s]*[=+@-]/,"'$&").replaceAll('"','""')+'"';
  const head=['岗位','企业','城市','方向','阶段','学历原文','经验原文','批次','毕业时间要求','薪资原文','币种','周期','税口径','构成','报价范围','原文核验时间','核验级别','空缺是否确认','截止日期','原文','缺失/排除原因'];
  const data=rows.map(r=>{const p=careerProfile(r);return [r.title,r.company,p.cities.join('/'),CAREER_FAMILIES[p.role_family],CAREER_AUDIENCES[p.audience],p.education_text,p.experience_text,p.hiring_batch,p.graduation_window,r.salary,r.salary_currency,r.salary_period,r.salary_tax,r.salary_inclusions,r.salary_scope||'job',p.verified_at,CAREER_LEVELS[p.verification_level],p.vacancy_status==='listed'?'采集时在列':'未确认 / 需复核',p.application_deadline,r.url,(p.quote.exclusion||[]).join('；')]});
  download('BioPulse-中国求职-'+new Date().toISOString().slice(0,10)+'.csv','\ufeff'+[head,...data].map(r=>r.map(cell).join(',')).join('\r\n'),'text/csv;charset=utf-8');
}
function careerEvidenceFacts(r){if(r.market!=='CN'||r.kind!=='job')return [];const p=careerProfile(r);return [['求职阶段',CAREER_AUDIENCES[p.audience]],['阶段判断依据',p.audience_basis],['学历原文',p.education_text],['经验原文',p.experience_text],['招聘批次',p.hiring_batch||'未明确'],['毕业窗口',p.graduation_window||'未明确'],['空缺核验',p.vacancy_status==='listed'?'采集时官方在列，仍须向雇主确认':'只核对到来源；当前空缺未确认'],['来源核验等级',CAREER_LEVELS[p.verification_level]],['截止日期',p.application_deadline||'原文未提供，不能认为长期有效'],['证据页码',r.evidence_pages?.join('、')||'见来源'],['专业要求',r.major_requirements||'未核验 / 未提供']]}
function careerDocumentHealth(){const checks=state.career?.document_status||[];if(!checks.length)return '';return '<section class="career-method"><h2>已知招聘简章的持续检查</h2><p class="detail-footnote">只检查这些PDF是否可读取及文件是否改变，不发现新岗位，也不延长人工阅读时间或确认招聘空缺。</p>'+checks.map(s=>'<div class="graph-connection"><span>'+esc(state.sources.find(v=>v.id===s.source_id)?.name||s.source_id)+'</span><span class="badge '+(s.state==='unchanged'?'outline':'warn')+'">'+esc(({unchanged:'文件可读 · 内容未变',changed:'文件改变 · 需重读',error:'读取失败 · 待复核'})[s.state]||s.state)+'</span><small>'+localTime(s.checked_at)+'</small></div>').join('')+'</section>'}
function collectionFreshness(){const stamp=state.meta.last_collection_at;if(!stamp)return '<div class="scope-notice">尚无可确认的最近云端采集时间；网页构建时间不等于数据核验时间。</div>';const hours=(Date.now()-new Date(stamp).getTime())/36e5;return hours>36?'<div class="scope-notice">云端采集距今已超过36小时（最近 '+localTime(stamp)+'）。当前显示历史快照，不等于期间没有更新。<a class="text-link" href="#sources">查看异常与覆盖</a></div>':''}
document.addEventListener('input',e=>{if(e.target.dataset.careerFilter==='q'){careerFilter.q=e.target.value;careerFilter.page=1;updateCareerResults()}});
document.addEventListener('change',e=>{const key=e.target.dataset.careerFilter;if(key&&key!=='q'){careerFilter[key]=['salary','saved'].includes(key)?e.target.checked:e.target.value;careerFilter.page=1;if(key==='saved'&&careerFilter.saved){careerFilter.audience='all';careerFilter.fresh='all';renderCareer(location.hash.startsWith('#salary'))}else updateCareerResults()}});
document.addEventListener('click',e=>{const b=e.target.closest('button,a');if(!b)return;
  if(b.hasAttribute('data-career-reset')){Object.assign(careerFilter,{q:'',city:'all',degree:'all',audience:'target',family:'all',fresh:'recent',salary:false,saved:false,page:1});renderCareer(location.hash.startsWith('#salary'))}
  if(b.dataset.careerPage){careerFilter.page+=Number(b.dataset.careerPage);updateCareerResults();$('#career-results').scrollIntoView({block:'start'})}
  if(b.hasAttribute('data-career-export'))exportCareer();
  if(b.hasAttribute('data-career-watch')){careerFilter.saved=true;careerFilter.audience='all';careerFilter.fresh='all';renderCareer()}
  if(b.dataset.careerFamily){careerFilter.family=b.dataset.careerFamily;careerFilter.page=1;renderCareer();$('#career-results').scrollIntoView({block:'start'})}
  if(b.dataset.watchSync){captureJobWatch(state.items.find(r=>r.id===b.dataset.watchSync));updateCareerResults()}
});
