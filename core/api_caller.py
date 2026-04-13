"""
core/api_caller.py
HTTP 接口调用层

核心设计原则：
  - 使用 requests 库发起 HTTP 请求
  - **严格保留 None → null 语义**：通过 requests 的 json= 参数传递原始字典，
    由 Python 标准库 json.dumps 负责序列化，None 会被正确转为 null，不做任何
    预处理过滤（不执行 pop/filter/dict comprehension 去除 None 值操作）
  - 完整记录请求 URL、请求体（含 null 字段）、响应码和响应体，便于问题溯源
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests
from requests import Response

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ApiCallError(Exception):
    """接口调用异常，包含状态码和响应文本信息"""

    def __init__(self, url: str, status_code: int, response_text: str) -> None:
        self.url = url
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(
            f"接口调用失败 | url={url}  status={status_code}  body={response_text[:500]}"
        )


class ApiCaller:
    """
    HTTP 接口调用器。

    Usage::

        caller = ApiCaller()
        response_data = caller.post(payload={"custNo": "C10000001", "amount": None})
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Args:
            base_url:      覆盖 config.json 中的 api.base_url（可选）。
            endpoint:      覆盖 config.json 中的 api.endpoint（可选）。
            timeout:       请求超时秒数，默认取 config.json 配置。
            extra_headers: 额外追加到请求头的键值对（可选）。
        """
        if base_url:
            self._url = base_url.rstrip("/")
            if endpoint:
                self._url += "/" + endpoint.lstrip("/")
        else:
            self._url = settings.api_url

        self._timeout = timeout if timeout is not None else settings.api_timeout

        self._headers: Dict[str, str] = dict(settings.api_headers)
        if extra_headers:
            self._headers.update(extra_headers)

    # ------------------------------------------------------------------ #
    #  核心发送方法
    # ------------------------------------------------------------------ #

    def post(
        self,
        payload: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        发送 POST 请求，严格保留报文中所有 None（序列化为 null）。

        ⚠️  **绝不** 在此处或调用前对 payload 执行任何过滤、pop 或
        dict comprehension 去除 None 操作，这会破坏业务报文的完整性。

        Args:
            payload:       请求体字典，None 值将被序列化为 JSON null。
            extra_headers: 本次请求额外追加的请求头（可选）。

        Returns:
            Dict：解析后的 JSON 响应体。

        Raises:
            ApiCallError:  HTTP 状态码非 2xx 时抛出。
            requests.exceptions.RequestException: 网络层异常。
        """
        headers = dict(self._headers)
        if extra_headers:
            headers.update(extra_headers)

        # 用标准库序列化，方便日志记录时展示（不过滤 None）
        payload_json_str = json.dumps(payload, ensure_ascii=False, default=str)

        logger.info(
            "发起 POST 请求 | url=%s\n  Headers: %s\n  Payload: %s",
            self._url,
            json.dumps(headers, ensure_ascii=False),
            payload_json_str,
        )

        try:
            # 直接传 json= 参数，requests 内部使用 json.dumps 序列化
            # None → null 由 Python 标准库保证，无需任何手工处理
            response: Response = requests.post(
                url=self._url,
                json=payload,       # ← 核心：原样传入，绝不预处理
                headers=headers,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout as exc:
            logger.error("请求超时 | url=%s  timeout=%ds", self._url, self._timeout)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("网络连接失败 | url=%s  error=%s", self._url, exc)
            raise
        except requests.exceptions.RequestException as exc:
            logger.error("请求异常 | url=%s  error=%s", self._url, exc)
            raise

        logger.info(
            "收到响应 | url=%s  status=%d\n  Body: %s",
            self._url,
            response.status_code,
            response.text[:2000],  # 防止超大响应体撑爆日志
        )

        if not response.ok:
            raise ApiCallError(
                url=self._url,
                status_code=response.status_code,
                response_text=response.text,
            )

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            logger.error(
                "响应体 JSON 解析失败 | url=%s  raw=%s  error=%s",
                self._url, response.text[:500], exc,
            )
            raise
