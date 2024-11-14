import os
import moviepy.editor as mp
from multiprocessing import Pool
import logging

# 日志配置
logging.basicConfig(filename="video_processing_errors.log",
                    level=logging.ERROR,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# 设置视频目录、输出目录和倍速（由用户指定）
input_video_folder = r"D:\桌面\国画\11月国画\input" # 替换为您的视频文件夹路径
output_video_folder = r"D:\桌面\国画\11月国画\input"  # 替换为您的输出文件夹路径
speed_factor = 2.0  # 设置倍速，例如2.0表示2倍速

# 支持的视频格式
supported_formats = (".mp4", ".avi", ".mov", ".mkv")

# 创建输出文件夹（如果不存在）
if not os.path.exists(output_video_folder):
    os.makedirs(output_video_folder)
    print(f"Output folder created: {output_video_folder}")


def process_video(file_path):
    """处理单个视频文件的函数"""
    try:
        # 读取视频
        video = mp.VideoFileClip(file_path)
        # 对视频进行加速处理
        accelerated_video = video.fx(mp.vfx.speedx, speed_factor)

        # 保存新视频到指定输出文件夹
        output_path = os.path.join(output_video_folder, f"accelerated_{os.path.basename(file_path)}")
        accelerated_video.write_videofile(output_path, codec="libx264")

        print(f"Processed {file_path} successfully.")
    except Exception as e:
        # 捕获异常并记录日志
        logging.error(f"Failed to process {file_path}: {e}")
        print(f"Error processing {file_path}, check log for details.")


def get_video_files(folder):
    """获取文件夹中的所有视频文件"""
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(supported_formats)]


def main():
    # 获取文件夹中的所有视频文件
    video_files = get_video_files(input_video_folder)

    if not video_files:
        print("No video files found in the input folder.")
        return

    # 使用多进程处理视频，最多使用4个进程
    with Pool(processes=4) as pool:
        pool.map(process_video, video_files)


if __name__ == "__main__":
    main()
