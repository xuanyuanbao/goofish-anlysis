# Demo 输出说明

这个目录保存了一套固定的可运行 demo 输出，方便你在 Windows 开发环境先看结果，再迁移到 Linux 正式运行。

目录内容包括：

- `generated/data/`：demo SQLite 数据库
- `generated/reports/daily/`：日报 CSV / XLSX
- `generated/reports/weekly/`：周报 CSV / XLSX
- `generated/reports/monthly/`：月报 CSV / XLSX
- `generated/logs/`：demo 运行日志
- `generated/demo_manifest.json`：本次 demo 的生成摘要

如果你想重新生成这套文件，可以执行：

```bash
python demo/generate_demo_bundle.py
```

这条命令会固定使用：

- `fixture` 采集模式
- `sqlite` 数据库
- `2026-03-30` 作为演示日期
- 回补最近 40 天数据
