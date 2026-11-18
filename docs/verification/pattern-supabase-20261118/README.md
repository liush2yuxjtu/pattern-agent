# Supabase 目录导入验收 · 2026-11-18

本地 PostgreSQL 17.11 与托管 Supabase PostgreSQL 17.12 均通过验收。[本地 SQL 回读](local-summary.json) · [原件校验](drive-source-check.json) · [托管回执](hosted-summary.json)

- 用项目中已发布的四份目录数据、初版私有 Drive 索引和浙大研究归档生成事务。隔离的 PostgreSQL 容器以内置 `psql -X -v ON_ERROR_STOP=1` 执行迁移和导入。
- 实际回读 62 份原件、31 个发布方入口、62 个 Drive 定位、37,515 条评论、40,438 条线索、63 条人工反馈和 63 份候选意图。查询 `search_feedback` 得到 46 条袖口线索。
- 13 个独立文件、25 个初版压缩包成员和 24 个研究档案成员的源文件 SHA-256 与目录一致。当前 Drive 连接成功查到对应的 19 个文件对象，独立文件大小与索引一致。
- 9 张表开启行级安全。使用 `SET ROLE anon` 和 `SET ROLE authenticated` 查 Drive 定位均返回 SQLSTATE 42501。将一份本地试验意图写成已审核并给定测试目标，重放整批导入后保留该状态和值，线索数量也保持 40,438。
- 容器使用 `--network none`、临时数据目录和随机容器 ID，验收结束后已移除。生成的 SQL 与私有 Drive ID 留在本机的忽略目录。

首轮本地回读发现同一 Drive 文件可对应多个成员。预期值按真实目录修正为 49 个成员，其中 24 个属于研究档案。已抽取实际归档成员并通过哈希核验。

## 托管验收

在 Free 组织的东京区域创建了独立项目，通过已授权的 Supabase 连接器执行迁移与分批导入。9 张表均通过行数与目录字段指纹比对。云端查询得到 46 条袖口线索。使用返回的 Drive 文件 ID 取得 108,836 字节的原始 DXF 文件引用，并成功定位包含 24 份 ZPRJ 的 7z 归档。

项目 SQL 连接可以查询。Postgres 读回显示 9 张表启用行级安全，`anon` 与 `authenticated` 的 schema 使用权均为 false，查询视图以调用者身份执行。给反馈动作外键补上索引后，`EXPLAIN` 在 `action_code = 'raise'` 查询中选用了新索引，性能顾问的未覆盖外键提示已消除。两个迁移文件的版本与托管迁移历史一致。中文交接页已添加并核对新 Agent 访问步骤。

[迁移、准备脚本与查询示例](../../../supabase/README.md) · [Supabase 权限文档](https://supabase.com/docs/guides/database/secure-data)
