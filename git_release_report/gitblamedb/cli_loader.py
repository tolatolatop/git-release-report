#!/usr/bin/env python3
"""
Git Blame Loader CLI工具
命令行工具用于快速加载git blame数据库
"""

import argparse
import sys
import os
from pathlib import Path
from sqlalchemy import func

from .models import get_db_session, Repository, Commit, File, BlameLine
from .loader import GitBlameLoader, load_git_blame_database
from .models import init_database


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Git Blame数据库加载器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本使用
  python -m git_release_report.gitblamedb.cli_loader /path/to/repo

  # 指定数据库和过滤条件
  python -m git_release_report.gitblamedb.cli_loader /path/to/repo \\
    --database sqlite:///my_blame.db \\
    --filter "\.(py|js)$" \\
    --name "my-project"

  # 使用PostgreSQL数据库
  python -m git_release_report.gitblamedb.cli_loader /path/to/repo \\
    --database "postgresql://user:pass@localhost/gitblame" \\
    --batch-size 2000

  # 强制重新加载所有文件
  python -m git_release_report.gitblamedb.cli_loader /path/to/repo \\
    --force-reload \\
    --verbose

  # 指定错误日志文件
  python -m git_release_report.gitblamedb.cli_loader /path/to/repo \\
    --log-file "custom-errors.log" \\
    --verbose
        """
    )

    parser.add_argument(
        'repo_path',
        help='Git仓库路径'
    )

    parser.add_argument(
        '--database', '-d',
        default='sqlite:///git_blame.db',
        help='数据库连接URL (默认: sqlite:///git_blame.db)'
    )

    parser.add_argument(
        '--filter', '-f',
        help='文件过滤正则表达式 (例如: "\\.(py|js)$")'
    )

    parser.add_argument(
        '--name', '-n',
        help='仓库名称 (默认使用路径名)'
    )

    parser.add_argument(
        '--url', '-u',
        help='仓库URL'
    )

    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=1000,
        help='批量插入大小 (默认: 1000)'
    )

    parser.add_argument(
        '--init-db',
        action='store_true',
        help='初始化数据库表'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )

    parser.add_argument(
        '--force-reload',
        action='store_true',
        help='强制重新加载所有文件，忽略修改时间检查'
    )

    parser.add_argument(
        '--log-file',
        default='analyze-failed.log',
        help='错误日志文件路径 (默认: analyze-failed.log)'
    )

    args = parser.parse_args()

    # 验证仓库路径
    if not os.path.exists(args.repo_path):
        print(f"❌ 错误: 仓库路径不存在: {args.repo_path}")
        sys.exit(1)

    if not os.path.exists(os.path.join(args.repo_path, '.git')):
        print(f"❌ 错误: 不是有效的git仓库: {args.repo_path}")
        sys.exit(1)

    # 初始化数据库
    if args.init_db:
        print(f"📊 初始化数据库: {args.database}")
        init_database(args.database)

    # 设置日志级别
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # 加载仓库
    print(f"🚀 开始加载仓库: {args.repo_path}")
    print(f"📊 数据库: {args.database}")
    if args.filter:
        print(f"🔍 文件过滤: {args.filter}")
    if args.name:
        print(f"📁 仓库名称: {args.name}")
    if args.url:
        print(f"🔗 仓库URL: {args.url}")
    print(f"📦 批量大小: {args.batch_size}")
    if args.force_reload:
        print("🔄 强制重新加载: 是")
    print(f"📝 错误日志文件: {args.log_file}")
    print("-" * 50)

    try:
        # 使用便捷函数加载
        success = load_git_blame_database(
            repo_path=args.repo_path,
            database_url=args.database,
            file_filter_regex=args.filter,
            repo_name=args.name,
            repo_url=args.url,
            force_reload=args.force_reload,
            log_file=args.log_file
        )

        if success:
            print("✅ 仓库加载成功！")

            # 显示统计信息
            try:

                session = get_db_session()
                try:
                    repo_count = session.query(Repository).count()
                    commit_count = session.query(Commit).count()
                    file_count = session.query(File).count()
                    blame_count = session.query(BlameLine).count()

                    print(f"\n📊 统计信息:")
                    print(f"  仓库数量: {repo_count}")
                    print(f"  提交数量: {commit_count}")
                    print(f"  文件数量: {file_count}")
                    print(f"  Blame行数: {blame_count}")

                finally:
                    session.close()

            except Exception as e:
                print(f"⚠️  无法获取统计信息: {e}")

            sys.exit(0)
        else:
            print("❌ 仓库加载失败！")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
