"""
main.py
入口执行脚本：查-发-查-比 自动化平台
"""
from __future__ import annotations

import sys
from utils.logger import get_logger
from core.pipeline import TestPipeline

logger = get_logger(__name__)

logger = get_logger(__name__)


def extract_routing_key(payload: dict) -> str | None:
    """从请求主体中抽取出具体的客户号或介质号供后续路由打标查库使用"""
    tx_header = payload.get("txHeader", {})
    
    # 规则 1：验证键值是否在字典中
    if "mainMapElemntInfo" not in tx_header:
        raise ValueError("严重错误：报文 txHeader 中缺失 mainMapElemntInfo 字段")
        
    main_info = tx_header.get("mainMapElemntInfo")
    
    # 如果允许其为 "" 或 null
    if not main_info:
        logger.info("提示：mainMapElemntInfo 字段存在，但值为空或 null")
        return None
        
    # 规则 2：04 开头，后续值为 custNo
    if main_info.startswith("04"):
        cust_no = main_info[2:]
        if not cust_no:
            raise ValueError("异常：mainMapElemntInfo 字段以 04 开头，但后续没有客户号字符串信息")
        logger.info("✅ 成功解析 mainMapElemntInfo 获取到客户号(custNo): %s", cust_no)
        return cust_no
        
    # 规则 3：05 开头，后续值为 mediumNo
    elif main_info.startswith("05"):
        medium_no = main_info[2:]
        if not medium_no:
            raise ValueError("异常：mainMapElemntInfo 字段以 05 开头，但后续没有介质号字符串信息")
        logger.info("✅ 成功解析 mainMapElemntInfo 获取到介质号(mediumNo): %s", medium_no)
        return medium_no
        
    # 未知前提的兜底抛错
    else:
        raise ValueError(f"异常：无法识别的 mainMapElemntInfo 头部前缀标识: {main_info}")


def main() -> None:
    logger.info("====== 查-发-查-比 自动化核对工具系统启动 ======")

    # 1. 初始化 Pipeline
    pipeline = TestPipeline()

    # 2. 准备模拟测试数据
    api_payload = {
        "txBody": {
            "txEntity": {
                "inputModeCode": "2",
                "coreTxFlag": "00000000000000",
                "mediumNo": "6217991000103398751"
            },
            "txComni": {
                "accountingDate": "20231026"
            },
            "txComn7": {
                "custNo": "00400022300118",
                "teschnlCustNo": "4067745905991"
            },
            "txComn8": {
                "busiSendSysOrCmptNo": "99100060000"
            },
            "txComn1": {
                "curQryReqNum": 10,
                "bgnIndexNo": 1
            },
            "txComn2": {
                "oprTellerNo": "0000000000"
            }
        },
        "txHeader": {
            "msgrptMac": "{{msgrptMac}}",
            "globalBusiTrackNo": "{{globalBusiTrackNo}}",
            "subtxNo": "{{subtxNo}}",
            "txStartTime": "{{txStartTime}}",
            "txSendTime": "{{txSendTime}}",
            "busiSendInstNo": "11005293",
            "reqSysSriNo": "20231026104615991000648028791662",
            "msgAgrType": "1",
            "startSysOrCmptNo": "99100060000",
            "targetSysOrCmptNo": "1022199",
            "resvedInputInfo": "",
            "mainMapElemntInfo": "056217991000103398751",
            "pubMsgHeadLen": "0",
            "servVerNo": "10000",
            "servNo": "10221997100",
            "msgrptTotalLen": "0",
            "dataCenterCode": "H",
            "servTpCd": "1",
            "msgrptFmtVerNo": "10000",
            "embedMsgrptLen": "0",
            "sendSysOrCmptNo": "99700040001",
            "startChnlFgCd": "15",
            "tenantId": "DEV1"
        }
    }

    # 3. 触发核心链路
    try:
        # Step 3.1: 抽取需要路由校验查表的 custNo 或 mediumNo
        routing_key = extract_routing_key(api_payload)
        
        # TODO: 后续迭代优化项（多表动态查询条件适配）
        # 1. 目前底层查询默认使用 `cust_no = %s` 进行条件过滤。
        # 2. 后续需要支持按表配置查询键：例如 `tb_dpmst_medium` 使用 `medium_no` 作为查询字段。
        # 3. 当从报文 `mainMapElemntInfo` 里仅提取到 `mediumNo` 时，若某些表或路由算法强依赖 `custNo`，
        #    需要增加一层中间查库逻辑（根据 `mediumNo` 到表里反查出 `custNo`）。
        # Step 3.2: 根据拿到的标识向下驱动查-发-查-比主链路
        report = pipeline.run_verify(
            cust_no=routing_key,
            payload=api_payload,
            # 可根据真实业务诉求追加条件，如 db_extra_cond="record_status != 9"
        )
        
        if not report.is_equal:
            logger.warning(
                "\n--- ⚠️ 数据出现核心字段变更 ---\n%s",
                report.to_json()
            )
        else:
            logger.info("✅ 测试通过：数据前后状态除噪音字段外完全一致！")
            
    except Exception as exc:
        logger.error("❌ main: 执行流出现异常中断: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
