// Pure application-unit tests, not a substitute for a real-browser interaction test.
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const nodes=new Map();
function el(){return {innerHTML:'',textContent:'',open:false,classList:{add(){},remove(){},toggle(){}},showModal(){this.open=true},setAttribute(){},querySelectorAll(){return []}}}
const storage=new Map();
const ctx=vm.createContext({console,URL,URLSearchParams,Blob,Set,Date,Intl,Number,String,JSON,Math,Promise,setTimeout:()=>0,clearTimeout(){},location:{hash:'#library',href:'https://example.org/#library'},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},window:{},document:{addEventListener(){},querySelector(s){if(!nodes.has(s))nodes.set(s,el());return nodes.get(s)},querySelectorAll(){return []}}});
for(const f of ['app.js','views.js'])vm.runInContext(readFileSync(join(__dirname,'../assets',f),'utf8'),ctx,{filename:f});
vm.runInContext(`
state.topics=[{id:'editing',name:'基因编辑',english:'Editing',kind:'技术',note:'Test note'},{id:'protein',name:'AI 蛋白质设计',english:'Protein design',kind:'技术',note:'Test note'}];
state.sources=[{id:'example',name:'Example',mode:'auto',category:'research',url:'https://example.org/'}];
state.items=[{id:'1',title:'CRISPR trial',summary:'A study',url:'https://example.org/1',date:'2026-11-10',kind:'trial',category:'clinical',source:'Example',source_id:'example',source_refs:['example'],topics:['editing'],first_seen:'2026-11-14T08:00:00+08:00',last_seen:'2026-11-14T08:00:00+08:00',updated_at:'2026-11-14T08:00:00+08:00'},
{id:'2',title:'=SUM(1,1)',summary:'Hiring',url:'https://example.org/2',date:'2026-11-12',kind:'job',category:'career',source:'Example',source_id:'example',source_refs:['example'],topics:['protein'],company:'Example',salary:'$100,000–$120,000',skills:['Python']},
{id:'3',title:'<img src=x onerror=alert(1)>',summary:'Preprint',url:'javascript:alert(1)',date:'2026-11-11',kind:'preprint',category:'research',source:'Example',source_id:'example',source_refs:['example'],topics:['protein']}];
state.meta={record_count:3,healthy_sources:1,auto_sources:1,today_new:3};
state.history=[{item_id:'1',at:'2026-11-14T08:00:00+08:00',type:'new',fields:{}}];
state.digests=[{date:'2026-11-14',item_ids:['1','2','3'],new:3,updated:0,note:'Baseline',generated_at:'2026-11-14T08:00:00+08:00'}];
state.editorial={annotations:{'1':{title_zh:'中文基因编辑',summary:'中文导读'}},briefs:[]};
`,ctx);
const run=code=>vm.runInContext(code,ctx);
assert.equal(run('filtered().length'),3);
assert.equal(run("state.filter.q='基因编辑'; filtered().length"),1);
assert.equal(run("state.filter.q='';state.filter.salary=true;filtered()[0].id"),'2');
assert.equal(run("state.filter.salary=false;state.filter.kind='preprint';filtered().length"),1);
assert(!run('card(state.items[2])').includes('<img'));
assert(run('card(state.items[2])').includes('&lt;img'));
assert.equal(run("safeUrl('javascript:alert(1)')"),'#');
run("state.filter.kind='all';state.filter.salary=true;download=(n,c,t)=>{captured={name:n,content:c,type:t}};toast=()=>{};exportRows()");
assert(run('captured.content').includes("'=SUM(1,1)"),'CSV formulas must be neutralized');
run('state.filter.salary=false;renderGraph()');
assert.equal((nodes.get('#view').innerHTML.match(/class="graph-node /g)||[]).length,2);
run('renderDigest()');assert(nodes.get('#view').innerHTML.includes('2026.11.14 增量简报'));
run('renderSources()');assert(nodes.get('#view').innerHTML.includes('source-table'));
run("showDetail('1')");assert(nodes.get('#detail-body').innerHTML.includes('中文基因编辑'));
assert(nodes.get('#detail').open);
run("toggleSaved('1')");assert.equal(run('state.saved.size'),1);assert(storage.get('biopulse-saved').includes('1'));
run("toggleSaved('1')");assert.equal(run('state.saved.size'),0);
console.log('Client unit checks passed: search, filters, escaping, CSV safety, graph, digest, sources, detail, saved state.');
