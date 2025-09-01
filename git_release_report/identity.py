import re
from typing import Optional


def is_bot(name: str, email: str, pattern: Optional[str]) -> bool:
    if not pattern:
        return False
    return re.search(pattern, f"{name} {email}", flags=re.IGNORECASE) is not None
