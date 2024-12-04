import  os
import subprocess
import pandas as pd
from tqdm import tqdm  # 进度条库
import logging
from datetime import datetime

# 设置日志文件路径
log_folder = r"D:\桌面\素材日志"  # 可以根据需要修改文件夹路径
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

# 设置日志文件名
log_filename = datetime.now().strftime("video_duration_log_%Y%m%d_%H%M%S.log")
log_path = os.path.join(log_folder, log_filename)

# 配置日志
logging.basicConfig(filename=log_path, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_video_duration(file_path):
    """使用 ffprobe 获取视频时长（秒），并过滤无效输出"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # 只提取时长信息（以防返回额外的编码信息）
        duration_str = result.stdout.strip()
        # 过滤掉任何非数字字符
        try:
            duration = float(duration_str)
            logging.info(f"成功获取 {file_path} 时长: {duration} 秒")
            return duration
        except ValueError:
            logging.warning(f"无法解析时长：{duration_str} ({file_path})")
            return 0
    except Exception as e:
        logging.error(f"无法获取 {file_path} 的时长: {e}")
        return 0


def format_duration(seconds):
    """将秒转换为 hh:mm:ss 格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"


def calculate_durations(root_folder):
    """遍历文件夹并统计每个文件夹下的视频文件数量和总时长"""
    results = []
    all_folders = [folder_name for folder_name, _, _ in os.walk(root_folder)]

    for folder_name in tqdm(all_folders, desc="Processing folders", unit="folder"):
        total_duration = 0
        video_count = 0  # 记录视频文件数量
        logging.info(f"正在处理文件夹: {folder_name}")

        # 遍历文件夹中的所有文件
        for file in os.listdir(folder_name):
            if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv')):
                file_path = os.path.join(folder_name, file)
                logging.info(f"处理文件: {file_path}")
                duration = get_video_duration(file_path)
                if duration > 0:
                    total_duration += duration
                    video_count += 1  # 每找到一个视频文件，数量加 1

        # 如果该文件夹下有视频文件，保存该文件夹的统计数据
        if video_count > 0:
            results.append({
                "Folder Path": folder_name,  # 文件夹的完整路径
                "Folder Name": os.path.basename(folder_name),  # 文件夹名称
                "Video Count": video_count,  # 视频文件数量
                "Total Duration (hh:mm:ss)": format_duration(total_duration)  # 总时长
            })
        else:
            logging.info(f"文件夹 {folder_name} 没有视频文件。")

    return results


def save_to_csv(data, output_file):
    """将结果保存为 CSV 文件"""
    # 确保路径存在
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    logging.info(f"结果已保存到 {output_file}")


if __name__ == "__main__":
    # 在此处指定根目录路径
    root_folder = r"D:\桌面\素材2\素材2" # 替换为你的根目录路径
    # 指定生成的 CSV 文件路径和文件名
    output_file = r"D:\桌面\素材统计"

    logging.info("统计时长脚本开始执行...")

    try:
        results = calculate_durations(root_folder)
        save_to_csv(results, output_file)
        logging.info("统计完成！")
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
