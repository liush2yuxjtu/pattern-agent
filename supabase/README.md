# Pattern Agent 的 Supabase 索引

Supabase 用于查询纸样、用户反馈和候选设计意图。查询归档纸样时可以取得 Google Drive 文件 ID、归档成员路径和 SHA-256。通过 Drive 授权打开或下载原件。[公开目录](https://liush2yuxjtu.github.io/pattern-agent/pattern-library/catalog/)

## 在新 Agent 中使用

- 在同一个 ChatGPT 账号下启用已连接的 Google Drive，并提供资料库或交接页链接。当会话可用同一 Google 账号的授权时，可以继续读取有权限的文件。
- 启用 Supabase 连接器后，选定 Pattern Agent 所在的项目。Drive 和 Supabase 各自检查当前连接账号的访问权限。跨客户端连接可使用 Supabase 的项目范围配置。[Supabase MCP 文档](https://supabase.com/docs/guides/getting-started/mcp)
- 在授权的项目 SQL 连接中查询 `pattern_agent`。迁移将数据放在该专用 schema，并为各表启用行级安全。浏览器常用的 `anon` 和 `authenticated` 角色没有该 schema 的访问权限。

## 查询

查询原始 DXF 并定位 Drive 文件。带 SHA-256 的条目代表已归档文件，其他条目保存发布方入口。

```sql
select a.asset_id, a.title, a.sha256, l.file_id, l.archive_member, a.source_url
from pattern_agent.cad_assets a
left join pattern_agent.cad_drive_locations l using (asset_id)
where 'DXF' = any(a.formats) and a.sha256 is not null
order by a.asset_id;
```

从批量线索查袖口需求，结果带原始评论的定位字段和候选量法。

```sql
select garment, candidate, measurement, evidence, source_url, source_index
from pattern_agent.search_feedback
where part_code = 'cuff'
order by review_id
limit 20;
```

`curated_feedback` 保存人工整理的原始网页、观察和量法，`design_intents` 保存对应的候选改法及审核状态。批量评论每条可关联多项 `feedback_signals`。

按实际来源和款式查询。两列 `source_key` 和 `style_key` 一起使用。批量数据的款式键是该来源的商品 ID，人工反馈的款式键是原款式名。计数区分评论和反馈线索。

```sql
select source_key, style_key, style_title, review_count, feedback_count
from pattern_agent.feedback_style_counts
where source_key = 'publisher:Zappos'
order by review_count desc, style_title;

select feedback_id, part, evidence, candidate, source_url, locator
from pattern_agent.feedback_by_source_style
where source_key = 'publisher:Zappos'
  and style_key = 'Dickies Eisenhower 男式夹克'
order by feedback_id;
```

## 导入

首次设置时通过 Supabase 连接器应用 `migrations/` 中的迁移，也可以用安全配置的 PostgreSQL 连接运行下方第一行。后两行准备并导入当前目录数据。Python 依赖 PyYAML，版本与 [编辑器依赖](../web/pattern-library/editor/requirements.txt) 相同。

```sh
cat supabase/migrations/*.sql | psql -X -v ON_ERROR_STOP=1 --single-transaction -f -
python supabase/prepare_catalog.py --output work/pattern-supabase/catalog.sql
psql -X -v ON_ERROR_STOP=1 -f work/pattern-supabase/catalog.sql
```

为归档原件补充 Drive 定位时，可提供 `--drive-index` 指向初版私有原件索引 CSV，并通过 `--research-archive` 给出扩充归档中浙大 7z 文件的 Drive ID 或文件链接。初版链接按 SHA-256 与文件长度匹配。研究档案成员共享一个 Drive 文件 ID。生成的 SQL 放在本机临时目录，含私有 Drive 定位的文件通过授权连接导入。

| 对象 | 当前资料快照 |
| --- | ---: |
| 已归档 CAD | 62 |
| 发布方入口 | 31 |
| 匹配到线索的评论 | 37,515 |
| 批量改版线索 | 40,438 |
| 人工观察及对应候选意图 | 各 63 |
| 提供两项 Drive 参数后的原件定位 | 62 |

导入在单个事务中执行。重复导入按稳定 ID 更新来源字段并保留已填写的候选意图目标与状态。

[源目录](../web/pattern-library/catalog/README.md) · [本地导入验收](../docs/verification/pattern-supabase-20261118/)
