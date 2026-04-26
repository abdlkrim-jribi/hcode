#!/usr/bin/env python3
"""
Hcode Daemon — JSON-RPC stdin/stdout wrapper for the HcodeAgent.

This is the entry point for the standalone daemon process that the
Tauri desktop app spawns and communicates with via line-delimited JSON-RPC.

Usage:
    python run_daemon.py         # Normal mode
    python run_daemon.py --mock  # Mock mode (deterministic responses for testing)
"""

import asyncio
import json
import sys
import os
import signal
import logging
from typing import Optional

# Load .env file so API keys (OPENAI_API_KEY, OPENAI_BASE_URL, etc.) are available
try:
    from dotenv import load_dotenv
    # Search upward from the daemon directory to find the project root .env
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
except ImportError:
    pass

# Add hcode source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('hcode-daemon.log'), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('hcode-daemon')


class JsonRpcDaemon:
    """
    JSON-RPC 2.0 daemon that wraps HcodeAgent.
    Reads requests from stdin, writes responses/notifications to stdout.
    """

    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.agent = None
        self.running = True
        self.current_task_id: Optional[str] = None

    async def initialize(self):
        """Initialize the HcodeAgent."""
        if self.mock_mode:
            logger.info("Starting in MOCK mode")
            return

        try:
            from hcode.core import HcodeAgent
            self.agent = HcodeAgent()
            logger.info("HcodeAgent initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import HcodeAgent: {e}")
            logger.info("Falling back to mock mode")
            self.mock_mode = True

    def send_response(self, id: str, result=None, error=None):
        """Send a JSON-RPC response to stdout."""
        response = {"jsonrpc": "2.0", "id": id}
        if error:
            response["error"] = error
        else:
            response["result"] = result
        self._write(response)

    def send_notification(self, method: str, params=None):
        """Send a JSON-RPC notification (no id) to stdout."""
        notification = {"jsonrpc": "2.0", "method": method}
        if params:
            notification["params"] = params
        self._write(notification)

    def _write(self, obj):
        """Write a JSON object as a single line to stdout."""
        line = json.dumps(obj, ensure_ascii=False)
        sys.stdout.write(line + '\n')
        sys.stdout.flush()

    async def handle_request(self, request: dict):
        """Handle a single JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        logger.info(f"Received: method={method}, id={req_id}")

        try:
            if method == "health":
                self.send_response(req_id, {"status": "running", "mock": self.mock_mode})

            elif method == "run_task":
                await self._handle_run_task(req_id, params)

            elif method == "abort":
                self.current_task_id = None
                self.send_response(req_id, {"status": "aborted"})

            elif method == "approve_plan":
                self.send_notification("phase_change", {"phase": "executing"})
                self.send_response(req_id, {"status": "approved"})

            elif method == "reject_plan":
                self.send_notification("phase_change", {"phase": "idle"})
                self.send_response(req_id, {"status": "rejected"})

            elif method == "accept_patch":
                path = params.get("path", "")
                self.send_response(req_id, {"status": "accepted", "path": path})

            elif method == "reject_patch":
                path = params.get("path", "")
                self.send_response(req_id, {"status": "rejected", "path": path})

            elif method == "rollback_all":
                self.send_response(req_id, {"status": "rolled_back"})

            elif method == "shutdown":
                logger.info("Shutdown requested")
                self.running = False
                if req_id:
                    self.send_response(req_id, {"status": "shutting_down"})

            else:
                self.send_response(req_id, error={
                    "code": -32601,
                    "message": f"Method not found: {method}"
                })

        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            if req_id:
                self.send_response(req_id, error={
                    "code": -32000,
                    "message": str(e)
                })

    async def _handle_run_task(self, req_id: str, params: dict):
        """Handle a run_task request."""
        task = params.get("task", "")
        mode = params.get("mode", "planning")

        self.current_task_id = req_id
        self.send_response(req_id, {"status": "started"})

        if self.mock_mode:
            await self._mock_task_execution(task, mode)
            return

        # Real execution via HcodeAgent
        try:
            self.send_notification("phase_change", {"phase": "thinking"})

            if self.agent:
                result = await self.agent.execute_task(
                    task=task,
                    stream_callback=lambda text: self.send_notification("log", {
                        "line": text, "stream": "stdout"
                    })
                )

                self.send_notification("done", {"result": str(result)})
            else:
                self.send_notification("error", {
                    "message": "Agent not initialized",
                    "suggestion": "Check daemon logs"
                })

        except Exception as e:
            self.send_notification("error", {
                "message": str(e),
                "suggestion": "Check the daemon log for details"
            })

    async def _mock_task_execution(self, task: str, mode: str):
        """Simulate task execution with deterministic responses."""
        import asyncio

        # Phase: Thinking
        self.send_notification("phase_change", {"phase": "thinking"})
        await asyncio.sleep(0.5)

        # Phase: Planning
        self.send_notification("phase_change", {"phase": "planning"})
        await asyncio.sleep(0.3)

        self.send_notification("plan", {
            "markdown": f"# Plan for: {task}\n\n"
                        f"1. Analyze the request\n"
                        f"2. Identify target files\n"
                        f"3. Generate changes\n"
                        f"4. Apply and verify\n\n"
                        f"**Mode**: {mode}\n"
                        f"**Estimated changes**: 1 file"
        })

        if mode == "planning":
            # Wait for approval (in mock, auto-approve after delay)
            await asyncio.sleep(1)

        # Phase: Executing
        self.send_notification("phase_change", {"phase": "executing"})
        await asyncio.sleep(0.5)

        self.send_notification("log", {"line": f"[Mock] Processing task: {task}", "stream": "stdout"})

        self.send_notification("file_patch", {
            "path": "example.py",
            "diff": "@@ -1,3 +1,3 @@\n-# old code\n+# new code",
            "backup": ".hcode/backups/example.py.bak",
            "originalContent": "# old code\nprint('hello')\n",
            "newContent": "# new code\nprint('hello world')\n",
            "aiExplanation": "Updated the comment as requested."
        })

        # Phase: Verifying
        self.send_notification("phase_change", {"phase": "verifying"})
        await asyncio.sleep(0.3)

        self.send_notification("verification", {
            "markdown": "All changes verified successfully.",
            "passed": True,
            "testResults": "1 test passed, 0 failed"
        })

        # Done
        self.send_notification("phase_change", {"phase": "done"})
        self.send_notification("done", {})

    async def run(self):
        """Main event loop — read stdin line by line."""
        await self.initialize()

        self.send_notification("ready", {})
        logger.info("Daemon ready, waiting for requests...")

        loop = asyncio.get_event_loop()

        while self.running:
            try:
                # Read one line from stdin (blocking, run in executor)
                line = await loop.run_in_executor(None, sys.stdin.readline)

                if not line:
                    logger.info("stdin closed, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue

                await self.handle_request(request)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt, shutting down")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

        logger.info("Daemon stopped")


def main():
    mock_mode = '--mock' in sys.argv

    daemon = JsonRpcDaemon(mock_mode=mock_mode)

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        daemon.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    asyncio.run(daemon.run())


if __name__ == '__main__':
    main()
