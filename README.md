# BioPulse / 生物科技情报库

**网站：[alex05250.github.io/biopulse](https://alex05250.github.io/biopulse/)**

从科研、产业、临床、政策到职业线索的可追溯索引。页面不需要账号，收藏只保存在当前浏览器。

## 已实现

- GitHub Actions 每日北京时间 **08:17** 采集公开 API / RSS，构建并发布 GitHub Pages。
- 按 DOI、NCT 编号、官方职位 ID 等稳定标识去重，保留首次发现和最近核对时间。
- 比较分期、登记状态、预印本版本、公开薪资等可见字段；保留差异，不虚构历史变化。
- 中英检索、分类 / 节点 / 类型 / 日期筛选、排序、收藏、记录详情与 CSV 导出。
- 每日增量、带出处的 AI 中文精选、可解释的主题网络。
- SQLite、JSON、Markdown 双链三种可移植格式。
- 自适应明暗主题，移动端导航，键盘与减少动态效果偏好支持。

## 覆盖不是全量

自动源与目录源在 `data/sources.json` 中分开配置；实时结果见网页“信源与采集状态”。初版有 16 个自动采集配置，部分来源可能被限制。不得把目录源数称为“已接入信源数”。

| 类型 | 当前自动采集范围 | 主要限制 |
| --- | --- | --- |
| 科研 | Europe PMC / PubMed 题录、Nature Methods RSS、bioRxiv 两个分类 | 35 天检索窗口与单查询上限；预印本 7 天、分类 90 个版本；非全量 |
| 临床 | ClinicalTrials.gov 指定关键词 | 35 天更新窗口、最新 60 条；登记不是审批或疗效结论 |
| 产业 | GEN、STAT Biotech、Fierce RSS | 只索引公开标题；原站可能付费、限流或拒绝访问 |
| 政策 | FDA Biologics RSS（能否成功以状态页为准） | 国内政策通过有原文核对的定时编辑补充，不称为全自动监控 |
| 岗位 | Generate Biomedicines、Neuralink 官方 Greenhouse 职位 | 海外两家公司样本；报价原币种，不推算到手收入 |

中文公众号、付费数据库、国内岗位、薪酬报告和社区口碑目前是**资料入口与定时编辑补充范围**，没有登录凭据或全网抓取。目录链接并非全部逐一核验。不把匿名爆料当事实，不抓临床联系人、求职者或付费全文。

首日“新增”表示首次建库，不是当日新发生的突破。部分文献的日期来自索引，可能是期刊标注日期而不是网络首次出现时间。

## 两层定时

1. **GitHub 云端**：每日 08:17 采集、入库、发布；网页关闭和本机离线不影响该层。GitHub 计划任务可能延迟，并有平台运行限制。长期失败应查看 Actions，不能用原定时间代替实际成功时间。
2. **本聊天的 AI 整理**：每日 20:30 检查云端结果，并按公开原始来源补充中文精选、国内政策与职业线索。依赖本机 Codex 可运行；没有完成的日期显示“自动索引汇总”，不会伪装成已完成 AI 审查。

不需要额外 AI API 密钥。GitHub Pages 是静态网站，不直接在网页上写数据库。AI 整理执行方法见 [RUNBOOK.md](RUNBOOK.md)。

## 本地运行

需要 Python 3.11+（仅标准库）和用于语法检查的 Node.js。

```powershell
python -m unittest discover -s tests -v
python scripts/collect.py
python scripts/build.py
python -m http.server 8786 --bind 127.0.0.1
```

浏览器打开 `http://127.0.0.1:8786/`。仅更新编辑记录时运行 `python scripts/collect.py --offline`，不会触发全网采集。

## 数据文件

- `data/items.json`：结构化索引；不含文章全文。
- `data/history.json`：每次首次入库与字段差异。
- `data/status.json`：逐源成功、失败、样本窗口、最近成功时间。
- `data/curated.json`：经过原文核验的人工 / AI 补充记录。
- `data/editorial.json`：中文标题、解读与每日精选，独立于机器题录。
- `data/library.sqlite`：记录、来源、节点、提及关系、历史、简报与全文检索索引。
- `knowledge/`：可作为 Obsidian 库打开的 Markdown 节点与记录。

英文 FTS 索引使用 SQLite `unicode61`；中文检索以网页的字符串包含匹配为主，不宣称中文分词检索。

## 来源与权利

保留原文链接与出处，原始标题、题录和公共登记信息的权利归原权利人。原创界面与索引工具代码不意味着获得转售、再分发来源全文的权利。AI 解读可能有误，不替代论文阅读、法律意见、医疗建议或投资判断。提及关联不是因果、合作或技术成熟度。
