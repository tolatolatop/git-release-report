#!/usr/bin/env python3
"""
Git Blame Loader使用示例
演示如何使用GitBlameLoader快速初始化git blame数据库
"""

from git_release_report.gitblamedb.models import init_database, get_db_session
from git_release_report.gitblamedb.loader import GitBlameLoader, load_git_blame_database
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def example_basic_usage():
    """基本使用示例"""
    print("🚀 Git Blame Loader 基本使用示例")
    print("=" * 50)

    # 数据库配置
    database_url = "sqlite:///example_git_blame.db"

    # 初始化数据库
    print("📊 初始化数据库...")
    init_database(database_url)

    # 使用便捷函数加载仓库
    repo_path = "/path/to/your/git/repo"  # 替换为实际的仓库路径

    if os.path.exists(repo_path):
        print(f"📁 加载仓库: {repo_path}")

        success = load_git_blame_database(
            repo_path=repo_path,
            database_url=database_url,
            file_filter_regex=r"\.(py|js|ts|java|cpp|c|h)$",  # 只分析代码文件
            repo_name="my-project",
            repo_url="https://github.com/user/my-project.git"
        )

        if success:
            print("✅ 仓库加载成功！")
        else:
            print("❌ 仓库加载失败！")
    else:
        print(f"⚠️  仓库路径不存在: {repo_path}")


def example_advanced_usage():
    """高级使用示例"""
    print("\n🔧 Git Blame Loader 高级使用示例")
    print("=" * 50)

    # 数据库配置
    database_url = "sqlite:///advanced_git_blame.db"

    # 初始化数据库
    init_database(database_url)

    # 创建加载器实例
    loader = GitBlameLoader(database_url, batch_size=500)

    try:
        # 加载多个仓库
        repositories = [
            {
                "path": "/path/to/repo1",
                "name": "backend-service",
                "url": "https://github.com/user/backend.git",
                "filter": r"\.(py|sql)$"  # 只分析Python和SQL文件
            },
            {
                "path": "/path/to/repo2",
                "name": "frontend-app",
                "url": "https://github.com/user/frontend.git",
                "filter": r"\.(js|ts|tsx|jsx|vue)$"  # 只分析前端文件
            }
        ]

        for repo_config in repositories:
            if os.path.exists(repo_config["path"]):
                print(f"📁 加载仓库: {repo_config['name']}")

                success = loader.load_repository(
                    repo_path=repo_config["path"],
                    file_filter_regex=repo_config["filter"],
                    repo_name=repo_config["name"],
                    repo_url=repo_config["url"]
                )

                if success:
                    print(f"✅ {repo_config['name']} 加载成功！")
                else:
                    print(f"❌ {repo_config['name']} 加载失败！")
            else:
                print(f"⚠️  仓库路径不存在: {repo_config['path']}")

    finally:
        loader.close()


def example_query_loaded_data():
    """查询已加载数据的示例"""
    print("\n📊 查询已加载数据示例")
    print("=" * 50)

    database_url = "sqlite:///example_git_blame.db"
    session = get_db_session()

    try:
        from git_release_report.gitblamedb.models import Repository, Commit, File, BlameLine
        from sqlalchemy import func

        # 查询仓库统计
        repo_count = session.query(Repository).count()
        print(f"📁 仓库数量: {repo_count}")

        # 查询提交统计
        commit_count = session.query(Commit).count()
        print(f"📝 提交数量: {commit_count}")

        # 查询文件统计
        file_count = session.query(File).count()
        print(f"📄 文件数量: {file_count}")

        # 查询blame行统计
        blame_count = session.query(BlameLine).count()
        print(f"🔍 Blame行数: {blame_count}")

        # 按文件类型统计
        file_type_stats = session.query(
            File.extension,
            func.count(BlameLine.id).label('line_count')
        ).join(BlameLine).group_by(File.extension).all()

        print("\n📈 按文件类型统计:")
        for ext, count in file_type_stats:
            print(f"  {ext or '无扩展名'}: {count} 行")

        # 按作者统计
        author_stats = session.query(
            Commit.author_name,
            func.count(func.distinct(Commit.id)).label('commit_count'),
            func.count(BlameLine.id).label('line_count')
        ).join(BlameLine).group_by(Commit.author_name).order_by(
            func.count(BlameLine.id).desc()
        ).limit(5).all()

        print("\n👥 贡献者统计 (Top 5):")
        for author, commit_count, line_count in author_stats:
            print(f"  {author}: {commit_count} 次提交, {line_count} 行代码")

        # 查询最近修改的文件
        recent_files = session.query(File).order_by(
            File.last_modified.desc()
        ).limit(5).all()

        print("\n📁 最近修改的文件:")
        for file in recent_files:
            print(f"  {file.path} (修改于: {file.last_modified})")

    except Exception as e:
        print(f"❌ 查询错误: {e}")
    finally:
        session.close()


def example_file_filtering():
    """文件过滤示例"""
    print("\n🔍 文件过滤示例")
    print("=" * 50)

    # 不同的过滤模式示例
    filter_examples = [
        {
            "name": "Python文件",
            "regex": r"\.py$",
            "description": "只分析Python文件"
        },
        {
            "name": "前端文件",
            "regex": r"\.(js|ts|tsx|jsx|vue|svelte)$",
            "description": "只分析前端相关文件"
        },
        {
            "name": "配置文件",
            "regex": r"\.(json|yaml|yml|toml|ini|cfg|conf)$",
            "description": "只分析配置文件"
        },
        {
            "name": "文档文件",
            "regex": r"\.(md|rst|txt|adoc)$",
            "description": "只分析文档文件"
        },
        {
            "name": "排除测试文件",
            "regex": r"^(?!.*test).*\.(py|js|ts)$",
            "description": "排除包含test的文件"
        },
        {
            "name": "特定目录",
            "regex": r"^src/.*\.(py|js|ts)$",
            "description": "只分析src目录下的代码文件"
        }
    ]

    for example in filter_examples:
        print(f"📋 {example['name']}: {example['regex']}")
        print(f"   {example['description']}")
        print()


def example_error_handling():
    """错误处理示例"""
    print("\n⚠️  错误处理示例")
    print("=" * 50)

    database_url = "sqlite:///error_handling_example.db"
    init_database(database_url)

    loader = GitBlameLoader(database_url)

    try:
        # 测试各种错误情况

        # 1. 不存在的路径
        print("1. 测试不存在的路径:")
        success = loader.load_repository("/nonexistent/path")
        print(f"   结果: {'成功' if success else '失败 (预期)'}")

        # 2. 非git仓库
        print("\n2. 测试非git仓库:")
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            success = loader.load_repository(temp_dir)
            print(f"   结果: {'成功' if success else '失败 (预期)'}")

        # 3. 无效的正则表达式
        print("\n3. 测试无效的正则表达式:")
        success = loader.load_repository(
            "/path/to/repo",
            file_filter_regex="[invalid regex"
        )
        print(f"   结果: {'成功' if success else '失败 (预期)'}")

    except Exception as e:
        print(f"❌ 捕获到异常: {e}")
    finally:
        loader.close()


if __name__ == "__main__":
    print("🎯 Git Blame Loader 完整示例")
    print("=" * 60)

    # 运行各种示例
    example_basic_usage()
    example_advanced_usage()
    example_query_loaded_data()
    example_file_filtering()
    example_error_handling()

    print("\n✅ 所有示例运行完成！")
    print("\n💡 使用提示:")
    print("1. 将示例中的路径替换为实际的git仓库路径")
    print("2. 根据需要调整文件过滤正则表达式")
    print("3. 对于大型仓库，考虑使用更大的batch_size")
    print("4. 定期清理数据库以保持性能")
