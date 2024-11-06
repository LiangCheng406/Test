import os
from moviepy.editor import VideoFileClip, concatenate_videoclips
from concurrent.futures import ProcessPoolExecutor
import tempfile


def merge_clips(video_files, target_resolution, target_fps):
    """
    合并一组视频文件并返回一个合成的VideoFileClip对象

    :param video_files: 要合并的视频文件列表
    :param target_resolution: 目标分辨率 (宽度, 高度)，如 (1920, 1080)
    :param target_fps: 目标帧率，如 30 fps
    :return: 合并后的 VideoFileClip 对象
    """
    clips = []
    for video in video_files:
        try:
            # 加载并调整视频的分辨率和帧率
            clip = VideoFileClip(video).resize(newsize=target_resolution).set_fps(target_fps)
            clips.append(clip)
        except Exception as e:
            print(f"加载视频文件 {video} 时出错: {e}")
    # 如果成功加载了视频，则进行合并
    if clips:
        final_clip = concatenate_videoclips(clips, method="compose")
        return final_clip
    return None


def save_temp_clip(video_files, output_path, target_resolution=(1280, 720), target_fps=20):
    """
    将一组视频文件合并并保存到临时文件

    :param video_files: 要合并的视频文件列表
    :param output_path: 临时文件保存路径
    :param target_resolution: 目标分辨率 (宽度, 高度)
    :param target_fps: 目标帧率
    :return: 临时文件的保存路径
    """
    clip = merge_clips(video_files, target_resolution, target_fps)
    if clip:
        clip.write_videofile(output_path, codec="libx264", preset="ultrafast", fps=target_fps)
        clip.close()
    return output_path


def parallel_merge_videos(input_folder, output_file, target_resolution=(1280, 720), target_fps=20, num_groups=4):
    """
    使用并行处理将文件夹中的所有视频文件合并成一个视频

    :param input_folder: 输入视频文件夹路径
    :param output_file: 最终合成视频的保存路径
    :param target_resolution: 目标分辨率 (宽度, 高度)
    :param target_fps: 目标帧率
    :param num_groups: 并行处理的组数，默认值为4
    """
    # 确保输出文件夹存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 获取文件夹中的所有视频文件路径
    video_files = [os.path.join(input_folder, file) for file in os.listdir(input_folder) if
                   file.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if not video_files:
        print("指定文件夹中没有找到视频文件.")
        return

    # 将视频文件分组，每组大小为 group_size
    group_size = max(1, len(video_files) // num_groups)
    video_groups = [video_files[i:i + group_size] for i in range(0, len(video_files), group_size)]

    temp_files = []
    # 使用临时目录存储中间结果
    with tempfile.TemporaryDirectory() as temp_dir:
        with ProcessPoolExecutor() as executor:
            futures = []
            for i, group in enumerate(video_groups):
                temp_output = os.path.join(temp_dir, f"temp_output_{i}.mp4")
                # 并行处理每个组
                futures.append(executor.submit(save_temp_clip, group, temp_output, target_resolution, target_fps))

            # 收集所有的临时文件路径
            for future in futures:
                temp_files.append(future.result())

        # 最终合并所有的临时文件
        final_clips = [VideoFileClip(temp_file) for temp_file in temp_files if temp_file]
        final_clip = concatenate_videoclips(final_clips, method="compose")
        final_clip.write_videofile(output_file, codec="libx264", preset="ultrafast", fps=target_fps)

        # 释放资源
        final_clip.close()
        for clip in final_clips:
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
    target_fps = 20  # 设置帧率，根据内容需求调整

    # 调用函数进行并行视频合并
    parallel_merge_videos(input_folder, output_file, target_resolution, target_fps)
