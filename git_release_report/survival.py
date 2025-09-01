from __future__ import annotations
from collections import defaultdict
from .gitwrap import GitWrap
from .models import SurvivalStat


def compute_survival(g: GitWrap, old: str, new: str, paths: list[str], ignore_ws: bool):
    """
    计算代码存活率统计

    分析在指定版本范围内引入的代码行有多少在新版本中仍然存活。
    存活率 = 存活行数 / 引入行数，用于评估代码质量和贡献者的代码持久性。

    Args:
        g: Git 操作包装器
        old: 旧版本引用
        new: 新版本引用  
        paths: 要分析的文件路径列表
        ignore_ws: 是否忽略空白字符差异

    Returns:
        tuple: (按提交分组的存活统计, 按作者分组的存活统计)
    """
    # 初始化统计字典
    by_commit = defaultdict(SurvivalStat)  # 按提交 SHA 分组
    by_author = defaultdict(SurvivalStat)  # 按作者身份分组

    # 第一步：统计引入的代码行数 (基于提交日志)
    # 使用 git log --numstat 获取每个提交的代码变更统计
    raw = g.log_numstat_no_merges(f"{old}..{new}")
    last_tag = None  # 记录当前处理的提交信息

    for ln in raw.splitlines():
        # 解析提交信息行 (格式: SHA|作者名|作者邮箱)
        if '|' in ln and ln.count('|') == 2 and ln.startswith(tuple('0123456789abcdef')):
            sha, an, ae = ln.split('|')
            last_tag = (sha, an, ae)
        # 解析文件变更统计行 (格式: 插入行数\t删除行数\t文件路径)
        elif '\t' in ln and last_tag:
            ins = ln.split('\t')[0]
            try:
                ins_i = int(ins)  # 插入的行数
            except ValueError:
                ins_i = 0  # 处理二进制文件等特殊情况
            sha, an, ae = last_tag
            # 累加到对应提交和作者的引入行数
            by_commit[sha].introduced_lines += ins_i
            by_author[f"{an} <{ae}>"].introduced_lines += ins_i

    # 第二步：统计存活的代码行数 (基于反向 blame)
    # 使用 git blame --reverse 查找在版本范围内引入且仍然存在的代码行
    for p in paths:
        try:
            # 尝试使用反向 blame 获取存活行信息
            braw = g.blame_reverse(old, new, p, ignore_ws)
        except Exception:
            # 如果反向 blame 不支持或失败，跳过该文件
            braw = ''

        # 解析 blame 输出，提取存活行信息
        sha = an = ae = None
        for ln in (braw.splitlines() if braw else []):
            # 解析提交 SHA (40 位十六进制字符串)
            if len(ln) >= 40 and all(c in '0123456789abcdef' for c in ln[:40]) and ln[40] == ' ':
                sha = ln[:40]
            # 解析作者姓名
            elif ln.startswith('author '):
                an = ln[7:]
            # 解析作者邮箱
            elif ln.startswith('author-mail '):
                ae = ln.split('<', 1)[-1].rstrip('>')
            # 解析代码行 (以制表符开头)
            elif ln.startswith('\t'):
                if sha and an and ae:
                    # 累加到对应提交和作者的存活行数
                    by_commit[sha].survived_lines += 1
                    by_author[f"{an} <{ae}>"].survived_lines += 1

    return by_commit, by_author
