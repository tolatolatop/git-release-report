#!/usr/bin/env python3
"""
增量加载示例
演示如何使用文件修改时间检查来避免重复处理未修改的文件
"""

from git_release_report.gitblamedb.models import init_database, get_db_session
from git_release_report.gitblamedb.loader import GitBlameLoader, load_git_blame_database
import os
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def example_incremental_loading():
    """增量加载示例"""
    print("🔄 增量加载示例")
    print("=" * 50)

    # 数据库配置
    database_url = "sqlite:///incremental_loading.db"

    # 初始化数据库
    print("📊 初始化数据库...")
    init_database(database_url)

    # 模拟仓库路径（请替换为实际路径）
    repo_path = "/path/to/your/git/repo"

    if not os.path.exists(repo_path):
        print(f"⚠️  仓库路径不存在: {repo_path}")
        print("请将示例中的路径替换为实际的git仓库路径")
        return

    # 第一次加载
    print("\n🚀 第一次加载仓库...")
    start_time = time.time()

    success = load_git_blame_database(
        repo_path=repo_path,
        database_url=database_url,
        file_filter_regex=r"\.(py|js|ts)$",
        repo_name="test-repo",
        force_reload=False  # 正常加载
    )

    first_load_time = time.time() - start_time

    if success:
        print(f"✅ 第一次加载成功！耗时: {first_load_time:.2f}秒")

        # 显示统计信息
        show_statistics(database_url)
    else:
        print("❌ 第一次加载失败！")
        return

    # 等待一段时间（模拟文件未修改）
    print("\n⏳ 等待5秒（模拟文件未修改）...")
    time.sleep(5)

    # 第二次加载（应该跳过未修改的文件）
    print("\n🔄 第二次加载仓库（增量模式）...")
    start_time = time.time()

    success = load_git_blame_database(
        repo_path=repo_path,
        database_url=database_url,
        file_filter_regex=r"\.(py|js|ts)$",
        repo_name="test-repo",
        force_reload=False  # 增量加载
    )

    second_load_time = time.time() - start_time

    if success:
        print(f"✅ 第二次加载成功！耗时: {second_load_time:.2f}秒")
        print(
            f"🚀 性能提升: {((first_load_time - second_load_time) / first_load_time * 100):.1f}%")

        # 显示统计信息
        show_statistics(database_url)
    else:
        print("❌ 第二次加载失败！")

    # 强制重新加载
    print("\n🔄 强制重新加载所有文件...")
    start_time = time.time()

    success = load_git_blame_database(
        repo_path=repo_path,
        database_url=database_url,
        file_filter_regex=r"\.(py|js|ts)$",
        repo_name="test-repo",
        force_reload=True  # 强制重新加载
    )

    force_load_time = time.time() - start_time

    if success:
        print(f"✅ 强制重新加载成功！耗时: {force_load_time:.2f}秒")

        # 显示统计信息
        show_statistics(database_url)
    else:
        print("❌ 强制重新加载失败！")


def show_statistics(database_url: str):
    """显示数据库统计信息"""
    try:
        session = get_db_session()

        from git_release_report.gitblamedb.models import Repository, Commit, File, BlameLine
        from sqlalchemy import func

        # 查询统计信息
        repo_count = session.query(Repository).count()
        commit_count = session.query(Commit).count()
        file_count = session.query(File).count()
        blame_count = session.query(BlameLine).count()

        print(f"\n📊 当前统计信息:")
        print(f"  仓库数量: {repo_count}")
        print(f"  提交数量: {commit_count}")
        print(f"  文件数量: {file_count}")
        print(f"  Blame行数: {blame_count}")

        # 查询最近更新的文件
        recent_files = session.query(File).order_by(
            File.updated_at.desc()
        ).limit(3).all()

        print(f"\n📁 最近更新的文件:")
        for file in recent_files:
            print(f"  {file.path} (更新于: {file.updated_at})")

        session.close()

    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")


def example_file_modification_detection():
    """文件修改检测示例"""
    print("\n🔍 文件修改检测示例")
    print("=" * 50)

    # 数据库配置
    database_url = "sqlite:///modification_detection.db"

    # 初始化数据库
    init_database(database_url)

    # 模拟仓库路径
    repo_path = "/path/to/your/git/repo"

    if not os.path.exists(repo_path):
        print(f"⚠️  仓库路径不存在: {repo_path}")
        return

    # 创建加载器实例
    loader = GitBlameLoader(database_url)

    try:
        # 第一次加载
        print("🚀 第一次加载...")
        success = loader.load_repository(
            repo_path=repo_path,
            file_filter_regex=r"\.py$",
            repo_name="modification-test"
        )

        if success:
            print("✅ 第一次加载成功！")

            # 模拟文件修改（这里只是演示，实际使用中文件会被git修改）
            print("\n📝 模拟文件修改...")
            print("在实际使用中，当文件被修改后，下次加载时会检测到修改并重新处理")

            # 第二次加载（检测修改）
            print("\n🔄 第二次加载（检测修改）...")
            success = loader.load_repository(
                repo_path=repo_path,
                file_filter_regex=r"\.py$",
                repo_name="modification-test"
            )

            if success:
                print("✅ 第二次加载成功！")
                print("💡 如果文件被修改，会重新处理；如果未修改，会跳过")
            else:
                print("❌ 第二次加载失败！")
        else:
            print("❌ 第一次加载失败！")

    finally:
        loader.close()


def example_cleanup_deleted_files():
    """清理已删除文件示例"""
    print("\n🗑️  清理已删除文件示例")
    print("=" * 50)

    # 数据库配置
    database_url = "sqlite:///cleanup_test.db"

    # 初始化数据库
    init_database(database_url)

    # 模拟仓库路径
    repo_path = "/path/to/your/git/repo"

    if not os.path.exists(repo_path):
        print(f"⚠️  仓库路径不存在: {repo_path}")
        return

    # 创建加载器实例
    loader = GitBlameLoader(database_url)

    try:
        # 第一次加载
        print("🚀 第一次加载所有文件...")
        success = loader.load_repository(
            repo_path=repo_path,
            file_filter_regex=r"\.py$",
            repo_name="cleanup-test"
        )

        if success:
            print("✅ 第一次加载成功！")
            show_statistics(database_url)

            print("\n📝 模拟文件删除...")
            print("在实际使用中，当文件从git仓库中删除后，下次加载时会自动清理相关记录")

            # 第二次加载（会清理已删除的文件）
            print("\n🔄 第二次加载（清理已删除文件）...")
            success = loader.load_repository(
                repo_path=repo_path,
                file_filter_regex=r"\.py$",  # 只处理Python文件，其他文件会被清理
                repo_name="cleanup-test"
            )

            if success:
                print("✅ 第二次加载成功！")
                print("💡 已删除文件的记录已被自动清理")
                show_statistics(database_url)
            else:
                print("❌ 第二次加载失败！")
        else:
            print("❌ 第一次加载失败！")

    finally:
        loader.close()


if __name__ == "__main__":
    print("🎯 Git Blame Loader 增量加载完整示例")
    print("=" * 60)

    # 运行各种示例
    example_incremental_loading()
    example_file_modification_detection()
    example_cleanup_deleted_files()

    print("\n✅ 所有示例运行完成！")
    print("\n💡 增量加载的优势:")
    print("1. 🚀 性能提升: 跳过未修改的文件，大幅减少处理时间")
    print("2. 🔄 自动检测: 基于文件修改时间自动判断是否需要重新处理")
    print("3. 🗑️  自动清理: 自动清理已删除文件的记录")
    print("4. 🎛️  灵活控制: 支持强制重新加载选项")
    print("5. 📊 智能统计: 提供详细的处理统计信息")
