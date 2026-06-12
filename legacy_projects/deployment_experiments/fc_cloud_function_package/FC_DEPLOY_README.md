# FC crawler dependencies

Upload these files to the Function Compute code directory:

- `app.py`
- `requirements-fc.txt`
- `install_fc_deps.sh`

Then run in the FC terminal:

```bash
chmod +x install_fc_deps.sh
./install_fc_deps.sh
```

If Chromium cannot start because system libraries are missing, use a custom container image and install Playwright dependencies there.

Start command:

```bash
python3 app.py
```

