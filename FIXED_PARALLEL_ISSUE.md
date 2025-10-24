# ✅ 并行爬虫问题修复说明

## 问题描述

运行 `./smart_crawl.sh 182 100` 时，所有任务都立即失败，日志只有开头部分，没有实际的爬取过程。

## 根本原因

`batch_crawl.sh` 脚本中有**两处交互式输入**，导致后台运行时卡住：

1. **第 60 行**：`read -p "确认开始抓取？(y/N) "`
2. **第 93 行**：`read -p "继续下一批次？(Y/n) "`

当脚本通过 `&` 在后台运行时，这些 `read` 命令无法接收输入，导致进程挂起。

## 修复方案

### 修复 1：自动激活虚拟环境

```bash
# 在脚本开头添加
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi
```

### 修复 2：检测运行模式

使用 `[ -t 0 ]` 检测标准输入是否是终端：
- 交互模式（终端）：正常询问用户
- 后台模式（管道/重定向）：自动继续

```bash
# 开始确认
if [ -t 0 ]; then
    # 交互模式：询问用户
    read -p "确认开始抓取？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}已取消${NC}"
        exit 0
    fi
else
    # 后台模式：自动开始
    echo -e "${GREEN}✅ 后台模式，自动开始...${NC}"
    echo ""
fi
```

```bash
# 失败后继续
if [ -t 0 ]; then
    # 交互模式：询问是否继续
    read -p "继续下一批次？(Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo -e "${YELLOW}已停止${NC}"
        break
    fi
else
    # 后台模式：自动继续
    echo -e "${YELLOW}自动继续下一批次...${NC}"
fi
```

## 验证测试

```bash
# 测试 1：交互模式
./batch_crawl.sh 193 1 5 cookies.json 1
# ✅ 会询问确认

# 测试 2：后台模式
echo "" | ./batch_crawl.sh 193 1 5 cookies.json 1
# ✅ 自动开始，不会卡住

# 测试 3：并行运行
./smart_crawl.sh 193 2 1
# ✅ 所有任务正常运行
```

## 影响文件

- ✅ `/root/dev/eyeuc-scrapy/batch_crawl.sh` - 已修复
- ✅ `/root/dev/eyeuc-scrapy/parallel_crawl.sh` - 调用 batch_crawl.sh，自动受益
- ✅ `/root/dev/eyeuc-scrapy/smart_crawl.sh` - 调用 batch_crawl.sh，自动受益

## 现在可以正常使用

```bash
# 一键并行爬取
./smart_crawl.sh 182 100

# 自定义并行数
./parallel_crawl.sh 182 100 8

# 手动并行（多个终端/后台）
./batch_crawl.sh 182 50 5 cookies.json 1 &
./batch_crawl.sh 182 100 5 cookies.json 51 &
wait
python3 merge_batches.py 182
```

## 其他发现的问题

### Cookies 过期警告

```
WARNING: 可能需要登录: https://bbs.eyeuc.com/down/view/31715
```

**解决方案**：重新获取 cookies
```bash
# 1. 浏览器登录 bbs.eyeuc.com
# 2. F12 → Application → Cookies
# 3. 复制所有 cookies 到 cookies.json
# 4. 格式参考 .env.example
```

### 相对时间解析警告

```
WARNING: 无法解析相对时间: 2025-9-7 18:56
```

**不是问题**：这个格式 `YYYY-M-D HH:MM` 已经是绝对时间，只是格式与标准的 `YYYY-MM-DD HH:MM` 略有不同（月份没有补零）。

**修复建议**：增强 `_parse_relative_time()` 支持这种格式。

---

**修复时间**：2025-10-19  
**状态**：✅ 已完成并测试通过







