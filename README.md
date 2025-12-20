# Fanbox Creator Update Monitor

[English](README_EN.md) | [简体中文](README_zh.md)

A Python script to monitor updates from creators you support or follow on Pixiv Fanbox, with automatic Bark notifications.

## Quick Start

1. Install dependencies:
```bash
pip install -r fanbox_monitor/requirements.txt
```

2. Configure `fanbox_monitor_config.json`:
```json
{
  "cookie": "Your Cookie string",
  "bark_key": "Your Bark key (optional)"
}
```

3. Run:
```bash
cd fanbox_monitor
python monitor.py
```

See [README_EN.md](README_EN.md) for detailed documentation in English, or [README_zh.md](README_zh.md) for Chinese documentation.

