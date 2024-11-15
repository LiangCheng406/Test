import os
import json

def get_filenames_from_folder(folder_path):
    # 获取指定文件夹中的所有文件名
    try:
        filenames = os.listdir(folder_path)
        return filenames
    except FileNotFoundError:
        print(f"文件夹 {folder_path} 不存在。")
        return []

# 示例：指定文件夹路径和输出文件路径
folder_path = r"\\192.168.2.39\e\movie\A图书电影3" # 替换为你的文件夹路径
output_path = "foundDiffName.json"  # 输出结果的文件路径

# 获取文件名列表
filenames = get_filenames_from_folder(folder_path)

# 将结果保存到 JSON 文件中
with open(output_path, 'w', encoding='utf-8') as json_file:
    json.dump(filenames, json_file, ensure_ascii=False, indent=4)

# 输出确认信息
print(f"文件名已保存到 {output_path}")
