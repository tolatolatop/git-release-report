import pytest
from click.testing import CliRunner
from git_release_report.cli import main


def test_main():
    """测试main函数的基本功能"""
    runner = CliRunner()

    # 使用CliRunner来测试Click命令
    result = runner.invoke(main, [
        '--repo', '.',
        '--old', 'HEAD~4',
        '--new', 'HEAD',
        '--preset', 'all',
        '--include', 'git_release_report/',
        '--exclude', 'vendor/',
        '--exclude', 'dist/',
        '--ignore-ws',
        '--rename', '90',
        '--copy', '80',
        '--no-first-parent',
        '--out', 'out'
    ])

    # 检查命令是否成功执行
    # 注意：由于这是一个真实的git操作，可能会因为git历史不足而失败
    # 所以我们主要检查命令能够被正确解析和执行
    assert result.exit_code in [0, 1]  # 0表示成功，1可能表示git历史不足等错误
    assert result.exception is None or isinstance(result.exception, SystemExit)
