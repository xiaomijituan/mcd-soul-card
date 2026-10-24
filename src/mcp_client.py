"""
麦当劳 MCP 客户端（Streamable HTTP）

负责与 https://mcp.mcd.cn 通信，完成 MCP 握手、工具列举与工具调用。
Token 只允许从环境变量读取，禁止硬编码（参赛信息安全要求）。

零依赖实现：仅使用 Python 标准库，clone 下来无需 pip install 即可运行。
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any

MCP_ENDPOINT = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-06-18"
DEFAULT_TIMEOUT = 30

# 简易响应容器，保持与常用 HTTP 库一致的字段访问习惯
class _Resp:
    def __init__(self, status: int, headers: dict[str, str], text: str) -> None:
        self.status_code = status
        self.headers = headers
        self.text = text
        self._json: Any = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        if self._json is None:
            self._json = json.loads(self.text)
        return self._json


class MCPAuthError(Exception):
    """Token 无效或未配置。"""


class MCPRateLimitError(Exception):
    """触发限流（每分钟 600 次上限）。"""


class MCPError(Exception):
    """MCP 返回的业务错误。"""


class McDonaldMCP:
    """麦当劳中国 MCP Server 的轻量客户端。"""

    def __init__(self, token: str | None = None, endpoint: str = MCP_ENDPOINT) -> None:
        self.token = token or os.getenv("MCD_MCP_TOKEN", "").strip()
        if not self.token:
            raise MCPAuthError(
                "未检测到 MCD_MCP_TOKEN。请先到 https://open.mcd.cn/mcp 登录后申请 Token，"
                "再执行 export MCD_MCP_TOKEN='你的Token'。"
            )
        self.endpoint = endpoint
        self.session_id: str | None = None
        self._tools: list[dict[str, Any]] | None = None
        self._request_id = 0

    # ------------------------------------------------------------------ 底层

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=self._headers(),
            method="POST",
        )
        context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT, context=context) as r:
                resp = _Resp(
                    r.status,
                    {k.lower(): v for k, v in r.headers.items()},
                    r.read().decode("utf-8", errors="replace"),
                )
        except urllib.error.HTTPError as exc:
            resp = _Resp(
                exc.code,
                {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])},
                exc.read().decode("utf-8", errors="replace"),
            )
        except urllib.error.URLError as exc:
            raise MCPError(f"网络请求失败：{exc.reason}") from exc

        # 按官方错误码表给出可读提示
        if resp.status_code == 401:
            raise MCPAuthError("MCP Token 无效、已过期或未提供（401）。")
        if resp.status_code == 429:
            raise MCPRateLimitError("触发限流，每分钟最多 600 次请求（429）。")
        if resp.status_code == 403:
            raise MCPAuthError("请求被拒绝（403），请确认 Token 已激活且来源合法。")
        if not resp.ok:
            raise MCPError(f"MCP 请求失败：HTTP {resp.status_code} {resp.text[:300]}")

        new_session = resp.headers.get("mcp-session-id")
        if new_session:
            self.session_id = new_session

        return self._parse(resp)

    def _parse(self, resp: _Resp) -> dict[str, Any]:
        """MCP 可能返回纯 JSON，也可能返回 SSE 流，这里统一处理。"""
        content_type = resp.headers.get("content-type", "")
        text = resp.text

        if "text/event-stream" in content_type:
            for line in text.splitlines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data:
                        try:
                            parsed = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        # 握手响应可能先返回 endpoint 事件，这里跳过
                        if "result" in parsed or "error" in parsed:
                            return parsed
            raise MCPError("SSE 响应中未解析到有效数据。")

        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise MCPError(f"响应不是合法 JSON：{text[:300]}") from exc

    # ------------------------------------------------------------------ 握手

    def initialize(self) -> dict[str, Any]:
        result = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                 "capabilities": {},
                    "clientInfo": {
                        "name": "mcd-soul-card",
                        "version": "1.0.0",
                    },
                },
            }
        )
        # 通知服务端初始化完成（无 id，不需要响应）
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except MCPError:
            # 部分服务端不要求该通知，忽略即可
            pass
        return result

    def _ensure_ready(self) -> None:
        if self.session_id is None:
            self.initialize()

    # ------------------------------------------------------------------ 工具

    def list_tools(self, refresh: bool = False) -> list[dict[str, Any]]:
        """列出 MCP Server 当前开放的全部工具。"""
        if self._tools is not None and not refresh:
            return self._tools

        self._ensure_ready()
        result = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
                "params": {},
            }
        )

        if "error" in result:
            raise MCPError(str(result["error"]))
        self._tools = result.get("result", {}).get("tools", [])
        return self._tools

    def tool_names(self) -> list[str]:
        return [t.get("name", "") for t in self.list_tools()]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """
        调用指定 MCP 工具。

        返回工具的结构化内容：优先取 content[0].text 中的 JSON，
        若不是 JSON 则原样返回文本。
        """
        self._ensure_ready()
        result = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {},
                },
            }
        )

        if "error" in result:
            err = result["error"]
            raise MCPError(f"{name} 调用失败：[{err.get('code')}] {err.get('message')}")

        payload = result.get("result", {})
        if payload.get("isError"):
            raise MCPError(f"{name} 返回错误：{payload}")

        contents = payload.get("content", [])
        texts: list[str] = []
        for item in contents:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif item.get("type") == "json":
                return item.get("json")

        if not texts:
            return payload

        raw = "\n".join(texts).strip()
        return self._extract_payload(raw)

    @staticmethod
    def _extract_payload(raw: str) -> Any:
        """
        麦当劳 MCP Server 的响应是 Markdown 包装：

            # API Response Information
            ...
            ## Response Structure
            <字段说明>
            ## Original Response
            {"success":true,...,"data":{...}}

        真正可用的数据在 `## Original Response` 之后。这里统一把它提取成
        JSON 对象；提取失败则原样返回文本。
        """
        s = raw.strip()
        if not s:
            return raw

        # 情况 1：本身就是 JSON
        try:
            return McDonaldMCP._deep_parse(json.loads(s))
        except json.JSONDecodeError:
            pass

        # 情况 2：Markdown 包装
        marker = "## Original Response"
        idx = s.find(marker)
        if idx >= 0:
            tail = s[idx + len(marker):].strip()
            if tail.startswith("```"):
                # 去掉代码围栏
                parts = tail.split("```")
                tail = parts[1] if len(parts) > 1 else tail[3:]
                tail = tail.strip()
                if tail[:4].lower() == "json":
                    tail = tail[4:].strip()
            try:
                return McDonaldMCP._deep_parse(json.loads(tail))
            except json.JSONDecodeError:
                pass

        # 情况 3：扫描第一个可解析的 JSON 对象
        # 用 raw_decode 只解析 JSON 前缀，容忍其后跟随的说明文字。
        # 只接受 '{' 开头且结果为 dict —— 说明文字里常出现 `data[].xxx`
        # 这类方括号片段，不能当成 JSON 数组。
        decoder = json.JSONDecoder()
        for i, ch in enumerate(s):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(s[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return McDonaldMCP._deep_parse(obj)

        return raw

    @staticmethod
    def _deep_parse(obj: Any, depth: int = 0) -> Any:
        """
        递归解析「被字符串化的嵌套 JSON」。

        麦当劳 MCP 的响应存在多层包装：外层是 JSON，
        而 `data` 字段的值又是一个 JSON 字符串。
        这里统一把这类嵌套字符串还原成真正的对象。
        """
        if depth > 5:
            return obj
        if isinstance(obj, str):
            s = obj.strip()
            if len(s) > 1 and s[0] in "{[":
                try:
                    return McDonaldMCP._deep_parse(json.loads(s), depth + 1)
                except json.JSONDecodeError:
                    return obj
            return obj
        if isinstance(obj, dict):
            return {k: McDonaldMCP._deep_parse(v, depth + 1) for k, v in obj.items()}
        if isinstance(obj, list):
            return [McDonaldMCP._deep_parse(v, depth + 1) for v in obj]
        return obj

    def __repr__(self) -> str:  # pragma: no cover
        return f"<McDonaldMCP endpoint={self.endpoint} session={self.session_id}>"
