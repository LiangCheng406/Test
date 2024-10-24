import os
import shutil


def find_and_move_videos_with_2(source_folder, destination_folder,
                                video_extensions=['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']):
    """
    查找源文件夹中名称包含数字'2'的视频文件，并将其移动到目标文件夹。
    如果文件有损坏，则打印错误日志到控制台。

    :param source_folder: 源文件夹路径
    :param destination_folder: 目标文件夹路径
    :param video_extensions: 支持的视频文件扩展名列表
    """
    # 确保目标文件夹存在，如果不存在则创建
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # 遍历源文件夹
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            # 检查文件名是否包含'2'且文件扩展名是视频格式
            if '2' in file and any(file.lower().endswith(ext) for ext in video_extensions):
                source_file = os.path.join(root, file)
                destination_file = os.path.join(destination_folder, file)

                try:
                    # 尝试将文件复制到目标文件夹
                    shutil.copy2(source_file, destination_file)
                    print(f"文件 {file} 已复制到 {destination_folder}")

                except Exception as e:
                    # 捕获并打印错误日志
                    print(f"错误: 无法复制文件 {file}. 错误信息: {e}")


# 使用示例
source_folder = r"D:\桌面\百草\20241026-1101\20241022_DOUYIN_WW\识百草"# 替换为你的源文件夹路径
destination_folder = r"D:\桌面\百草\20241026-1101\20241022_DOUYIN_WW\识百草11"# 替换为目标文件夹路径

find_and_move_videos_with_2(source_folder, destination_folder)
