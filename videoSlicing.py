import os
from moviepy.editor import VideoFileClip, concatenate_videoclips
from multiprocessing import Pool

def process_single_video(args):
    filename, input_folder, output_folder, segments, slice_duration = args

    file_path = os.path.join(input_folder, filename)
    try:
        clip = VideoFileClip(file_path)
        total_duration = clip.duration
        clips_dict = {i: [] for i in range(1, segments + 1)}

        # 遍历原视频，按分段数和时长来切分片段并分配到不同的文件
        for i in range(0, int(total_duration), slice_duration):
            segment_index = (i // slice_duration) % segments + 1
            start_time = i
            end_time = min(i + slice_duration, total_duration)
            segment_clip = clip.subclip(start_time, end_time)

            # 将切片加入对应的分段列表
            clips_dict[segment_index].append(segment_clip)

        # 拼接并保存每个分段的视频到对应的 "切片" 文件夹
        base_name = os.path.splitext(filename)[0]
        for segment_index, clips_list in clips_dict.items():
            if clips_list:
                final_clip = concatenate_videoclips(clips_list)

                # 创建切片文件夹，例如 "切片1", "切片2", "切片3"
                output_subfolder = os.path.join(output_folder, f"切片{segment_index}")
                if not os.path.exists(output_subfolder):
                    os.makedirs(output_subfolder)

                # 输出文件路径和文件名，保留原文件名
                output_filename = f"{filename}"
                output_path = os.path.join(output_subfolder, output_filename)
                final_clip.write_videofile(output_path, codec="libx264")

                # 检查并确认写入完成
                if os.path.exists(output_path):
                    print(f"Segment {segment_index} for {filename} saved successfully in {output_subfolder}.")

        print(f"Processed {filename}")
    except Exception as e:
        print(f"Error processing {filename}: {e}")

def slice_videos(input_folder, output_folder, segments, slice_duration, num_workers=4):
    # 检查输出文件夹是否存在，不存在则创建
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 准备每个视频文件的参数
    video_files = [
        (filename, input_folder, output_folder, segments, slice_duration)
        for filename in os.listdir(input_folder)
        if filename.endswith((".mp4", ".avi", ".mov", ".mkv"))
    ]

    # 使用多进程池并行处理视频文件
    with Pool(processes=num_workers) as pool:
        pool.map(process_single_video, video_files)

if __name__ == '__main__':
    # 输入文件夹、输出文件夹、切片分段数和单位时长
    input_folder = r"D:\桌面\国画\11月国画未剪辑\output_"
    output_folder = r"D:\桌面\国画\11月国画未剪辑\out"
    segments = 3  # 切片分段数
    slice_duration = 1  # 切片单位时长（秒）
    num_workers = 4  # 并行处理的进程数

    # 调用切片函数
    slice_videos(input_folder, output_folder, segments, slice_duration, num_workers)