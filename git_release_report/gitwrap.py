from __future__ import annotations
from git import Repo
from typing import Iterable, List


class GitWrap:
    """Git 操作封装类，提供统一的 Git 命令接口"""

    def __init__(self, repo_path: str):
        """
        初始化 Git 仓库包装器

        Args:
            repo_path: Git 仓库路径
        """
        self.repo = Repo(repo_path)
        assert not self.repo.bare
        self.git = self.repo.git

    def merge_base(self, a: str, b: str) -> str:
        """
        查找两个提交的共同祖先

        Args:
            a: 第一个提交引用
            b: 第二个提交引用

        Returns:
            共同祖先的 SHA 值
        """
        return self.git.merge_base(a, b).strip()

    def iter_commits_range(self, spec: str):
        """
        迭代指定范围内的提交

        Args:
            spec: 提交范围规范 (如: "HEAD~10..HEAD")

        Returns:
            提交迭代器
        """
        return self.repo.iter_commits(spec)

    def diff_raw(self, old: str, new: str, ignore_ws: bool, rename: int, copy: int,
                 include: List[str], exclude: List[str], unified0: bool = True) -> str:
        """
        获取两个版本之间的原始差异输出

        Args:
            old: 旧版本引用
            new: 新版本引用
            ignore_ws: 是否忽略空白字符差异
            rename: 重命名检测阈值 (百分比)
            copy: 复制检测阈值 (百分比)
            include: 包含的路径列表
            exclude: 排除的路径列表
            unified0: 是否使用 -U0 格式

        Returns:
            原始差异文本
        """
        args = [old, new, "-M", f"--find-renames={rename}%",
                "-C", f"--find-copies={copy}%", "--numstat", "--patch"]
        if ignore_ws:
            args.append("-w")
        if unified0:
            args.append("-U0")
        args.append("--")
        args.extend(include or ["."])
        for ex in exclude or []:
            args.append(f":(exclude){ex}")
        return self.git.diff(*args)

    def blame_porcelain(self, rev: str, path: str, start: int, end: int, ignore_ws: bool) -> str:
        """
        获取指定行范围的 blame 信息 (porcelain 格式)

        Args:
            rev: 版本引用
            path: 文件路径
            start: 起始行号
            end: 结束行号
            ignore_ws: 是否忽略空白字符差异

        Returns:
            blame 信息文本 (porcelain 格式)
        """
        args = [rev, "--line-porcelain", "-L", f"{start},{end}", "--", path]
        if ignore_ws:
            args.insert(1, "-w")
            args.insert(2, "-M")
            args.insert(3, "-C")
        return self.git.blame(*args)

    def log_numstat_no_merges(self, spec: str) -> str:
        """
        获取指定范围内的提交日志 (排除合并提交，包含统计信息)

        Args:
            spec: 提交范围规范

        Returns:
            格式化的日志文本 (SHA|作者名|作者邮箱)
        """
        return self.git.log(spec, "--no-merges", "--numstat", "--format=%H|%an|%ae")

    def blame_reverse_supported(self) -> bool:
        """
        检查当前 Git 版本是否支持反向 blame

        Returns:
            是否支持反向 blame
        """
        try:
            self.git.blame("--help")
            return True
        except Exception:
            return False

    def blame_reverse(self, old: str, new: str, path: str, ignore_ws: bool) -> str:
        """
        执行反向 blame 操作，查找在指定版本范围内引入的代码行

        Args:
            old: 旧版本引用
            new: 新版本引用
            path: 文件路径
            ignore_ws: 是否忽略空白字符差异

        Returns:
            反向 blame 结果文本
        """
        # git blame --reverse OLD..NEW -- path
        args = ["--reverse", f"{old}..{new}"]
        if ignore_ws:
            args.insert(0, "-w")
            args.insert(1, "-M")
            args.insert(2, "-C")
        args.extend(["--", path])
        return self.git.blame(*args)
