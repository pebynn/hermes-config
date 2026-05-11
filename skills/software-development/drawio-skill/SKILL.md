---
name: drawio-skill
description: Generate professional .drawio diagrams from natural language — export to PNG/SVG/PDF. Works with Claude Code, OpenClaw, Hermes Agent, Codex.
version: 1.3.0
author: Agents365
tags: [diagram, drawio, architecture, flowchart, UML, ERD]
allowed-tools:
  - terminal
  - file
  - vision_analyze
when-to-use: |
  User wants to create architecture diagrams, flowcharts, ERDs, UML diagrams, sequence diagrams.
  Trigger when explaining systems with 3+ components.
---
# drawio-skill — 文本转专业图表

从自然语言生成 draw.io 图表，导出 PNG/SVG/PDF。支持架构图、流程图、ERD、UML、时序图等。

## 前提条件

需要安装 draw.io 桌面版 CLI：
```bash
# macOS
brew install --cask drawio
# Linux: 从 https://github.com/jgraph/drawio-desktop/releases 下载
```

## 使用方式

说"画一个XX架构图"或"帮我画个流程图"，我会自动调此技能。

## 工作流程

1. 确认图表类型和输出格式
2. 生成 .drawio XML
3. 导出 PNG 预览
4. 接收反馈修改
5. 最终导出

## 支持的图表类型

架构图、流程图、ERD、UML、时序图、拓扑图、思维导图、组织结构图等。
