'use strict';
// A small, auditable vocabulary, not automatic translation or semantic search.
const SEARCH_ALIASES=[
  ['质检','质量检验','质量控制','quality control','QC'],
  ['质量保证','质量保障','quality assurance','QA'],
  ['工艺','bioprocess','process development'],
  ['生物信息','生信','bioinformatics'],
  ['细胞培养','cell culture'],['蛋白纯化','protein purification'],
  ['技术支持','应用支持','technical support','application support'],
  ['科研助理','研究助理','research assistant','research associate'],
  ['应届','校招','campus','graduate'],
  ['结直肠癌','colorectal'],['胰腺癌','pancreatic'],
  ['抗生素耐药','抗微生物耐药','antimicrobial resistance'],
  ['蛋白质设计','蛋白设计','protein design','de novo protein'],
  ['基因编辑','genome editing','gene editing','CRISPR'],
  ['合成生物','synthetic biology'],['基因治疗','gene therapy'],
  ['细胞治疗','cell therapy'],['脑机接口','brain-computer interface'],
  ['注册','regulatory affairs'],['临床','clinical'],
];
function searchHas(text,term){
  const value=String(text||'').toLowerCase(),q=String(term||'').trim().toLowerCase();
  if(!q)return true;
  if(/^[a-z0-9-]{1,5}$/.test(q))return new RegExp('(^|[^a-z0-9])'+q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?=$|[^a-z0-9])','i').test(value);
  return value.includes(q);
}
function matchesSearch(text,query){
  const q=String(query||'').trim();if(!q)return true;
  if(searchHas(text,q))return true;
  const aliases=SEARCH_ALIASES.find(group=>group.some(term=>term.toLowerCase()===q.toLowerCase()));
  return !!aliases&&aliases.some(term=>searchHas(text,term));
}
