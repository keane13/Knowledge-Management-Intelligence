import os
from google.adk.tools.toolbox_toolset import ToolboxToolset

# Local dev: run the toolbox binary on port 5000:
#   ./toolbox --tools-file=infrastructure/tools/tools.yaml
# Cloud Run: deploy Toolbox as its own (private) service and set TOOLBOX_URL to its URL.
TOOLBOX_URL = os.getenv("TOOLBOX_URL", "http://127.0.0.1:5000").rstrip("/")

if TOOLBOX_URL.startswith("https://"):
    # Private Cloud Run service: authenticate with a Google ID token from the runtime service account
    from toolbox_adk import CredentialStrategy
    toolset = ToolboxToolset(
        server_url=TOOLBOX_URL,
        credentials=CredentialStrategy.workload_identity(target_audience=TOOLBOX_URL),
    )
else:
    toolset = ToolboxToolset(server_url=TOOLBOX_URL)
