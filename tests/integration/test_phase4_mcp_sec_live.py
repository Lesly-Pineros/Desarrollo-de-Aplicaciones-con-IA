import os

import pytest

from investiq.mcp_sec import handle_message
from investiq.settings import Settings

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.getenv("RUN_LIVE_INTEGRATION") != "1", reason="Activa RUN_LIVE_INTEGRATION=1 solo en el entorno conectado",
)]


@pytest.mark.skipif(not Settings().sec_user_agent.strip() or "@" not in Settings().sec_user_agent,
                    reason="SEC_USER_AGENT con contacto real no configurado")
def test_mcp_sec_filings_tool_against_live_edgar(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'sec-mcp-live.db'}")
    response = handle_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "sec_filings", "arguments": {"symbol": "AAPL", "limit": 2}},
    }, settings)
    result = response["result"]
    assert not result.get("isError")
    filings = result["structuredContent"]["filings"]
    assert filings
    assert all(item["url"].startswith("https://www.sec.gov/Archives/edgar/data/") for item in filings)
