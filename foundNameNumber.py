import os
import json
import re

# 指定文件夹路径
folder_path = r"D:\桌面\识百草视频1019-1025\识百草视频"
# 输出文件路径
output_path = "foundNameNumber.json"

# 获取文件夹中的所有文件名（不带后缀）
existing_files = {os.path.splitext(file)[0] for file in os.listdir(folder_path)}

# 使用正则表达式匹配类似于 xx1 到 xx10 的文件名
pattern = re.compile(r'^(.*?)(\d{1,2})$')  # 匹配前缀和数字部分

# 定义存储发现的文件名和前缀
found_files = {}
duplicate_files = []  # 存储重复的文件名
out_of_range_files = []  # 存储不在1-10范围的文件名

# 遍历已有文件名并进行匹配
for file in existing_files:
    match = pattern.match(file)
    if match:
        prefix, number = match.groups()
        number = int(number)  # 转换为整数

        if 1 <= number <= 10:
            # 初始化前缀字典
            if prefix not in found_files:
                found_files[prefix] = {}

            # 记录编号的出现次数
            if number not in found_files[prefix]:
                found_files[prefix][number] = 1
            else:
                found_files[prefix][number] += 1
                duplicate_files.append(f"{prefix}{number}")  # 记录重复文件名
        else:
            out_of_range_files.append(f"{prefix}{number}")  # 记录不在1-10范围的文件名

# 找出缺少的文件名
missing_files = []
for prefix, numbers in found_files.items():
    for i in range(1, 11):
        if i not in numbers:
            missing_files.append(f"{prefix}{i}")  # 记录缺少的文件名（不带后缀）

# 将缺少的文件名、重复的文件名和不在1-10范围的文件名写入 JSON 文件
output_data = {
    "missing_files": missing_files,
    "duplicate_files": duplicate_files,
    "out_of_range_files": out_of_range_files
}

# 写入输出文件
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

print(f"缺少的文件名、重复的文件名和不在1-10范围的文件名已输出到 {output_path}")
