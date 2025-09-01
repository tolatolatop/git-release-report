from pydantic import BaseModel, Field
from typing import List, Optional


class CLIOptions(BaseModel):
    repo: str
    old: str
    new: str
    preset: str = Field("all", description="all|A|B|C|D|E|F")
    include: List[str] = []
    exclude: List[str] = []
    ignore_ws: bool = True
    rename: int = 90
    copy: int = 80
    first_parent: bool = False
    mailmap: Optional[str] = None
    bot_filter: Optional[str] = None
    out: str = "out"
