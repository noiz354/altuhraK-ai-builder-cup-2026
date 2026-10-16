"""C05 deployment entry point.

Exposes the shared MVP app plus the C05 Field Crew / Admin / Agent adapter so
one process serves the QC service that the Next.js app talks to.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from c05_bootstrap import create_app  # noqa: E402

app = create_app(os.environ.get("C05_DB_PATH"))

if __name__ == "__main__":
    import uvicorn

    # Cloud Run reaches the container over the network and can only reach a process
    # bound to 0.0.0.0. Binding to loopback worked locally because the client was on
    # the same host, and would leave the deployed service completely unreachable.
    # Reachability is enforced by ingress policy and in-app RBAC, not by hiding
    # the socket.
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))