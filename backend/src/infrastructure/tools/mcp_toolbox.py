from google.adk.tools.toolbox_toolset import ToolboxToolset

# Make sure to run the toolbox binary on port 5000:
# ./toolbox --tools-file=infrastructure/tools/tools.yaml
toolset = ToolboxToolset(server_url="http://127.0.0.1:5000")
