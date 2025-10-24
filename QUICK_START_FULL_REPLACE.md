# 🚀 全量替换功能 - 快速上手

## 问题

> 数据库需要实时保持新数据，需要每次入库前都将旧库完全删除，再导入新的数据

## 解决方案 ✅

**只需添加一个环境变量即可！**

```bash
FULL_REPLACE=true python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
```

---

## 对比

### 之前（增量导入）

```bash
# 更新已有数据，添加新数据，保留旧数据
python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
```

**结果**：
- 旧数据：保留 ✅
- 新数据：更新/添加 ✅
- 已删除的资源：仍然保留 ⚠️

### 现在（全量替换）

```bash
# 删除所有旧数据，导入全新数据
FULL_REPLACE=true python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
```

**结果**：
- 旧数据：删除 ✅
- 新数据：重新导入 ✅
- 已删除的资源：自动清除 ✅

---

## 运行示例

```bash
$ FULL_REPLACE=true python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

⚠️  ============================================================================
⚠️  全量替换模式：将删除所有旧数据，然后导入新数据
⚠️  ============================================================================

📁 找到 3 个文件:
  - eyeuc_list182_merged_20251024.jsonl
  - eyeuc_list193_merged_20251024.jsonl
  - eyeuc_list172_merged_20251024.jsonl

🔌 连接数据库...
✅ 已连接: 162.43.7.144:3306/eyeuc

🗑️  全量替换模式：删除所有旧数据...
  ✅ 清空表: downloads
  ✅ 清空表: versions
  ✅ 清空表: images
  ✅ 清空表: mods
  ✅ 清空表: lists
✅ 所有旧数据已删除

📄 处理: eyeuc_list182_merged_20251024.jsonl
  ✅ 完成: 2300 items

📄 处理: eyeuc_list193_merged_20251024.jsonl
  ✅ 完成: 228 items

📄 处理: eyeuc_list172_merged_20251024.jsonl
  ✅ 完成: 456 items

================================================================================
🎉 导入完成!
================================================================================
  总 items: 2984
  总文件: 3
  用时: 18.5s
  速度: 161.3 items/s
================================================================================

🧹 清理已导入的文件...
  ✅ 删除: eyeuc_list182_merged_20251024.jsonl
  ✅ 删除: eyeuc_list193_merged_20251024.jsonl
  ✅ 删除: eyeuc_list172_merged_20251024.jsonl
✨ 清理完成
```

---

## 定时任务集成

修改 `automation/run_scheduled_crawls.sh`：

```bash
function run_list() {
  local list_id=$1
  local pages=$2
  
  # 爬取最新数据
  bash smart_crawl.sh "$list_id" "$pages"
  
  # 全量替换导入（删除旧数据，导入新数据）
  FULL_REPLACE=true python3 scripts/import_eyeuc_jsonl_to_mysql.py \
    "$(ls -t per_list_output/eyeuc_list${list_id}_*_merged_*.jsonl | head -1)"
}

# 每 6 小时运行，确保数据库始终最新
run_list 182 100
run_list 193 50
run_list 172 35
run_list 93 31
```

---

## 安全机制

- ✅ **事务保护**：失败自动回滚，旧数据保留
- ✅ **快速删除**：使用 `TRUNCATE TABLE`
- ✅ **警告提示**：明确告知用户正在使用全量替换
- ✅ **详细日志**：每个步骤都有清晰的输出

---

## 常用命令

```bash
# 1. 增量导入（默认）
python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

# 2. 全量替换
FULL_REPLACE=true python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

# 3. 全量替换 + 禁用清理（调试用）
FULL_REPLACE=true CLEANUP=false python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

# 4. 在 .env 中永久配置
echo "FULL_REPLACE=true" >> .env
```

---

## 核心优势

| 特性 | 优势 |
|------|------|
| **简单** | 只需添加 `FULL_REPLACE=true` |
| **快速** | 使用 `TRUNCATE TABLE` 快速删除 |
| **安全** | 事务保护，失败自动回滚 |
| **干净** | 数据库始终与爬取结果完全同步 |
| **自动** | 配合定时任务，无需人工干预 |

---

## 详细文档

- **完整指南**: `docs/FULL_REPLACE_GUIDE.md`
- **数据库导入**: `DATABASE_IMPORT_README.md`
- **自动清理**: `docs/AUTO_CLEANUP_GUIDE.md`

---

## 总结

✅ **问题已解决！**

只需在导入命令前添加 `FULL_REPLACE=true`，即可实现：
- 删除所有旧数据
- 导入全新数据
- 数据库实时保持最新

**超级简单，一个环境变量搞定！** 🎉

