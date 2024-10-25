import os
import subprocess
from tqdm import tqdm
import logging
from concurrent.futures import ThreadPoolExecutor

# 配置日志记录
logging.basicConfig(filename='logs/video_processing.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def crop_to_resolution(input_folder, output_folder, target_resolution, num_workers=4):
    """
    批量裁剪视频至指定分辨率，并行处理
    :param input_folder: 输入文件夹
    :param output_folder: 输出文件夹
    :param target_resolution: 目标分辨率，如 "1920:1080"
    :param num_workers: 并行处理的线程数量
    """
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 获取文件夹中的所有视频文件
    video_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.flv'))]

    # 检查目标分辨率格式是否正确
    try:
        target_width, target_height = map(int, target_resolution.split(':'))
    except ValueError:
        raise ValueError("目标分辨率格式不正确，请使用 'width:height' 格式，例如 '1920:1080'")

    # 定义处理视频的函数
    def process_video(video_file):
        input_path = os.path.join(input_folder, video_file)
        output_path = os.path.join(output_folder, os.path.splitext(video_file)[0] + '.mp4')  # 统一输出为 .mp4 文件

        # 获取原始视频的宽高
        try:
            probe = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of',
                 'csv=p=0:s=x', input_path],
                capture_output=True, text=True, check=True)

            original_width, original_height = map(int, probe.stdout.strip().split('x'))

            # 确定裁剪宽高，保持比例并从 (0, 0) 开始裁切
            scale_ratio_width = original_width / target_width
            scale_ratio_height = original_height / target_height

            if scale_ratio_width > scale_ratio_height:
                crop_width = int(target_width * scale_ratio_height)
                crop_height = original_height
            else:
                crop_width = original_width
                crop_height = int(target_height * scale_ratio_width)

            # 使用 ffmpeg 命令裁切视频并确保生成的文件可以正常播放
            command = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f'crop={crop_width}:{crop_height}:0:0,scale={target_width}:{target_height}',
                '-c:v', 'libx264',
                '-crf', '23',
                '-c:a', 'copy',
                '-movflags', 'faststart',
                output_path
            ]

            # 执行 ffmpeg 命令并检查输出
            subprocess.run(command, check=True)

        except subprocess.CalledProcessError as e:
            logging.error(f"处理视频 {video_file} 时出错: {str(e)}")
        except Exception as e:
            logging.error(f"处理视频 {video_file} 时发生未预期的错误: {str(e)}")

    # 使用 tqdm 显示进度条并并行处理
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        list(tqdm(executor.map(process_video, video_files), total=len(video_files), desc="Processing videos"))

    print("所有视频处理成功！")


# 示例用法
input_folder_path = r"D:\桌面\百草\20241102-1108\测试11"
output_folder_path = r"D:\桌面\百草\20241102-1108\output"
target_resolution = "1920:1080"  # 目标分辨率

crop_to_resolution(input_folder_path, output_folder_path, target_resolution, num_workers=4)
