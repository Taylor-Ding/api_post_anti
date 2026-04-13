"""
core/db_router.py
数据库路由与查询模块

职责：
  1. 根据 custNo 计算 Hash 值（预留 calculate_hash 供接入真实算法）
  2. 推导目标分库名称（dcdpdb1 ~ dcdpdb4）和分表名称（tb_dpmst_medium_0001 ~ 0008）
  3. 建立 pymysql 连接（使用 DictCursor 保证返回字典列表）
  4. 提供通用动态查询方法，不硬编码任何业务字段名

路由算法说明:
  - hash_result ∈ [1, 8]   → 表后缀 (用 4 位零填充)
  - db_index    = (hash_result - 1) // 2 + 1  → dcdpdb{db_index}
  - 示例:
      hash=1 → dcdpdb1, tb_dpmst_medium_0001
      hash=2 → dcdpdb1, tb_dpmst_medium_0002
      hash=3 → dcdpdb2, tb_dpmst_medium_0003
      ...
      hash=8 → dcdpdb4, tb_dpmst_medium_0008
"""
from __future__ import annotations

import contextlib
from typing import Any, Dict, Generator, List, Optional, Tuple

import psycopg2
import psycopg2.extras

from core.hash_utils import determine_sharding_number_by_cust_no

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ------------------------------------------------------------------ #
#  Hash 计算（预留扩展点）
# ------------------------------------------------------------------ #

def calculate_hash(cust_no: str, total_shards: Optional[int] = None) -> int:
    """
    根据 custNo 计算分片 Hash 值。

    Args:
        cust_no: 客户标识，例如 "C10000001"
        total_shards: 可选的传入分表总数，如果不传则默认读取配置

    Returns:
        int: 范围 [1, total_shards] 的 Hash 结果，直接对应表名后缀数字。
    """
    total = total_shards or settings.total_shards
    
    # 使用与 Java 端一致的 MurmurHash3 算法和取模逻辑提取编号
    hash_result = determine_sharding_number_by_cust_no(cust_no, total)

    if not (1 <= hash_result <= total):
        raise ValueError(
            f"calculate_hash 返回值 {hash_result!r} 超出合法范围 "
            f"[1, {total}]，请检查路由算法实现。"
        )
    return hash_result


# ------------------------------------------------------------------ #
#  路由推导
# ------------------------------------------------------------------ #

def resolve_route(
    cust_no: str,
    total_shards: Optional[int] = None,
    shards_per_db: Optional[int] = None,
    db_prefix: Optional[str] = None,
    table_prefix: Optional[str] = None
) -> Tuple[str, str]:
    """
    根据 custNo 推导目标库名与表名。

    Args:
        cust_no: 客户标识
        total_shards: 可选的环境特有总分表数覆盖
        shards_per_db: 可选的环境特有单库分表数覆盖
        db_prefix: 可选的数据库前缀覆盖
        table_prefix: 可选的分表前缀覆盖

    Returns:
        Tuple[db_name, table_name]:
            - db_name:    如 "dcdpdb2"
            - table_name: 如 "tb_dpmst_medium_0003"
    """
    total_shards = total_shards or settings.total_shards
    shards_per_db = shards_per_db or settings.shards_per_db
    db_prefix = db_prefix or settings.db_prefix
    table_prefix = table_prefix or settings.table_prefix

    hash_result = calculate_hash(cust_no, total_shards)
    db_index = (hash_result - 1) // shards_per_db + 1
    db_name = f"{db_prefix}{db_index}"
    table_name = f"{table_prefix}{hash_result:04d}"

    logger.debug(
        "路由计算 | custNo=%s  hash=%d  →  db=%s  table=%s",
        cust_no, hash_result, db_name, table_name,
    )
    return db_name, table_name


# ------------------------------------------------------------------ #
#  连接管理
# ------------------------------------------------------------------ #

@contextlib.contextmanager
def get_connection(db_name: str) -> Generator[psycopg2.extensions.connection, None, None]:
    """
    上下文管理器：创建并返回指定库的 pymysql 连接，退出时自动关闭。

    用法::

        with get_connection("dcdpdb1") as conn:
            ...

    Args:
        db_name: 数据库名，须与 config.json 中 databases 的 key 一致。

    Yields:
        psycopg2.extensions.connection
    """
    db_cfg = settings.get_db_config(db_name)
    conn: Optional[psycopg2.extensions.connection] = None
    try:
        conn = psycopg2.connect(
            host=db_cfg["host"],
            port=int(db_cfg.get("port", 5432)),
            user=db_cfg["user"],
            password=db_cfg["password"],
            dbname=db_cfg["database"],
            options=f"-c statement_timeout={int(db_cfg.get('connect_timeout', 10))*1000}"
        )
        # Using RealDictCursor for compatibility
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        logger.debug("DB 连接成功 | host=%s db=%s", db_cfg["host"], db_name)
        yield conn
    except psycopg2.Error as exc:
        logger.error("DB 连接失败 | db=%s error=%s", db_name, exc)
        raise
    finally:
        if conn:
            conn.close()
            logger.debug("DB 连接已关闭 | db=%s", db_name)


# ------------------------------------------------------------------ #
#  动态表级别查询配置
# ------------------------------------------------------------------ #

TABLE_QUERY_FIELD_MAP = {
    # 针对 tb_dpmst_medium 实体表，强制使用 medium_no 作为主查询条件过滤字段
    "tb_dpmst_medium": "medium_no",
}


def query_by_keys(
    cust_no: str,
    medium_no: Optional[str] = None,
    extra_conditions: Optional[str] = None,
    extra_params: Optional[tuple] = None,
) -> Dict[str, Any]:
    """
    基于 cust_no 进行分表路由，并根据表配置映射目标查询字段(cust_no 还是 medium_no)。

    Args:
        cust_no:          强制使用客户号(cust_no)计算分片路由和查表（如果表以该条件为主键）。
        medium_no:        如果可用，部分特定表(如 medium) 会强制以此为查询匹配条件。
        extra_conditions: 可选的额外 WHERE 子句片段（不含 WHERE 关键字），
                          例如 "status = %s AND type = %s"。
        extra_params:     与 extra_conditions 对应的参数元组。

    Returns:
        Dict 包含:
            - "db_name":    命中的数据库名
            - "table_name": 命中的表名
            - "rows":       List[Dict]，每行作为一个字典（DictCursor 输出）
    """
    db_name, table_name = resolve_route(cust_no)

    # 从分表名 (例如 tb_dpmst_medium_0005) 剖离出包含业务前缀的基础表名 (tb_dpmst_medium)
    base_table_name = table_name.rsplit('_', 1)[0]
    
    # 动态匹配出该表在数据库中应该根据什么条件查询
    query_field = TABLE_QUERY_FIELD_MAP.get(base_table_name, "cust_no")

    # 指定真正应该使用的参数值
    if query_field == "medium_no" and medium_no:
        actual_query_val = medium_no
    else:
        actual_query_val = cust_no

    # 构造 SQL
    sql = f'SELECT * FROM "{table_name}" WHERE {query_field} = %s'
    params: tuple = (actual_query_val,)
    if extra_conditions:
        sql += f" AND {extra_conditions}"
        params += extra_params or ()

    logger.info("执行查询 | db=%s  sql=%s  params=%s", db_name, sql, params)

    with get_connection(db_name) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            logger.debug("查询明细 | db=%s table=%s 获取结果集: %s", db_name, table_name, rows)
            
            # 使用 list() 返回真正的列表
            rows_list = list(rows) if rows else []
            logger.info("查询完成 | db=%s  table=%s  rows=%d", db_name, table_name, len(rows_list))

    return {
        "db_name": db_name,
        "table_name": table_name,
        "rows": rows_list,
    }


def execute_raw_query(
    db_name: str,
    sql: str,
    params: Optional[tuple] = None,
) -> List[Dict[str, Any]]:
    """
    在指定库上执行任意 SELECT 语句（高级用法，绕过路由推导）。

    Args:
        db_name: 目标数据库名。
        sql:     完整 SQL 语句，使用 %s 占位符。
        params:  参数元组。

    Returns:
        List[Dict]：每行为一个字典。
    """
    logger.info("原始查询 | db=%s  sql=%s  params=%s", db_name, sql, params)
    with get_connection(db_name) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            rows: List[Dict[str, Any]] = cursor.fetchall()
    logger.info("原始查询完成 | db=%s  rows=%d", db_name, len(rows))
    return rows
