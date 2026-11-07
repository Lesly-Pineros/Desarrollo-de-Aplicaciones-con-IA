"""Minimal MCP stdio server exposing the existing SEC filings tool."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from sqlmodel import Session

from investiq.data.database import create_db, make_engine
from investiq.domain import FilingItem
from investiq.instruments import INSTRUMENT_BY_SYMBOL
from investiq.providers.sec import sec_docs
from investiq.settings import Settings

SERVER_INFO = {"name": "investiq-sec-filings", "version": "0.2.0"}
TOOL = {
    "name": "sec_filings",
    "description": "Consulta filings verificables de la SEC para un símbolo cubierto.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Símbolo cubierto, por ejemplo AAPL."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        },
        "required": ["symbol"],
        "additionalProperties": False,
    },
}


def _tool_result(arguments: Any, settings: Settings,
                 fetch: Callable = sec_docs) -> dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) - {"symbol", "limit"}:
        return {"isError": True, "content": [{"type": "text", "text": "Parámetros inválidos para sec_filings."}]}
    symbol = arguments.get("symbol")
    limit = arguments.get("limit", 5)
    if not isinstance(symbol, str) or not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10:
        return {"isError": True, "content": [{"type": "text", "text": "Indica un símbolo y un límite entero entre 1 y 10."}]}
    symbol = symbol.strip().upper()
    if symbol not in INSTRUMENT_BY_SYMBOL:
        return {"isError": True, "content": [{"type": "text", "text": "Símbolo fuera del universo cubierto."}]}
    engine = create_db(make_engine(settings.database_url))
    try:
        with Session(engine) as session:
            filings, reason = fetch(session, symbol, settings, limit=limit)
    except Exception:
        return {"isError": True, "content": [{"type": "text", "text": "No se pudo completar la consulta de filings de la SEC."}]}
    payload = {
        "symbol": symbol,
        "filings": [item.model_dump(mode="json") if isinstance(item, FilingItem) else item for item in filings],
        "notice": reason,
    }
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "structuredContent": payload}


def handle_message(message: dict[str, Any], settings: Settings,
                   fetch: Callable = sec_docs) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if not method:
        return None
    if method == "initialize":
        result = {"protocolVersion": message.get("params", {}).get("protocolVersion", "2024-11-05"),
                  "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}
    elif method == "notifications/initialized":
        return None
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        params = message.get("params", {})
        if params.get("name") != "sec_filings":
            result = {"isError": True, "content": [{"type": "text", "text": "Herramienta desconocida."}]}
        else:
            result = _tool_result(params.get("arguments", {}), settings, fetch)
    else:
        if request_id is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Método no encontrado."}}
    if request_id is None:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(input_stream=None, output_stream=None, settings: Settings | None = None) -> None:
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    settings = settings or Settings()
    for line in input_stream:
        try:
            message = json.loads(line)
            response = handle_message(message, settings)
        except (json.JSONDecodeError, AttributeError, TypeError):
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON-RPC inválido."}}
        if response is not None:
            output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
            output_stream.flush()


if __name__ == "__main__":
    serve()
