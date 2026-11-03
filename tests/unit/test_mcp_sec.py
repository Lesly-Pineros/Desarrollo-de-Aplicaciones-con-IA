import json

from investiq.domain import FilingItem
from investiq.mcp_sec import handle_message, serve
from investiq.settings import Settings


def test_mcp_initialize_list_and_call_use_sec_tool(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'mcp.db'}")
    calls = []

    def fake_sec(session, symbol, settings, *, limit):
        calls.append((symbol, limit))
        return [FilingItem(form="10-K", filing_date="2026-02-01", url="https://www.sec.gov/example",
                           accession="0001-26-000001", source_id="sec:AAPL:0001")], None

    init = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, settings)
    assert init["result"]["capabilities"]["tools"] == {}
    listed = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, settings)
    assert listed["result"]["tools"][0]["name"] == "sec_filings"
    called = handle_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                             "params": {"name": "sec_filings", "arguments": {"symbol": "aapl", "limit": 2}}},
                            settings, fake_sec)
    assert called["result"]["structuredContent"]["filings"][0]["url"].startswith("https://www.sec.gov/")
    assert calls == [("AAPL", 2)]


def test_mcp_rejects_unknown_ticker_and_bad_limit(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'mcp.db'}")
    for args in ({"symbol": "FAKE"}, {"symbol": "AAPL", "limit": 99}):
        response = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                   "params": {"name": "sec_filings", "arguments": args}}, settings)
        assert response["result"]["isError"]


def test_stdio_transport_emits_only_json_rpc_lines():
    class Stream:
        def __init__(self, content=""):
            self.lines = content.splitlines(True)
            self.output = ""
        def __iter__(self):
            return iter(self.lines)
        def write(self, value):
            self.output += value
        def flush(self):
            pass

    source = Stream(json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"}) + "\n")
    target = Stream()
    serve(source, target, Settings())
    assert json.loads(target.output)["result"] == {}
