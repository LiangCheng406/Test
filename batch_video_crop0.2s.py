import os
import ffmpeg

def get_video_duration(input_video_path):
    """获取视频的总时长（秒）"""
    try:
        # 获取视频信息
        probe = ffmpeg.probe(input_video_path, v='error', select_streams='v:0', show_entries='stream=duration')
        duration = float(probe['streams'][0]['duration'])
        return duration
    except ffmpeg.Error as e:
        print(f"获取视频时长失败：{input_video_path}")
        print(e)
        return None

def trim_video(input_video_path, output_video_path, start_time, duration=None):
    try:
        # 如果未指定持续时长，则计算视频的总时长
        if duration is None:
            duration = get_video_duration(input_video_path) - start_time
            if duration <= 0:
                print(f"裁剪时长无效，视频起始时间过晚：{input_video_path}")
                return

        # 裁剪视频
        ffmpeg.input(input_video_path, ss=start_time).output(output_video_path, t=duration, vcodec='libx264', acodec='aac').run()
        print(f"成功裁剪并编码为H.264：{input_video_path} -> {output_video_path}")
    except ffmpeg.Error as e:
        print(f"裁剪失败：{input_video_path} -> {output_video_path}")
        print(e)

def batch_trim_videos(input_folder, output_folder, start_time, duration=None):
    # 遍历输入文件夹中的所有视频文件
    for file_name in os.listdir(input_folder):
        input_video_path = os.path.join(input_folder, file_name)
        if os.path.isfile(input_video_path) and file_name.endswith(('.mp4', '.mkv', '.avi', '.mov')):  # 支持的视频格式
            # 输出路径
            output_video_path = os.path.join(output_folder, f"{file_name}")
            # 执行裁剪
            trim_video(input_video_path, output_video_path, start_time, duration)

# 设置输入和输出文件夹路径
input_folder = r'D:\桌面\教辅\单作品解析\单作品解析\视频作品'  # 输入文件夹路径，替换为你的实际路径
output_folder = r'D:\桌面\教辅\单作品解析\视频作品'  # 输出文件夹路径，替换为你的实际路径

# 批量裁剪
start_time = 0.3  # 裁剪的起始时间
duration = None    # 设置为 None，如果希望裁剪到视频结束
batch_trim_videos(input_folder, output_folder, start_time, duration)
