"""
core/diff_engine.py
差异比对引擎

核心设计：
  - 强制使用 deepdiff.DeepDiff 进行结构化比对
  - ignore_order=True：忽略列表/多行记录的顺序差异
  - exclude_regex_paths：基于正则表达式排除噪音字段
    （如 update_time、version、trace_id 等动态字段）
  - 提供结构化的比对报告，便于断言和日志记录
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from deepdiff import DeepDiff

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ------------------------------------------------------------------ #
#  结果数据结构
# ------------------------------------------------------------------ #

@dataclass
class DiffReport:
    """
    比对报告。

    Attributes:
        is_equal:        True 表示两份数据在忽略噪音后完全一致。
        diff_detail:     DeepDiff 原始输出（dict 形式），便于序列化和断言。
        excluded_paths:  本次比对使用的排除正则列表。
        before_snapshot: 比对前的原始数据快照（仅存 db_name / table_name / rows）。
        after_snapshot:  比对后的原始数据快照。
        summary:         人类可读的一行摘要。
    """
    is_equal: bool
    diff_detail: Dict[str, Any]
    excluded_paths: List[str]
    before_snapshot: Dict[str, Any]
    after_snapshot: Dict[str, Any]
    summary: str = field(init=False)

    def __post_init__(self) -> None:
        if self.is_equal:
            self.summary = "✅ 数据一致：接口前后数据库状态无核心业务字段变更。"
        else:
            transl = {
                "values_changed": "字段值内容被篡改/修改",
                "dictionary_item_added": "发现异常新增字段",
                "dictionary_item_removed": "发现数据记录丢失",
                "iterable_item_added": "数据集行数增加",
                "iterable_item_removed": "数据集行数减少"
            }
            change_types = list(self.diff_detail.keys())
            keys_zh = [transl.get(k, k) for k in change_types]
            self.summary = (
                f"❌ 数据不一致：检测到 {len(change_types)} 类差异 → {keys_zh}"
            )

    def to_json(self, indent: int = 2) -> str:
        """将报告序列化为 JSON 字符串，便于日志输出和文件持久化。"""
        serializable = {
            "is_equal": self.is_equal,
            "summary": self.summary,
            "excluded_paths": self.excluded_paths,
            "diff_detail": self.diff_detail,
            "before_snapshot": {
                "db_name": self.before_snapshot.get("db_name"),
                "table_name": self.before_snapshot.get("table_name"),
                "row_count": len(self.before_snapshot.get("rows", [])),
            },
            "after_snapshot": {
                "db_name": self.after_snapshot.get("db_name"),
                "table_name": self.after_snapshot.get("table_name"),
                "row_count": len(self.after_snapshot.get("rows", [])),
            },
        }
        return json.dumps(serializable, ensure_ascii=False, indent=indent, default=str)


# ------------------------------------------------------------------ #
#  核心比对函数
# ------------------------------------------------------------------ #

class DiffEngine:
    """
    差异比对引擎，封装 DeepDiff 并注入噪音排除策略。

    Usage::

        engine = DiffEngine()
        report = engine.compare(before_result, after_result)
        if not report.is_equal:
            print(report.to_json())
    """

    def __init__(
        self,
        ignore_order: Optional[bool] = None,
        extra_exclude_regex_paths: Optional[List[str]] = None,
    ) -> None:
        """
        Args:
            ignore_order:
                是否忽略列表顺序，默认从 config.json 中读取。
            extra_exclude_regex_paths:
                在 config.json 配置的白名单之外，本次额外追加的排除路径正则。
        """
        self._ignore_order: bool = (
            ignore_order if ignore_order is not None else settings.diff_ignore_order
        )
        self._exclude_regex_paths: List[str] = list(settings.diff_exclude_regex_paths)
        if extra_exclude_regex_paths:
            self._exclude_regex_paths.extend(extra_exclude_regex_paths)

        logger.debug(
            "DiffEngine 初始化 | ignore_order=%s  exclude_regex_paths=%s",
            self._ignore_order,
            self._exclude_regex_paths,
        )

    def compare(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> DiffReport:
        """
        对比查询结果的前后状态。

        Args:
            before: ``db_router.query_by_cust_no`` 接口触发**前**的返回值，
                    格式: {"db_name": ..., "table_name": ..., "rows": [...]}
            after:  接口触发**后**的查询返回值，格式同上。

        Returns:
            DiffReport 结构化比对报告。
        """
        before_rows: List[Dict] = before.get("rows", [])
        after_rows: List[Dict] = after.get("rows", [])

        logger.info(
            "开始比对 | before_rows=%d  after_rows=%d  exclude_paths=%s",
            len(before_rows),
            len(after_rows),
            self._exclude_regex_paths,
        )

        diff = DeepDiff(
            before_rows,
            after_rows,
            ignore_order=self._ignore_order,
            exclude_regex_paths=self._exclude_regex_paths if self._exclude_regex_paths else None,
            verbose_level=2,
        )

        # DeepDiff 返回自定义 dict-like 对象，转为普通 dict 以便序列化
        diff_dict: Dict[str, Any] = dict(diff)

        is_equal = len(diff_dict) == 0

        report = DiffReport(
            is_equal=is_equal,
            diff_detail=diff_dict,
            excluded_paths=list(self._exclude_regex_paths),
            before_snapshot=before,
            after_snapshot=after,
        )

        if is_equal:
            logger.info("比对结论：%s", report.summary)
        else:
            logger.warning(
                "比对结论：%s\n  差异详情 (JSON):\n%s",
                report.summary,
                report.to_json(),
            )

        return report
