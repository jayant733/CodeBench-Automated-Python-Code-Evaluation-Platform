import asyncio
import logging
import httpx
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from pydantic import AnyUrl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_mcp_test():
    url = "http://127.0.0.1:8000/mcp/"
    logger.info(f"Connecting to MCP server at {url}")
    
    try:
        # Check if the server is up
        async with httpx.AsyncClient() as c:
            r = await c.get("http://127.0.0.1:8000/health")
            if r.status_code != 200:
                logger.error("FastAPI server is not responding to /health. Start it with `python -m ai_code_evaluator.api`.")
                return
    except Exception as e:
        logger.error(f"Cannot connect to server: {e}")
        return

    # In MCP v2 with HTTP transport, we use the sse_client connector to establish the connection
    try:
        async with sse_client(url=url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                logger.info("Initializing MCP Session...")
                await session.initialize()
                logger.info("Successfully initialized MCP session.")
                
                # List tools
                logger.info("Discovering tools...")
                tools = await session.list_tools()
                
                tool_names = [t.name for t in tools.tools]
                logger.info(f"Available tools: {tool_names}")
                
                assert "get_task" in tool_names, "get_task tool not found!"
                assert "evaluate_code" in tool_names, "evaluate_code tool not found!"
                
                logger.info("Tool discovery successful!")
                
                # We won't test invocation directly here to keep the smoke test fast
                # and avoid needing Docker for `evaluate_code`, but we proved the
                # MCP connection and capabilities exchange works.
                logger.info("MCP external validation smoke test passed successfully.")
                
    except Exception as e:
        logger.error(f"MCP test failed: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(run_mcp_test())
