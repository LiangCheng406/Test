import os
from moviepy.editor import VideoFileClip
from multiprocessing import Pool, cpu_count


def process_video(args):
    """
    处理单个视频，将1080x1920的视频转换为1920x1080（通过填充黑色区域）。

    参数：
        args (tuple): 包含输入视频路径、输出视频路径的信息。
    """
    input_path, output_path = args

    try:
        print(f"正在处理视频: {input_path}")
        # 读取视频
        clip = VideoFileClip(input_path)

        # 获取原视频的宽度和高度
        original_width, original_height = clip.size

        # 检查是否是1080x1920的视频
        if original_width == 1080 and original_height == 1920:
            # 创建一个新的画布（1920x1080），背景为黑色
            new_clip = clip.on_color(size=(1920, 1080), color=(0, 0, 0), pos='center')

            # 保存处理后的视频
            new_clip.write_videofile(
                output_path,
                codec='libx264',  # H.264 编码
                audio_codec='aac'  # 保留音频
            )
            print(f"转换完成: {output_path}")
        else:
            print(f"跳过视频（非1080x1920尺寸）: {input_path}")

    except Exception as e:
        print(f"处理视频时出错: {input_path}，错误信息: {e}")


def batch_convert_videos(input_folder, output_folder, max_processes=4):
    """
    批量将1080x1920的视频转换为1920x1080（通过填充黑色区域），使用多进程加速处理。

    参数：
        input_folder (str): 输入文件夹路径，包含待处理的视频。
        output_folder (str): 输出文件夹路径，用于保存处理后的视频。
        max_processes (int): 最大并行进程数。
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    # 获取输入文件夹中的所有文件
    files = os.listdir(input_folder)

    # 创建任务列表
    tasks = []
    for file_name in files:
        input_path = os.path.join(input_folder, file_name)
        output_path = os.path.join(output_folder, file_name)

        # 检查是否是视频文件（根据扩展名筛选，可以根据需要调整）
        if file_name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            tasks.append((input_path, output_path))

    # 使用多进程池处理视频
    with Pool(processes=max_processes) as pool:
        pool.map(process_video, tasks)


if __name__ == "__main__":
    # 输入和输出文件夹路径
    input_folder = r"D:\桌面\教辅\教辅一组\1220"  # 替换为您的输入文件夹路径
    output_folder = r"D:\桌面\教辅\单作品解析\作品"  # 替换为您的输出文件夹路径

    # 批量转换，最多使用 4 个进程
    batch_convert_videos(input_folder, output_folder, max_processes=4)
