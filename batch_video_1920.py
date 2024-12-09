import os
import subprocess

def resize_and_pad_videos_to_9_16(input_folder, output_folder):
    # 创建输出目录
    os.makedirs(output_folder, exist_ok=True)

    # 遍历输入文件夹中的所有视频文件
    for filename in os.listdir(input_folder):
        if filename.endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv')):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)

            # 获取视频信息
            cmd_probe = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "csv=p=0", input_path
            ]
            try:
                output = subprocess.check_output(cmd_probe, universal_newlines=True).strip()
                width, height = map(int, output.split(','))
            except Exception as e:
                print(f"获取视频信息失败: {filename}, 错误: {e}")
                continue

            # 计算缩放和填充参数
            target_width = 1080
            target_height = 1920
            aspect_ratio = width / height
            target_ratio = target_width / target_height

            if aspect_ratio > target_ratio:
                # 宽比高大，以宽为基准缩放
                scale_width = target_width
                scale_height = int(target_width / aspect_ratio)
                pad_x = 0
                pad_y = (target_height - scale_height) // 2
            else:
                # 高比宽大，以高为基准缩放
                scale_height = target_height
                scale_width = int(target_height * aspect_ratio)
                pad_x = (target_width - scale_width) // 2
                pad_y = 0

            # VF参数：缩放并填充到目标尺寸
            vf_params = (
                f"scale={scale_width}:{scale_height},pad={target_width}:{target_height}:"
                f"{pad_x}:{pad_y}:black"
            )

            # 使用FFmpeg转换
            cmd_ffmpeg = [
                "ffmpeg", "-i", input_path, "-vf", vf_params,
                "-c:v", "libx264", "-crf", "23", "-preset", "fast", output_path
            ]

            try:
                subprocess.run(cmd_ffmpeg, check=True)
                print(f"处理完成: {output_path}")
            except subprocess.CalledProcessError as e:
                print(f"视频处理失败: {filename}, 错误: {e}")

if __name__ == "__main__":
    input_folder = r"D:\桌面\教辅\单作品解析\视频作品1"  # 输入视频文件夹
    output_folder = r"D:\桌面\教辅\单作品解析\作品"  # 输出视频文件夹

    resize_and_pad_videos_to_9_16(input_folder, output_folder)
