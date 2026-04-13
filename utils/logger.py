"""
utils/logger.py
日志管理模块

特性：
- 同时输出到控制台（StreamHandler）和日志文件（RotatingFileHandler）
- 日志文件存放于 logs/sync_test.log，支持按大小滚动，Linux 下可用 tail -f 实时追踪
- 日志级别、格式、文件路径均从 config.json 读取
- 提供 get_logger(name) 入口函数供各模块直接使用
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ------------------------------------------------------------------ #
#  延迟导入 settings，避免循环依赖
# ------------------------------------------------------------------ #
_initialized = False
_root_logger_name = "api_check"


def _init_logging() -> None:
    """初始化日志系统（幂等，仅执行一次）"""
    global _initialized
    if _initialized:
        return

    # 延迟导入，防止循环依赖
    from config.settings import settings  # noqa: PLC0415

    cfg = settings.logging_cfg

    level_name: str = cfg.get("level", "DEBUG").upper()
    level = getattr(logging, level_name, logging.DEBUG)

    fmt = cfg.get("format", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    date_fmt = cfg.get("date_format", "%Y-%m-%d %H:%M:%S")
    formatter = logging.Formatter(fmt=fmt, datefmt=date_fmt)

    # 项目根目录下的 logs/ 文件夹
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / cfg.get("log_dir", "logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / cfg.get("log_filename", "sync_test.log")
    max_bytes: int = int(cfg.get("max_bytes", 50 * 1024 * 1024))  # 默认 50MB
    backup_count: int = int(cfg.get("backup_count", 10))

    root = logging.getLogger(_root_logger_name)
    root.setLevel(level)

    # 避免重复注册 Handler（热重载场景）
    if root.handlers:
        root.handlers.clear()

    # ── 控制台 Handler ──────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # ── 文件 Handler（按大小滚动）─────────────────────────────────
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root.propagate = False

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    获取具名子 Logger。

    用法::

        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("模块初始化完成")

    Args:
        name: 通常传入 ``__name__``，用于标识日志来源模块。

    Returns:
        logging.Logger 实例，已挂载到根日志器层级。
    """
    _init_logging()
    return logging.getLogger(f"{_root_logger_name}.{name}")
