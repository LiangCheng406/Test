import os
from moviepy.editor import VideoFileClip, concatenate_videoclips


def merge_videos(input_folder, output_file, target_resolution=(1280, 720), target_fps=30):
    """
    直接合并文件夹中的所有视频文件并导出为一个视频文件。

    :param input_folder: 输入视频文件夹路径
    :param output_file: 最终合成视频的保存路径
    :param target_resolution: 目标分辨率 (宽度, 高度)
    :param target_fps: 目标帧率
    """
    # 确保输出文件夹存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 获取文件夹中的所有视频文件路径
    video_files = [os.path.join(input_folder, file) for file in os.listdir(input_folder) if
                   file.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if not video_files:
        print("指定文件夹中没有找到视频文件.")
        return

    clips = []
    for video in video_files:
        try:
            # 加载视频，设置目标分辨率和帧率
            clip = VideoFileClip(video).resize(newsize=target_resolution).set_fps(target_fps)
            clips.append(clip)
        except Exception as e:
            print(f"加载视频文件 {video} 时出错: {e}")

    # 将所有视频剪辑合并为一个
    if clips:
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(output_file, codec="libx264", preset="ultrafast", fps=target_fps)
        final_clip.close()

        # 释放资源
        for clip in clips:
            clip.close()

# 常用分辨率和对应的帧率建议
# 1. (1920, 1080): 30 fps（常用于1080p全高清内容，适合普通高清视频拍摄）
# 2. (1280, 720): 30 fps（常用于720p高清内容，适合在线视频）
# 3. (854, 480): 30 fps（常用于480p标清内容，适合文件大小有限的内容）
# 4. (640, 360): 25 fps（常用于360p低清内容，适合低带宽需求的视频）
# 5. (426, 240): 15-20 fps（常用于240p低清内容，适合超低带宽环境）

if __name__ == "__main__":
    # 设置输入文件夹路径和输出文件路径，并指定分辨率
    input_folder = r"D:\桌面\宝妈\炒菜视频\10.17炒菜\虾仁豆腐蛋20个"
    output_file = r"D:\桌面\宝妈\炒菜视频\10.17炒菜\虾仁豆腐蛋.mp4"
    target_resolution = (1920, 1080)  # 选择合适的分辨率
    target_fps = 30  # 设置帧率

    # 调用函数进行视频合并
    merge_videos(input_folder, output_file, target_resolution, target_fps)
