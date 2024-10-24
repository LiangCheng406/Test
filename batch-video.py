import os
import subprocess
from tqdm import tqdm  # 引入进度条库

def crop_to_resolution(input_folder, output_folder, target_resolution):
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 获取文件夹中的所有视频文件
    video_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.flv'))]

    # 分析目标分辨率
    target_width, target_height = map(int, target_resolution.split(':'))

    # 使用 tqdm 增加处理进度条
    for video_file in tqdm(video_files, desc="Processing videos"):
        input_path = os.path.join(input_folder, video_file)
        output_path = os.path.join(output_folder, video_file)

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
                '-i', input_path,  # 输入文件
                '-vf', f'crop={crop_width}:{crop_height}:0:0,scale={target_width}:{target_height}',  # 裁切并缩放
                '-c:v', 'libx264',  # 使用 libx264 编码器
                '-crf', '23',  # 压缩质量参数，数值越低质量越高
                '-c:a', 'copy',  # 保持音频编码不变
                '-movflags', 'faststart',  # 修复 moov atom
                output_path
            ]

            # 执行 ffmpeg 命令并检查输出
            subprocess.run(command, check=True)

        except subprocess.CalledProcessError as e:
            print(f"处理视频 {video_file} 时出错: {str(e)}")
        except Exception as e:
            print(f"处理视频 {video_file} 时发生未预期的错误: {str(e)}")

    print("所有视频处理成功！")


# 示例用法
input_folder_path = r"D:\桌面\百草\20241102-1108\10.22百草视频\10.22百草视频"
output_folder_path = r"D:\桌面\百草\20241102-1108\唱百草"
target_resolution = "1920:1082"  # 目标分辨率

crop_to_resolution(input_folder_path, output_folder_path, target_resolution)

