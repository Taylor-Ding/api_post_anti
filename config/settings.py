"""
config/settings.py
配置加载与解析模块
负责从 conf/config.json 读取并向全局暴露结构化配置对象
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import sys

# 项目根目录（settings.py 所在的上一层）
if getattr(sys, 'frozen', False):
    _PROJECT_ROOT = Path(sys._MEIPASS)
else:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 默认配置文件路径（可通过环境变量 CONFIG_PATH 覆盖）
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "conf" / "config.json"


class Settings:
    """全局配置管理类（单例访问）"""

    def __init__(self, config_path: str | Path | None = None) -> None:
        path = Path(config_path) if config_path else Path(
            os.environ.get("CONFIG_PATH", str(_DEFAULT_CONFIG_PATH))
        )
        if not path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {path}\n"
                f"请确认 conf/config.json 已正确放置，或通过环境变量 CONFIG_PATH 指定路径。"
            )
        with path.open("r", encoding="utf-8") as f:
            raw: Dict[str, Any] = json.load(f)

        self._raw = raw
        self.databases: Dict[str, Dict[str, Any]] = raw["databases"]
        self.api: Dict[str, Any] = raw["api"]
        self.db_routing: Dict[str, Any] = raw["db_routing"]
        self.diff: Dict[str, Any] = raw["diff"]
        self.logging_cfg: Dict[str, Any] = raw["logging"]

    # ------------------------------------------------------------------ #
    #  数据库配置快捷访问
    # ------------------------------------------------------------------ #
    def get_db_config(self, db_name: str) -> Dict[str, Any]:
        """按库名返回连接配置字典"""
        if db_name not in self.databases:
            raise KeyError(
                f"数据库 '{db_name}' 未在配置文件中定义。"
                f"可用库：{list(self.databases.keys())}"
            )
        return self.databases[db_name]

    # ------------------------------------------------------------------ #
    #  API 配置快捷访问
    # ------------------------------------------------------------------ #
    @property
    def api_url(self) -> str:
        return self.api["base_url"].rstrip("/") + "/" + self.api["endpoint"].lstrip("/")

    @property
    def route_query_url(self) -> str:
        return self.api.get("route_query_url", "http://localhost:8080/testtool/routeQuery")

    @property
    def api_timeout(self) -> int:
        return int(self.api.get("timeout_seconds", 30))

    @property
    def api_headers(self) -> Dict[str, str]:
        return dict(self.api.get("headers", {}))

    # ------------------------------------------------------------------ #
    #  路由配置快捷访问
    # ------------------------------------------------------------------ #
    @property
    def db_prefix(self) -> str:
        return self.db_routing.get("db_prefix", "dcdpdb")

    @property
    def table_prefix(self) -> str:
        return self.db_routing["table_prefix"]

    @property
    def total_shards(self) -> int:
        return int(self.db_routing["total_shards"])

    @property
    def shards_per_db(self) -> int:
        return int(self.db_routing["shards_per_db"])

    # ------------------------------------------------------------------ #
    #  Diff 配置快捷访问
    # ------------------------------------------------------------------ #
    @property
    def diff_ignore_order(self) -> bool:
        return bool(self.diff.get("ignore_order", True))

    @property
    def diff_exclude_regex_paths(self) -> list[str]:
        return list(self.diff.get("exclude_regex_paths", []))

    def __repr__(self) -> str:
        return f"<Settings api_url={self.api_url!r} dbs={list(self.databases.keys())}>"


# ------------------------------------------------------------------ #
#  模块级单例（其他模块 from config.settings import settings 即可使用）
# ------------------------------------------------------------------ #
settings = Settings()
