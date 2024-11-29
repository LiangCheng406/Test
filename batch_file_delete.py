import os
import shutil
import logging
from tqdm import tqdm  # 进度条

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,  # 设置日志记录的最低级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)


def delete_folders_by_name(root_dir, target_name):
    """
    遍历指定文件夹及其子文件夹，删除名称包含target_name的文件夹及其内容。
    """
    # 获取所有需要删除的文件夹路径
    folders_to_delete = []
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for dir_name in dirs:
            folder_path = os.path.join(root, dir_name)
            if target_name in dir_name:  # 如果文件夹名称中包含指定的关键字
                folders_to_delete.append(folder_path)

    # 使用 tqdm 显示进度条
    for folder_path in tqdm(folders_to_delete, desc="删除文件夹", unit="个文件夹"):
        try:
            logging.info(f"正在删除文件夹: {folder_path}")
            shutil.rmtree(folder_path)  # 删除文件夹及其中内容
            logging.info(f"文件夹删除成功: {folder_path}")
        except Exception as e:
            logging.error(f"删除文件夹 {folder_path} 时出错: {e}")


if __name__ == "__main__":
    # 指定目标文件夹
    target_folder = r"D:\桌面\素材1\素材1\素材1"

    # 设置要匹配的文件夹名称关键字
    target_folder_name = "低于480包括480"

    if os.path.isdir(target_folder):
        logging.info(f"开始遍历文件夹: {target_folder}")
        delete_folders_by_name(target_folder, target_folder_name)
        logging.info("操作完成。")
    else:
        logging.error("指定的路径不是一个有效的文件夹！")
