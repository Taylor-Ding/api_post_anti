"""
core/pipeline.py
查-发-查-比 自动化调度流水线

负责全业务流程串联：
  1. 查：调用 db_router 查接口前状态
  2. 发：调用 api_caller 发 HTTP 请求
  3. 查：调用 db_router 查接口后状态
  4. 比：调用 diff_engine 对比前后差异
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.api_caller import ApiCaller
from core.db_router import query_by_keys, resolve_route, get_connection
from core.diff_engine import DiffEngine, DiffReport
from utils.logger import get_logger

logger = get_logger(__name__)


class TestPipeline:
    """自动化测试核对流水线编排器"""

    def __init__(self) -> None:
        self.api_caller = ApiCaller()
        self.diff_engine = DiffEngine()

    def run_verify(
        self,
        cust_no: str,
        payload: Dict[str, Any],
        medium_no: Optional[str] = None,
        target_url: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        db_extra_cond: Optional[str] = None,
        db_extra_params: Optional[tuple] = None,
    ) -> Tuple[DiffReport, Dict[str, Any]]:
        """
        执行一条完整的查-发-查-比链路。

        Args:
            cust_no:         客户号，强制用于 DB 分片计算。如果从 payload 拿到就是客户号，直接传这里；如果拿到是介质号，通过反查后得到的客户号传这里。
            payload:         业务 HTTP POST 的请求体，不可随意过滤 None！
            medium_no:       可选，原始报文中的介质号（如有）。
            target_url:      前端透传过来的业务接口真实目标 URL（如果为空则使用配置值）。
            extra_headers:   可选，向业务接口传递额外的请求头。
            db_extra_cond:   可选，查表时的额外条件（例如 "status = %s"）。
            db_extra_params: 可选，查表时的额外条件参数。

        Returns:
            Tuple[DiffReport, Dict[str, Any]]: (对比结果报告, API 响应体)
        """
        logger.info("=" * 60)
        logger.info("🚀 启动自动化核稳流水线 | custNo(sharding): %s", cust_no)
        
        # 动态更新 api_caller
        if target_url:
            self.api_caller = ApiCaller(base_url=target_url, endpoint="")
            
        logger.info("=" * 60)

        # ------------------------------------------------------------------
        # STEP 1: 查 (Pre-Query)
        # ------------------------------------------------------------------
        logger.info(">>> [1/4] 查询接口调用前的数据状态...")
        before_snapshot = query_by_keys(
            cust_no=cust_no,
            medium_no=medium_no,
            extra_conditions=db_extra_cond,
            extra_params=db_extra_params,
        )

        # ------------------------------------------------------------------
        # STEP 2: 发 (API Call)
        # ------------------------------------------------------------------
        logger.info(">>> [2/4] 触发业务网关接口...")
        try:
            api_response = self.api_caller.post(
                payload=payload,
                extra_headers=extra_headers,
            )
            # 可选：对 api_response 的基础字段做防呆断言或打印
            logger.info("接口返回标志: code=%s, msg=%s", api_response.get("code"), api_response.get("msg"))
        except Exception as exc:
            logger.error("❌ 业务接口调用异常中断，Pipeline 终止！报错：%s", exc)
            raise

        # ==================================================================
        # [TODO: MOCK DEMO TO BE DELETED] 模拟业务系统的 SQL 数据变更
        # 说明：根据要求在第三步查询前模拟业务层面对数据库记录做出了修改。
        # 遵循 cust_no 路由算出分库分表并落键 medium_no
        # ==================================================================
        if medium_no:
            try:
                mock_db_name, mock_table_name = resolve_route(cust_no)
                with get_connection(mock_db_name) as conn:
                    with conn.cursor() as cursor:
                        # 确保替换为当前分片表的表名
                        mock_sql = f"update \"{mock_table_name}\" set medium_print_no = '12312321' where medium_no = %s"
                        logger.warning("🔨 [DEMO MOCK] 模拟篡改数据 SQL -> %s", mock_sql)
                        cursor.execute(mock_sql, (medium_no,))
                    conn.commit()
            except Exception as mock_err:
                logger.error("🔨 [DEMO MOCK] 篡改数据报错被压制: %s", mock_err)
        # ==================================================================

        # ------------------------------------------------------------------
        # STEP 3: 查 (Post-Query)
        # ------------------------------------------------------------------
        logger.info(">>> [3/4] 查询接口调用后的数据状态...")
        after_snapshot = query_by_keys(
            cust_no=cust_no,
            medium_no=medium_no,
            extra_conditions=db_extra_cond,
            extra_params=db_extra_params,
        )

        # ------------------------------------------------------------------
        # STEP 4: 比 (Diff)
        # ------------------------------------------------------------------
        logger.info(">>> [4/4] 启动 DeepDiff 对比分析引擎...")
        report = self.diff_engine.compare(before=before_snapshot, after=after_snapshot)

        logger.info("🏁 流水线执行结束 | 结论 -> %s", report.is_equal)
        logger.info("=" * 60)

        return report, api_response
