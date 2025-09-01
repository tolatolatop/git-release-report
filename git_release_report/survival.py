from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from rich.console import Console
from .gitwrap import GitWrap
from .models import SurvivalStat

con = Console()


def compute_survival(g: GitWrap, old: str, new: str, paths: list[str], ignore_ws: bool, debug_log_file: str = None):
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
        debug_log_file: 调试日志文件路径（可选）

    Returns:
        tuple: (按提交分组的存活统计, 按作者分组的存活统计)
    """
    # 初始化统计字典
    by_commit = defaultdict(SurvivalStat)  # 按提交 SHA 分组
    by_author = defaultdict(SurvivalStat)  # 按作者身份分组

    # 设置调试日志文件
    debug_log = None
    if debug_log_file:
        debug_log_path = Path(debug_log_file)
        debug_log_path.parent.mkdir(parents=True, exist_ok=True)
        debug_log = debug_log_path.open('w', encoding='utf-8')

    def debug_log_write(msg: str):
        """写入调试日志"""
        if debug_log:
            try:
                # 处理编码问题，替换无法编码的字符
                safe_msg = msg.encode(
                    'utf-8', errors='replace').decode('utf-8')
                debug_log.write(safe_msg + '\n')
                debug_log.flush()
            except Exception as e:
                # 如果还是有问题，使用 ASCII 安全模式
                safe_msg = msg.encode(
                    'ascii', errors='replace').decode('ascii')
                debug_log.write(f"[编码错误] {safe_msg}\n")
                debug_log.flush()

    con.log(f"[yellow]开始计算存活率统计: {old} → {new}[/yellow]")
    con.log(f"[blue]分析文件数量: {len(paths)}[/blue]")
    debug_log_write(f"开始计算存活率统计: {old} → {new}")
    debug_log_write(f"分析文件数量: {len(paths)}")

    # 第一步：统计引入的代码行数 (基于提交日志)
    # 使用 git log --numstat 获取每个提交的代码变更统计
    con.log("[cyan]第一步: 统计引入的代码行数[/cyan]")
    debug_log_write("第一步: 统计引入的代码行数")
    raw = g.log_numstat_no_merges(f"{old}..{new}")
    debug_log_write(f"Git log 输出行数: {len(raw.splitlines())}")

    last_tag = None  # 记录当前处理的提交信息
    introduced_count = 0

    for ln in raw.splitlines():
        # 解析提交信息行 (格式: SHA|作者名|作者邮箱)
        if '|' in ln and ln.count('|') == 2 and ln.startswith(tuple('0123456789abcdef')):
            sha, an, ae = ln.split('|')
            last_tag = (sha, an, ae)
            debug_log_write(f"处理提交: {sha[:8]} by {an}")
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
            introduced_count += ins_i
            if ins_i > 0:
                debug_log_write(f"  +{ins_i} 行引入")

    con.log(f"[green]引入行数统计完成: 总计 {introduced_count} 行[/green]")
    con.log(f"[green]涉及提交数: {len(by_commit)}[/green]")
    debug_log_write(f"引入行数统计完成: 总计 {introduced_count} 行")
    debug_log_write(f"涉及提交数: {len(by_commit)}")

    # 第二步：统计存活的代码行数 (基于反向 blame)
    # 使用 git blame --reverse 查找在版本范围内引入且仍然存在的代码行
    con.log("[cyan]第二步: 统计存活的代码行数[/cyan]")
    debug_log_write("第二步: 统计存活的代码行数")
    survived_count = 0
    processed_files = 0

    for p in paths:
        debug_log_write(f"处理文件: {p}")
        try:
            # 尝试使用反向 blame 获取存活行信息
            braw = g.blame_reverse(old, new, p, ignore_ws)
            debug_log_write(
                f"  blame 输出行数: {len(braw.splitlines()) if braw else 0}")
        except Exception as e:
            # 如果反向 blame 不支持或失败，跳过该文件
            con.log(f"[red]  blame 失败: {e}[/red]")
            debug_log_write(f"  blame 失败: {e}")
            braw = ''

        # 解析 blame 输出，提取存活行信息
        # git blame --reverse 使用简化格式: SHA (作者 日期 行号) 代码内容
        file_survived = 0

        for ln in (braw.splitlines() if braw else []):
            # 解析反向 blame 格式: SHA (作者 日期 行号) 代码内容
            # 检测 SHA：找到第一个非十六进制字符的位置
            sha_end = 0
            for i, c in enumerate(ln):
                if c not in '0123456789abcdef':
                    sha_end = i
                    break

            if sha_end >= 7:  # 至少7个字符的SHA
                sha = ln[:sha_end]
                debug_log_write(f"    解析行: {ln[:80]}...")
                debug_log_write(f"    检测到SHA: {sha}")
                # 提取作者信息 (在括号内)
                if '(' in ln and ')' in ln:
                    paren_start = ln.find('(')
                    paren_end = ln.find(')')
                    if paren_start < paren_end:
                        author_info = ln[paren_start+1:paren_end]
                        debug_log_write(f"    作者信息: {author_info}")
                        # 作者信息格式: "作者名 日期 行号"
                        parts = author_info.split()
                        if len(parts) >= 1:
                            an = parts[0]  # 作者名
                            # 对于邮箱，我们需要从提交信息中获取
                            # 这里先使用作者名，后续可以从提交信息中匹配邮箱
                            ae = "unknown@example.com"  # 临时邮箱

                            debug_log_write(f"    匹配到存活行: SHA={sha}, 作者={an}")
                            # 累加到对应提交和作者的存活行数
                            by_commit[sha].survived_lines += 1
                            by_author[f"{an} <{ae}>"].survived_lines += 1
                            survived_count += 1
                            file_survived += 1
                        else:
                            debug_log_write(f"    作者信息解析失败: {author_info}")
                else:
                    debug_log_write(f"    未找到括号: {ln[:60]}")
            else:
                debug_log_write(f"    非SHA行: {ln[:60]}")

        if file_survived > 0:
            con.log(f"[green]  {p}: {file_survived} 行存活[/green]")
            debug_log_write(f"  {p}: {file_survived} 行存活")
        processed_files += 1

    con.log(f"[green]存活行数统计完成: 总计 {survived_count} 行[/green]")
    con.log(f"[green]处理文件数: {processed_files}[/green]")
    debug_log_write(f"存活行数统计完成: 总计 {survived_count} 行")
    debug_log_write(f"处理文件数: {processed_files}")

    # 显示统计摘要
    total_introduced = sum(
        stat.introduced_lines for stat in by_commit.values())
    total_survived = sum(stat.survived_lines for stat in by_commit.values())
    overall_rate = (total_survived / total_introduced *
                    100) if total_introduced > 0 else 0

    con.log(f"[bold green]存活率统计摘要:[/bold green]")
    con.log(f"[green]  引入行数: {total_introduced}[/green]")
    con.log(f"[green]  存活行数: {total_survived}[/green]")
    con.log(f"[green]  存活率: {overall_rate:.2f}%[/green]")

    debug_log_write(f"存活率统计摘要:")
    debug_log_write(f"  引入行数: {total_introduced}")
    debug_log_write(f"  存活行数: {total_survived}")
    debug_log_write(f"  存活率: {overall_rate:.2f}%")

    # 关闭调试日志文件
    if debug_log:
        debug_log.close()
        con.log(f"[dim]调试日志已保存到: {debug_log_file}[/dim]")

    return by_commit, by_author
