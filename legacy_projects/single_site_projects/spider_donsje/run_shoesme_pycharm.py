import os
import runpy


BASE_DIR = os.path.dirname(__file__)

defaults = {
    "PYTHONUNBUFFERED": "1",
    "SHOESME_BOT_HEADLESS": "0",
    "SHOESME_BOT_BATCH": "1",
    "SHOESME_BOT_WAIT": "5",
    "SHOESME_BOT_CACHE": "1",
    "SHOESME_GOODS_FIRST": "1",
}

for key, value in defaults.items():
    os.environ.setdefault(key, value)

os.chdir(BASE_DIR)
runpy.run_path(os.path.join(BASE_DIR, "3_shoesme_botasaurus.py"), run_name="__main__")
