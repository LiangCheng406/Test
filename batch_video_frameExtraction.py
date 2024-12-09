import os
import subprocess
import glob
import math

# 设置视频文件夹路径
video_folder = r"D:\桌面\教辅\1213"  # 替换为你的视频文件夹路径
output_folder = "D:\桌面\教辅\Output"  # 替换为保存帧的文件夹路径
# 用户输入指定的秒数和帧数
duration = 5  # 例如 5
total_frames = 10  # 例如 10

# 计算每秒的帧数
frame_rate = math.ceil(total_frames / duration)  # 向上取整，保证足够的帧数

# 创建输出文件夹（如果不存在）
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 获取视频文件夹中的所有视频文件
video_files = glob.glob(os.path.join(video_folder, "*.mp4"))  # 可以根据需要扩展支持的格式

# 遍历每个视频文件进行抽帧
for video_file in video_files:
    # 获取视频文件名（不包括扩展名）
    video_name = os.path.basename(video_file).split('.')[0]

    # 设置输出帧文件夹
    video_output_folder = os.path.join(output_folder, video_name)
    if not os.path.exists(video_output_folder):
        os.makedirs(video_output_folder)

    # 使用FFmpeg抽帧，限制时间为duration秒，并按frame_rate抽帧
    cmd = [
        'ffmpeg', '-i', video_file,
        '-t', str(duration),  # 限制抽帧的时间（前duration秒）
        '-vf', f'fps={frame_rate}',  # 设置帧率
        os.path.join(video_output_folder, '%04d.png')  # 设置输出格式和路径
    ]

    # 执行命令
    subprocess.run(cmd)

print("指定秒数和帧数的抽帧完成！")
