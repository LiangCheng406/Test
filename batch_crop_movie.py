import os
import subprocess
from pathlib import Path
import platform
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import time
import logging
import threading

# 设置日志记录
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

def log(message):
    """打印并记录日志信息"""
    print(message)
    logging.info(message)  # 将日志记录到 log.txt


def check_nvenc_support():
    """
    检查系统是否支持 NVIDIA NVENC 和 CUDA 加速
    :return: True if NVENC and CUDA are supported, False otherwise
    """
    try:
        # 检查 NVENC 编码器是否支持
        nvenc_result = subprocess.run(["ffmpeg", "-encoders"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if b"h264_nvenc" not in nvenc_result.stdout:
            log("未检测到 NVIDIA NVENC 支持。")
            return False

        # 检查 CUDA 是否可用
        cuda_result = subprocess.run(["ffmpeg", "-hwaccels"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if b"cuda" in cuda_result.stdout:
            log("NVIDIA NVENC 和 CUDA 支持已检测到。")
            return True
        else:
            log("未检测到 CUDA 支持。")
            return False

    except Exception as e:
        log(f"检查 NVENC 和 CUDA 支持时出错: {e}")
        return False


def format_seconds(seconds):
    """将秒数格式化为 hh:mm:ss 格式"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def get_video_resolution(input_file):
    """获取视频的分辨率"""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height", "-of", "csv=s=x:p=0", input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        log(f"获取分辨率失败: {result.stderr.decode()}")
        return None, None
    resolution = result.stdout.decode().strip().split('x')
    return int(resolution[0]), int(resolution[1])


def get_video_pix_fmt(input_file):
    """获取视频的像素格式"""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=pix_fmt", "-of", "default=noprint_wrappers=1:nokey=1", input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        log(f"获取像素格式失败: {result.stderr.decode()}")
        return None
    return result.stdout.decode().strip()


def crop_video(input_file, output_file, start_time, end_time, use_cuda=False):
    """
    调用ffmpeg裁剪视频时长，去掉音轨和字幕轨，并按分辨率裁剪内容，同时启用 NVIDIA NVENC 硬件加速（如可用）。
    """
    width, height = get_video_resolution(input_file)
    if width is None or height is None:
        log(f"无法获取视频分辨率: {input_file}")
        return

    pix_fmt = get_video_pix_fmt(input_file)
    if pix_fmt is None:
        log(f"无法获取视频像素格式: {input_file}")
        return

    # 保留视频下方90%的部分，裁剪上方10%
    crop_height = int(height * 1)
    crop_y = int(height * 0)  # 从上方10%的位置开始裁剪

    # 计算目标5:4的宽高
    target_aspect_ratio = 9 / 16
    target_width = width
    target_height = int(width / target_aspect_ratio)

    # 如果裁剪后高度大于原始高度，则调整宽度
    if target_height > crop_height:
        target_height = crop_height
        target_width = int(crop_height * target_aspect_ratio)

    # 计算左右裁剪边界
    crop_x = (width - target_width) // 2

    cmd = 'ffmpeg'
    if platform.system() == 'Windows':
        cmd += ".exe"

    # 创建一个临时的进度文件路径
    progress_file = "progress.log"

    # 构建视频滤镜，强制将 10-bit 视频转换为 8-bit
    filters = f"crop={target_width}:{target_height}:{crop_x}:{crop_y}"
    if 'yuv420p10le' in pix_fmt or 'yuv422p10le' in pix_fmt or 'yuv444p10le' in pix_fmt:
        filters += ",format=yuv420p"  # 强制转换为 8-bit 色深

    # 构建 FFmpeg 命令，根据硬件支持决定是否使用 CUDA 加速
    command = [
        cmd,
        '-fflags', '+genpts',
        '-loglevel', 'error',
        '-progress', progress_file,  # 记录进度
        '-ss', format_seconds(start_time),
        '-to', format_seconds(end_time),
        '-i', input_file,
        '-vf', filters,
        '-an',
        '-sn',
        '-c:v', 'libx264',  # 使用 CPU 模式的 libx264 编码器
        '-preset', 'fast',
        '-b:v', '5M',
        output_file
    ]

    # 创建一个线程读取进度文件
    threading.Thread(target=monitor_progress, args=(progress_file,), daemon=True).start()

    # 执行FFmpeg命令
    subprocess.run(command, check=True)

    # 删除进度文件
    if os.path.exists(progress_file):
        os.remove(progress_file)


def monitor_progress(progress_file):
    """
    读取并解析 progress 文件，记录当前的帧率信息
    """
    while os.path.exists(progress_file):
        time.sleep(1)  # 每秒读取一次
        with open(progress_file, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if "fps=" in line:  # 查找 fps 字段
                    fps = line.split('=')[1].strip()
                    log(f"当前处理速度: {fps} 帧/秒")


def process_video(video_file, input_path, output_path, start_trim, end_trim, fail_log, skip_log, use_cuda=False):
    ext = video_file.suffix.lower()
    supported_formats = ['.mkv', '.mp4', '.rmvb', '.avi', '.mov', '.flv', '.wmv']  # 添加 rmvb 格式支持
    if ext not in supported_formats:
        return

    relative_path = video_file.relative_to(input_path)
    output_file = output_path / relative_path.with_suffix('.mp4')  # 保持输出为mp4格式
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 检查输出文件是否已存在，如果存在则跳过处理并记录日志
    if output_file.exists():
        log(f"{output_file} 已存在，跳过处理。")
        skip_log.write(f"{video_file.parent.name}: {video_file}\n")  # 记录跳过的文件
        return

    # 获取视频总时长
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_file)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        log(f"ffprobe 获取视频时长失败: {result.stderr.decode()}")
        fail_log.write(f"{video_file.parent.name}: {video_file}\n")
        return

    duration_str = result.stdout.decode().strip()
    try:
        duration = float(duration_str)
    except ValueError:
        log(f"无法解析视频时长: {duration_str}")
        fail_log.write(f"{video_file.parent.name}: {video_file}\n")
        return

    # 计算裁剪后的结束时间
    end_time = duration - end_trim
    if end_time <= start_trim:
        log("裁剪时间设置无效，结束时间早于开始时间。跳过处理。")
        fail_log.write(f"{video_file.parent.name}: {video_file}\n")
        return

    log(f"裁剪开始时间: {start_trim} 秒，裁剪结束时间: {end_time} 秒")

    # 裁剪视频并去除非视频轨道
    try:
        crop_video(str(video_file), str(output_file), start_trim, end_time, use_cuda)
    except Exception as e:
        log(f"处理视频 {video_file} 失败: {e}")
        fail_log.write(f"{video_file.parent.name}: {video_file}\n")


def monitor_new_files(input_folder, video_files_set):
    """
    监控输入文件夹是否有新文件
    :param input_folder: 输入文件夹路径
    :param video_files_set: 当前已存在的文件集合
    :return: 新的文件列表
    """
    new_files = []
    for file in Path(input_folder).rglob("*.*"):
        if file.is_file() and file not in video_files_set:
            new_files.append(file)
            video_files_set.add(file)
    return new_files


def batch_process_videos(input_folder, output_folder, start_trim, end_trim, fail_log_path='fail.txt', skip_log_path='skipped_files.txt'):
    """
    批量裁剪文件夹中的所有视频，保留目录结构，处理失败和跳过的视频文件路径分别保存到 fail.txt 和 skipped_files.txt
    :param input_folder: 输入文件夹路径
    :param output_folder: 输出文件夹路径
    :param start_trim: 开始裁剪的时间（秒）
    :param end_trim: 结束裁剪的时间（秒）
    :param fail_log_path: 记录失败文件的路径
    :param skip_log_path: 记录跳过文件的路径
    :return: None
    """
    use_cuda = check_nvenc_support()

    input_path = Path(input_folder)
    output_path = Path(output_folder)

    # 确保输出文件夹存在
    output_path.mkdir(parents=True, exist_ok=True)

    # 打开失败和跳过记录文件的句柄
    with open(fail_log_path, 'a', encoding='utf-8') as fail_log, open(skip_log_path, 'a', encoding='utf-8') as skip_log:

        # 初始化文件集合，监控文件夹中的新文件
        video_files_set = set(input_path.rglob("*.*"))
        log(f"初始文件数: {len(video_files_set)}")

        while True:
            new_files = monitor_new_files(input_folder, video_files_set)
            if new_files:
                log(f"检测到 {len(new_files)} 个新文件，将加入处理队列。")

            # 使用 ThreadPoolExecutor 并行处理视频，最多同时处理2个文件
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(process_video, video_file, input_path, output_path, start_trim, end_trim, fail_log, skip_log, use_cuda)
                    for video_file in video_files_set if video_file.is_file()
                ]

                # 使用 tqdm 显示进度条
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="处理视频", unit="个"):
                    pass

            # 等待 10 秒再次检查新文件
            time.sleep(10)


if __name__ == "__main__":
    input_folder = r"D:\桌面\国画\国画素材\0925"  # 输入文件夹路径
    output_folder = r"D:\桌面\国画\国画素材\09251"  # 输出文件夹路径

    # 裁剪的时长，单位为秒
    start_trim = 20 # 开始裁剪的时长（例如8分钟）
    end_trim = 20 # 结束裁剪的时长（例如10分钟）

    batch_process_videos(input_folder, output_folder, start_trim, end_trim, fail_log_path='fail.txt', skip_log_path='skipped_files.txt')
