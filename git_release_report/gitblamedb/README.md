# Git Blame数据库模块

这个模块使用SQLAlchemy实现了一个完整的git blame数据库，用于详细记录仓库名称、文件、行号、git信息以及文件更新时间等信息。

## 功能特性

- 🗄️ **完整的数据库模型**: 包含仓库、提交、文件和blame行信息
- 🔍 **高效的索引**: 针对常用查询场景优化的数据库索引
- 🔗 **关系映射**: 完整的表间关系，支持级联操作
- 📊 **统计分析**: 支持按作者、文件类型、时间范围等维度统计
- 🚀 **易于使用**: 提供便捷的数据库管理器和会话管理

## 数据库表结构

### 1. Repository (仓库表)
- `id`: 主键
- `name`: 仓库名称
- `path`: 仓库路径
- `url`: 仓库URL
- `description`: 仓库描述
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. Commit (提交表)
- `id`: 主键
- `repository_id`: 仓库ID (外键)
- `sha`: 提交SHA
- `short_sha`: 短SHA
- `author_name`: 作者姓名
- `author_email`: 作者邮箱
- `committer_name`: 提交者姓名
- `committer_email`: 提交者邮箱
- `authored_time`: 作者时间
- `committed_time`: 提交时间
- `message`: 提交信息
- `is_merge`: 是否为合并提交
- `on_mainline`: 是否在主线上

### 3. File (文件表)
- `id`: 主键
- `repository_id`: 仓库ID (外键)
- `path`: 文件路径
- `name`: 文件名
- `extension`: 文件扩展名
- `size`: 文件大小
- `is_binary`: 是否为二进制文件
- `last_modified`: 最后修改时间

### 4. BlameLine (Blame行表)
- `id`: 主键
- `repository_id`: 仓库ID (外键)
- `file_id`: 文件ID (外键)
- `commit_id`: 提交ID (外键)
- `line_number`: 行号
- `content`: 行内容
- `is_merge_line`: 是否为合并行
- `original_line_number`: 原始行号
- `original_file_path`: 原始文件路径
- `blamed_at`: blame分析时间

## 使用方法

### 1. 基本使用

```python
from git_release_report.gitblamedb import (
    Repository, Commit, File, BlameLine,
    init_database, get_db_session
)

# 初始化数据库
init_database("sqlite:///git_blame.db")

# 获取数据库会话
session = get_db_session()

# 创建仓库记录
repo = Repository(
    name="my-repo",
    path="/path/to/repo",
    url="https://github.com/user/repo.git"
)
session.add(repo)
session.commit()
```

### 2. 批量插入blame数据

```python
# 创建提交记录
commit = Commit(
    repository_id=repo.id,
    sha="a1b2c3d4e5f6...",
    author_name="张三",
    author_email="zhangsan@example.com",
    authored_time=datetime.now()
)
session.add(commit)

# 创建文件记录
file_record = File(
    repository_id=repo.id,
    path="src/main.py",
    name="main.py",
    extension="py"
)
session.add(file_record)

# 批量插入blame行
blame_lines = []
for line_num, content in enumerate(file_content, 1):
    blame_line = BlameLine(
        repository_id=repo.id,
        file_id=file_record.id,
        commit_id=commit.id,
        line_number=line_num,
        content=content
    )
    blame_lines.append(blame_line)

session.add_all(blame_lines)
session.commit()
```

### 3. 查询示例

```python
# 查询特定文件的blame信息
blame_info = session.query(BlameLine).join(File).filter(
    File.path == "src/main.py"
).all()

# 查询特定作者的提交
author_commits = session.query(Commit).filter(
    Commit.author_name == "张三"
).all()

# 按文件类型统计
from sqlalchemy import func
file_stats = session.query(
    File.extension,
    func.count(BlameLine.id).label('line_count')
).join(BlameLine).group_by(File.extension).all()
```

### 4. 数据库管理

```python
from git_release_report.gitblamedb import DatabaseManager

# 创建自定义数据库管理器
db_manager = DatabaseManager("postgresql://user:pass@localhost/db")

# 创建表
db_manager.create_tables()

# 删除表
db_manager.drop_tables()

# 关闭连接
db_manager.close()
```

## 索引优化

数据库包含以下索引以优化查询性能：

- 仓库名称和路径索引
- 提交SHA索引
- 作者信息索引
- 文件路径索引
- blame行号索引
- 时间范围索引

## 支持的数据库

- SQLite (默认)
- PostgreSQL
- MySQL
- 其他SQLAlchemy支持的数据库

## 依赖要求

- SQLAlchemy >= 2.0.0
- Python >= 3.10

## Git Blame Loader

### 快速加载器

`GitBlameLoader` 类提供了快速初始化git blame数据库的功能：

```python
from git_release_report.gitblamedb import GitBlameLoader, load_git_blame_database

# 使用便捷函数
success = load_git_blame_database(
    repo_path="/path/to/your/repo",
    database_url="sqlite:///git_blame.db",
    file_filter_regex=r"\.(py|js|ts)$",  # 只分析代码文件
    repo_name="my-project",
    repo_url="https://github.com/user/repo.git"
)

# 或使用类实例
loader = GitBlameLoader("sqlite:///git_blame.db", batch_size=1000)
try:
    success = loader.load_repository(
        repo_path="/path/to/your/repo",
        file_filter_regex=r"\.(py|js|ts)$"
    )
finally:
    loader.close()
```

### 命令行工具

使用CLI工具快速加载：

```bash
# 基本使用
python -m git_release_report.gitblamedb.cli_loader /path/to/repo

# 指定过滤条件和数据库
python -m git_release_report.gitblamedb.cli_loader /path/to/repo \
  --database sqlite:///my_blame.db \
  --filter "\.(py|js)$" \
  --name "my-project" \
  --verbose
```

### 文件过滤

支持使用正则表达式过滤文件：

- `r"\.py$"` - 只分析Python文件
- `r"\.(js|ts|tsx)$"` - 只分析前端文件
- `r"^src/.*\.py$"` - 只分析src目录下的Python文件
- `r"^(?!.*test).*\.py$"` - 排除测试文件

### 增量加载

Loader支持智能的增量加载功能，可以显著提高重复加载的性能：

```python
# 增量加载（默认模式）
success = load_git_blame_database(
    repo_path="/path/to/repo",
    database_url="sqlite:///git_blame.db",
    force_reload=False  # 跳过未修改的文件
)

# 强制重新加载所有文件
success = load_git_blame_database(
    repo_path="/path/to/repo", 
    database_url="sqlite:///git_blame.db",
    force_reload=True  # 重新处理所有文件
)
```

**增量加载特性：**
- 🚀 **性能优化**: 自动跳过未修改的文件，大幅减少处理时间
- 🔄 **智能检测**: 基于文件修改时间自动判断是否需要重新处理
- 🗑️ **自动清理**: 自动清理已删除文件的记录
- 📊 **统计信息**: 提供详细的处理统计和性能指标

### 调试和错误处理

Loader提供了强大的调试和错误处理功能：

```python
# 指定错误日志文件
loader = GitBlameLoader(
    database_url="sqlite:///git_blame.db",
    log_file="custom-errors.log"
)
```

**调试特性：**
- 📝 **详细日志**: 分析失败时自动记录详细信息到日志文件
- 🔍 **输出转储**: 当git blame执行失败时，自动转储原始输出
- 🛡️ **错误恢复**: 遇到无法解析的行时自动跳过，继续处理其他文件
- 📊 **分类记录**: 不同类型的错误分别记录，便于问题定位

## 示例代码

查看以下文件获取完整的使用示例：
- `example_usage.py` - 基本模型使用示例
- `loader_example.py` - Loader使用示例
- `incremental_loading_example.py` - 增量加载示例
- `cli_loader.py` - 命令行工具

## 注意事项

1. 确保在插入数据前先创建仓库和提交记录
2. 使用事务确保数据一致性
3. 对于大量数据，考虑使用批量插入
4. 定期清理不需要的历史数据以保持性能
