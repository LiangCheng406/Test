import os
import shutil
import re

def batch_rename_files(input_folder, output_folder, new_name):
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 定义不允许的特殊字符，其他字符均视为允许
    disallowed_characters = r'[?\\/*|":<>]'  # 定义不允许的特殊字符
    max_length = 255  # 文件名最大长度限制

    # 获取所有文件
    files = [f for f in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, f))]

    # 遍历文件并修改名称
    for i, file_name in enumerate(files, start=1):
        # 拆分文件名和后缀
        file_base, file_ext = os.path.splitext(file_name)

        # 检查文件名长度
        if len(file_base) > max_length:
            print(f"文件名 '{file_name}' 超过最大长度限制 ({max_length} 个字符)")
            continue

        # 查找文件名中的非法字符
        invalid_chars = ''.join(set(re.findall(disallowed_characters, file_base)))

        # 如果有不允许的字符，跳过该文件
        if invalid_chars:
            print(f"文件名 '{file_name}' 不符合要求，非法字符: '{invalid_chars}'")
            continue

        # 新文件名：new_name + 数字
        new_file_name = f"{new_name}{i}{file_ext}"

        # 构建输入文件和输出文件的完整路径
        input_file_path = os.path.join(input_folder, file_name)
        output_file_path = os.path.join(output_folder, new_file_name)

        # 复制并重命名文件到目标文件夹
        shutil.copy(input_file_path, output_file_path)

    print(f"所有符合要求的文件已重命名并保存到 {output_folder} ！")

# 示例用法
input_folder_path = r"D:\桌面\宝妈\炒菜视频"  # 输入文件夹路径
output_folder_path = r"D:\桌面\宝妈\炒菜视频1"  # 输出文件夹路径
new_name = "百草"  # 新文件名的前缀

batch_rename_files(input_folder_path, output_folder_path, new_name)
