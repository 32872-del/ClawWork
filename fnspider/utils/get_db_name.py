import os
import re


def get_latest_db(folder_path, target_name):
    all_files = os.listdir(folder_path)
    all_files = [z for z in all_files if re.search(r"\d+\.db$", z)]
    this_files = [file for file in all_files if file.startswith(target_name)]
    if not this_files:
        return None
    number = [int(re.findall(r"(\d+)\.db$", z)[0]) for z in this_files]
    number.sort()
    latest = target_name + "_" + str(number[-1]) + ".db"
    return os.path.join(folder_path, latest)


def get_new_db(folder_path, target_name):
    all_files = os.listdir(folder_path)
    all_files = [z for z in all_files if re.search(r"\d+\.db$", z)]
    this_files = [file for file in all_files if file.startswith(target_name)]
    if not this_files:
        new_db = target_name + "_1.db"
    else:
        number = [int(re.findall(r"(\d+)\.db$", z)[0]) for z in this_files]
        number.sort()
        new_db = target_name + "_" + str(number[-1] + 1) + ".db"
    return os.path.join(folder_path, new_db)
