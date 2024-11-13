import os
import subprocess
from pathlib import Path
import multiprocessing


def get_video_format(input_file):
    """获取视频文件的格式"""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=format_name",
        "-of", "default=noprint_wrappers=1:nokey=1", input_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"获取视频格式失败: {result.stderr.decode()}")
        return None
    return result.stdout.decode().strip()


def rotate_video(input_file, output_file, rotation_angle):
    """
    使用 ffmpeg 对视频进行旋转
    :param input_file: 输入视频文件路径
    :param output_file: 输出视频文件路径
    :param rotation_angle: 旋转角度 (90, 180, 270 等)
    """
    cmd = [
        "ffmpeg", "-i", input_file,
        "-vf", f"rotate={rotation_angle}*PI/180",  # 使用旋转滤镜
        "-c:v", "libx264",  # 设置视频编码器
        "-preset", "fast",  # 设置编码器预设
        "-c:a", "aac",  # 设置音频编码器
        "-b:v", "5M",  # 设置视频比特率
        "-strict", "experimental",  # 允许使用一些实验性编码选项
        output_file
    ]

    subprocess.run(cmd, check=True)


def process_video(video_file, input_folder, output_folder, rotation_angle):
    """处理单个视频文件，旋转视频并保持原格式和文件名"""
    video_format = get_video_format(str(video_file))
    if not video_format:
        print(f"无法识别格式，跳过文件: {video_file}")
        return

    # 保持输出文件格式一致
    output_file = output_folder / video_file.name

    # 旋转视频
    try:
        print(f"处理视频: {video_file.name}，旋转角度: {rotation_angle}°")
        rotate_video(str(video_file), str(output_file), rotation_angle)
        print(f"完成: {video_file.name}")
    except subprocess.CalledProcessError as e:
        print(f"处理 {video_file.name} 时出错: {e}")


def process_videos_in_parallel(input_folder, output_folder, rotation_angle, max_workers=4):
    """并行处理文件夹中的视频，按指定角度旋转并保持原格式和文件名"""
    input_folder_path = Path(input_folder)
    output_folder_path = Path(output_folder)

    if not output_folder_path.exists():
        os.makedirs(output_folder_path)

    # 获取所有视频文件
    video_files = [file for file in input_folder_path.rglob('*.*') if file.is_file()]

    # 设置进程池并行处理视频文件
    with multiprocessing.Pool(processes=max_workers) as pool:
        pool.starmap(process_video,
                     [(video_file, input_folder_path, output_folder_path, rotation_angle) for video_file in
                      video_files])


if __name__ == "__main__":
    # 设置输入输出文件夹路径
    input_folder = r"D:\桌面\国画\11月国画未剪辑\output"  # 输入文件夹路径
    output_folder = r"D:\桌面\国画\11月国画未剪辑\output_"  # 输出文件夹路径

    # 设置旋转角度（可以根据需求调整）
    rotation_angle = 180  # 旋转角度，例如 90°、180° 或 270°

    # 并行处理视频，最多同时处理4个文件
    process_videos_in_parallel(input_folder, output_folder, rotation_angle, max_workers=4)
