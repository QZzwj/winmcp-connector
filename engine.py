import importlib.metadata
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logging.getLogger('windows_mcp').setLevel(logging.INFO)

os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ.setdefault('WINDOWS_MCP_PROFILE_SNAPSHOT', '1')
os.environ.setdefault('WINDOWS_MCP_CONTROL_PUSH', 'false')
entry = next(item for item in importlib.metadata.distribution('windows-mcp').entry_points
             if item.group == 'console_scripts' and item.name == 'windows-mcp')
entry.load()()
