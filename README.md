# git-release-report

一个精确的发布差异分析和贡献者分析工具，使用 GitPython + 原生 git，生成多视图报告（基于提交、基于 blame、合并责任、重命名/复制/删除、存活率、按目录变更）。

## 功能特性

- **发布简报·提交口径** (A): 基于提交的贡献者统计
- **精准归属·行级 blame** (C): 基于 blame 的最终代码归属分析
- **R/C/D 监督** (E): 重命名、复制、删除文件跟踪
- **存活度审计** (F): 代码存活率分析

## 安装

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 使用方法

```bash
release-report \
  --repo . \
  --old v1.2.0 --new v1.3.0 \
  --preset all \
  --include "src/" --exclude "vendor/,dist/" \
  --ignore-ws true \
  --rename 90 --copy 80 \
  --first-parent false \
  --mailmap .mailmap \
  --bot-filter "bot|automation|ci@" \
  --out ./out
```

## 输出

工具会在 `/out` 文件夹中生成：

- `analysis.json` - 完整的结构化数据
- `commits_survival.json` - 按提交顺序排序的代码存活率报告
- `summary.md` - 人类可读的发布报告
- CSV 文件：
  - 贡献者（基于提交）
  - 贡献者（基于 blame 的最终归属）
  - 合并提交
  - 重命名/复制/删除
  - 按提交/作者分组的存活率
  - 按目录的变更统计

## 示例

运行演示脚本：

```bash
./examples/run_demo.sh
```

## 路线图

- v0.1.1: 并行 blame + sqlite 缓存
- v0.1.2: 主线/对称差去重
- v0.1.3: 合并解决行分析
- v0.1.4: 按目录变更表 + Jinja2 模板
- v0.1.5: 更好的重命名/删除推断
- v0.1.6: 身份规范化与 .mailmap 支持



##
异步
管道
终止符
批处理
缓冲区
中断恢复
事务

```yaml
manifest:
  repos:
    files:
      lines:
    commits:
```

## 统计
- 两版本差异
- 时间段内合入
  - 包含了merge子节点

- 所有修改
- 存活的修改

- 所有的修改
- 代码的修改

- 差异的文件

- 移动
- 删除
