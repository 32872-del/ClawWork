# Git Boundary

This project is a private runnable crawler framework. Git should capture the code and runtime assets needed to rebuild the crawler environment, but not daily generated data.

## Commit

- `fnspider/` framework source
- `fnspider/clash/` private proxy runtime files
- root site crawler scripts such as `29_obi.py` and `67_lomar.py`
- repair scripts such as `46_11teamsports_repair_images.py`
- `tools/` utility scripts
- `study/` learning and engineering notes
- project reports and handoff documents
- `requirements.txt`
- `.env.example`

## Ignore

- `goods/`: generated SQLite output databases
- `goods_cache/`: HTTP/page cache
- `downloadimg/`: downloaded images
- `out/` and `output/`: probes, debug HTML, generated scans
- `upload/`: generated spreadsheets and upload files
- `logs/` and `error_logs/`: run logs and screenshots
- `browser_profiles/`: browser user data and auth state
- `runtime_env/`, `.venv/`, `venv/`: local Python environments
- `__pycache__/`: Python bytecode
- `*.zip`: backup packages

## Before Push Checklist

```powershell
git status --short
git add .
git status --short
```

Confirm the staged files include crawler scripts and framework files, and do not include generated databases, cache folders, downloaded images, logs, browser profiles, or zip backups.
