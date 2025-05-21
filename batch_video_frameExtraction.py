import os
import subprocess
import glob
import math

# 设置视频文件夹路径
video_folder = r"D:\桌面\餐饮店铺\dfb048884ee61f5002f9b38967bf3576"
output_folder = r"D:\桌面\餐饮店铺\output"

# 用户输入指定的秒数和帧数
duration = None  # None 表示使用整个视频长度
total_frames = 10  # 希望抽取的总帧数

# 创建输出文件夹（如果不存在）
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 获取视频文件夹中的所有视频文件
video_extensions = ["*.mp4", "*.mov", "*.avi", "*.mkv"]
video_files = []
for ext in video_extensions:
    video_files.extend(glob.glob(os.path.join(video_folder, ext)))


def get_video_duration(video_path):
    """使用 ffprobe 获取视频时长（单位：秒）"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


# 遍历每个视频文件进行抽帧
for video_file in video_files:
    video_name = os.path.basename(video_file).split('.')[0]
    video_output_folder = os.path.join(output_folder, video_name)
    if not os.path.exists(video_output_folder):
        os.makedirs(video_output_folder)

    # 获取当前视频时长（如果未指定 duration）
    video_duration = get_video_duration(video_file)
    use_duration = duration if duration is not None else video_duration

    if use_duration is None:
        print(f"无法获取视频时长: {video_file}")
        continue

    # 计算每秒需要的帧数，保证抽取 total_frames 张以内
    frame_rate = math.ceil(total_frames / use_duration)

    # 构造 FFmpeg 命令
    cmd = ['ffmpeg', '-i', video_file]

    if duration is not None:
        cmd += ['-t', str(duration)]

    cmd += [
        '-vf', f'fps={frame_rate}',
        '-frames:v', str(total_frames),  # 限制最多抽取 total_frames 张
        os.path.join(video_output_folder, '%04d.png')
    ]

    subprocess.run(cmd)

print("抽帧完成，每个视频最多抽取指定帧数！")
