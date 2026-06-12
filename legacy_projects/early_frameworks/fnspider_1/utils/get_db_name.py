import os
import re


# def get_latest_db(folder_path, target_name):
#     matching_files = []
#     for file in os.listdir(folder_path):
#         match = re.findall(rf"^(\d{{10}}){target_name}\.db$", str(file))
#         if match:
#             timestamp = int(match[0])
#             matching_files.append((timestamp, file))
#
#     if not matching_files:
#         return None
#     # 根据时间戳降序排序，取第一个（即最大的）
#     matching_files.sort(key=lambda x: x[0], reverse=True)
#
#     return matching_files[0][1]
def get_latest_db(folder_path, target_name):
    all_files = os.listdir(folder_path)
    all_files = [z for z in all_files if re.search(r'\d+\.db$', z)]
    this_files = []
    for file in all_files:
        if file.startswith(target_name):
            this_files.append(file)
    number = [int(re.findall(r'(\d+)\.db$', z)[0]) for z in this_files]
    number.sort()
    latest = target_name + '_' + str(number[-1]) + '.db'
    return os.path.join(folder_path, latest)

def get_new_db(folder_path, target_name):
    all_files = os.listdir(folder_path)
    all_files = [z for z in all_files if re.search(r'\d+\.db$', z)]
    this_files = []
    for file in all_files:
        if file.startswith(target_name):
            this_files.append(file)
    if len(this_files) == 0:
        new_db = target_name + '_1.db'
    else:
        number = [int(re.findall(r'(\d+)\.db$',z)[0]) for z in this_files]
        number.sort()
        last_name = number[-1] + 1
        # print(b)
        new_db = target_name + '_' + str(last_name) + '.db'
    return os.path.join(folder_path, new_db)


