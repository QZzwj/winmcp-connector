# WinMCP Connector

非官方 Windows 连接器，把本机能力通过 [Windows-MCP](https://github.com/CursorTouch/Windows-MCP) 暴露给同一局域网内的 QZdesk 设备。

## 组成

| 文件 | 说明 |
| --- | --- |
| `connector.py` | 连接器界面：发现设备、配对、生成访问密钥、启动和停止引擎 |
| `engine.py` | Windows-MCP 引擎的打包入口 |
| `QZdeskConnector.spec` | 连接器界面的 PyInstaller 配置 |
| `QZdeskMcpEngine.spec` | MCP 引擎的 PyInstaller 配置 |
| `build.ps1` | Windows 一键构建脚本 |
| `main.cpp` / `CMakeLists.txt` | Qt 版界面实现 |

## 构建

要求 Windows 10/11、Python 3.14（含 Tcl/Tk），并保证 `Windows-MCP` 源码与当前目录同级：

```text
parent/
├── Windows-MCP/
└── winmcp-connector/
```

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

产物：

- `dist/QZdeskConnector/QZdeskConnector.exe`
- `QZdeskConnector-Windows.zip`

## 安全说明

连接器只监听配对设备的局域网地址，并使用每次启动随机生成的 Bearer token 保护 HTTP 请求。默认仅开放 `Snapshot`；设备端确认控制请求后，才启用交互类工具。

## 与上游的关系

本项目依赖并打包 [CursorTouch/Windows-MCP](https://github.com/CursorTouch/Windows-MCP)（MIT License）。本项目与 Windows-MCP 上游没有官方关联。

## 命名状态

仓库名为 `winmcp-connector`，当前程序内部仍使用 `QZdeskConnector` 和 `QZdeskMcpEngine` 作为可执行文件名。
