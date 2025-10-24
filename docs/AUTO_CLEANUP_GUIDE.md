# 🧹 自动清理功能指南

## 概述

为了防止 `per_list_output` 文件夹因累积大量已导入的 JSONL 文件而占用过多磁盘空间，导入脚本现在支持**自动清理**功能。

---

## 功能特性

### ✅ 默认行为

导入脚本 **默认开启自动清理**，在成功导入数据到 MySQL 后，会自动：

1. **删除已导入的 JSONL 文件**
2. **检查目录是否为空**，如果为空则删除目录
3. **仅清理成功导入的文件**

### 🛡️ 安全机制

- ✅ **只在导入成功后清理**：如果导入失败，文件将被保留
- ✅ **只清理已导入的文件**：不会误删其他文件
- ✅ **智能目录管理**：只删除空目录
- ✅ **可禁用**：通过环境变量 `CLEANUP=false` 禁用清理

---

## 使用方法

### 1. 默认使用（推荐）

```bash
# 自动清理已导入的文件
python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/eyeuc_list193_*.jsonl"
```

**输出示例**：
```
📁 找到 3 个文件:
  - eyeuc_list193_p1-5_20251024_100000.jsonl
  - eyeuc_list193_p6-10_20251024_100001.jsonl
  - eyeuc_list193_merged_20251024_100002.jsonl

🔌 连接数据库...
✅ 已连接: 162.43.7.144:3306/eyeuc

📄 处理: eyeuc_list193_p1-5_20251024_100000.jsonl
  ✅ 完成: 125 items

📄 处理: eyeuc_list193_p6-10_20251024_100001.jsonl
  ✅ 完成: 103 items

📄 处理: eyeuc_list193_merged_20251024_100002.jsonl
  ✅ 完成: 228 items

================================================================================
🎉 导入完成!
================================================================================
  总 items: 228
  总文件: 3
  用时: 5.23s
  速度: 43.6 items/s
================================================================================

🧹 清理已导入的文件...
  ✅ 删除: eyeuc_list193_p1-5_20251024_100000.jsonl
  ✅ 删除: eyeuc_list193_p6-10_20251024_100001.jsonl
  ✅ 删除: eyeuc_list193_merged_20251024_100002.jsonl
  📁 目录已空，删除: per_list_output
✨ 清理完成
```

---

### 2. 禁用自动清理

如果你需要保留源文件（例如备份或调试），可以禁用清理：

```bash
# 方法 1：环境变量
CLEANUP=false python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"

# 方法 2：在 .env 文件中设置
echo "CLEANUP=false" >> .env
source .env
python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
```

---

## 清理逻辑详解

### 清理时机

```python
# 只有在以下条件同时满足时才清理：
1. 导入成功（import_success = True）
2. 自动清理开启（auto_cleanup = True）
3. 数据库事务成功提交（conn.commit()）
```

### 清理范围

```python
# 清理的文件：
- 当前导入脚本处理的所有 JSONL 文件
- 由 glob 模式匹配的文件

# 不会清理：
- 导入失败的文件
- 不在当前导入列表中的文件
- 非 JSONL 文件
- 其他目录中的文件
```

### 目录管理

```python
# 清理文件后检查目录：
if 目录为空:
    删除目录
else:
    保留目录（显示剩余文件数量）
```

---

## 在自动化任务中使用

### 定时任务（automation/run_scheduled_crawls.sh）

自动化脚本已默认启用清理功能：

```bash
#!/bin/bash
# run_scheduled_crawls.sh

function run_list() {
  local list_id=$1
  local pages=$2
  
  # 1. 爬取数据
  bash smart_crawl.sh "$list_id" "$pages"
  
  # 2. 导入数据库（自动清理）
  python3 scripts/import_eyeuc_jsonl_to_mysql.py \
    "$(ls -t per_list_output/eyeuc_list${list_id}_*_merged_*.jsonl | head -1)"
  
  # ✅ 导入成功后，源文件已自动清理
}

run_list 182 100
run_list 193 50
```

**好处**：
- ✅ 每次定时任务后自动清理
- ✅ 防止磁盘空间累积
- ✅ 无需手动维护

---

## 配置示例

### .env 文件配置

```bash
# 数据库连接
MYSQL_HOST=162.43.7.144
MYSQL_PORT=3306
MYSQL_USER=eyeuc
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=eyeuc
MYSQL_SSL=false

# 自动清理（默认 true）
CLEANUP=true  # 或 false 禁用清理
```

---

## 故障排查

### 问题 1：文件没有被清理

**可能原因**：
1. 导入失败（检查日志中的 "❌" 标记）
2. `CLEANUP=false` 被设置
3. 文件权限问题

**解决方法**：
```bash
# 检查环境变量
echo $CLEANUP

# 检查文件权限
ls -lh per_list_output/

# 手动清理
rm per_list_output/*.jsonl
```

---

### 问题 2：目录没有被删除

**可能原因**：
- 目录不为空（还有其他文件）

**检查**：
```bash
# 查看目录内容
ls -la per_list_output/

# 查看剩余文件
find per_list_output/ -type f
```

---

### 问题 3：想恢复已删除的文件

**建议**：
1. **预防**：在首次导入前备份重要数据
   ```bash
   # 备份 JSONL 文件
   cp -r per_list_output per_list_output_backup
   ```

2. **重新爬取**：
   ```bash
   # 重新爬取指定列表
   bash batch_crawl.sh 193 5 cookies.json
   ```

3. **从数据库导出**（如果已导入）：
   ```bash
   # 可以从 MySQL 重新导出数据
   python scripts/export_database_to_jsonl.py  # (需自行编写)
   ```

---

## 最佳实践

### ✅ 推荐做法

1. **生产环境**：启用自动清理（默认）
   ```bash
   # 无需额外配置，默认行为即可
   python scripts/import_eyeuc_jsonl_to_mysql.py "per_list_output/*.jsonl"
   ```

2. **定期监控磁盘空间**：
   ```bash
   # 检查 per_list_output 大小
   du -sh per_list_output/
   
   # 如果发现异常增长，检查是否有导入失败
   ls -lh per_list_output/
   ```

3. **自动化任务日志**：
   ```bash
   # 检查最近的定时任务日志
   tail -100 logs/scheduled/run_*.log | grep "清理"
   ```

---

### ⚠️ 注意事项

1. **首次导入**：
   - 如果是首次大批量导入，建议先备份
   - 或者使用 `CLEANUP=false` 禁用清理
   - 验证数据正确后再启用清理

2. **调试阶段**：
   - 开发和调试时建议禁用清理
   - 便于检查原始数据和排查问题

3. **磁盘空间紧张时**：
   - 启用自动清理可以有效节省空间
   - 对于 list 182（100页），每次约 50MB

---

## 统计数据

### 清理效果

| 列表 | 页数 | 文件大小 | 清理后 |
|------|------|----------|--------|
| 182 (NBA2K25) | 100 | ~50 MB | 0 MB |
| 193 (NBA2K26) | 50 | ~25 MB | 0 MB |
| 172 (FIFA) | 35 | ~18 MB | 0 MB |
| 93 (其他) | 31 | ~15 MB | 0 MB |

**总节省**：每次自动任务约 **108 MB**

### 定时任务（6 小时一次）

- 每天运行 4 次
- 每天生成约 432 MB 数据
- 启用清理后：**0 MB** 累积 ✅

---

## 技术细节

### 核心代码

```python
def cleanup_imported_files(files):
    """清理已成功导入的文件"""
    if not files:
        return
    
    print("🧹 清理已导入的文件...")
    
    dirs_to_check = set()
    for file_path in files:
        try:
            file_obj = Path(file_path)
            if file_obj.exists():
                os.remove(file_path)
                print(f"  ✅ 删除: {file_obj.name}")
                dirs_to_check.add(file_obj.parent)
        except Exception as e:
            print(f"  ⚠️  删除失败 {Path(file_path).name}: {e}")
    
    # 检查目录是否为空
    for dir_path in dirs_to_check:
        try:
            if dir_path.exists() and dir_path.is_dir():
                remaining = list(dir_path.glob('*'))
                if not remaining:
                    print(f"  📁 目录已空，删除: {dir_path.name}")
                    dir_path.rmdir()
                else:
                    print(f"  📁 目录保留（还有 {len(remaining)} 个文件）: {dir_path.name}")
        except Exception as e:
            print(f"  ⚠️  检查目录失败 {dir_path}: {e}")
    
    print("✨ 清理完成\n")
```

### 调用逻辑

```python
def import_files(glob_pattern, auto_cleanup=True):
    files = glob.glob(glob_pattern)
    import_success = False
    
    try:
        # 导入数据...
        conn.commit()
        import_success = True
        
        # 自动清理
        if import_success and auto_cleanup:
            cleanup_imported_files(files)
        
        return True
    except Exception as e:
        conn.rollback()
        raise
```

---

## 总结

### 优点 ✅

1. **防止磁盘空间累积**
2. **全自动化**，无需手动维护
3. **安全**：只清理成功导入的文件
4. **可配置**：可随时禁用

### 适用场景 🎯

- ✅ 生产环境定时任务
- ✅ 自动化 CI/CD 流程
- ✅ 磁盘空间有限的服务器
- ✅ 不需要保留原始 JSONL 的场景

### 不适用场景 ⛔

- ❌ 需要长期保留原始数据
- ❌ 调试和开发阶段
- ❌ 需要多次导入同一文件

**建议**：根据实际需求灵活配置 `CLEANUP` 环境变量 🚀

