import os
import subprocess
import logging
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    filename='video_processing.log',  # 指定日志文件
    level=logging.INFO,  # 设置日志级别为 INFO
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)


def adjust_video_properties(input_folder, output_folder):
    """
    批量调整视频属性，增强清晰度，旋转270度并设置分辨率为1080x1920（9:16），保持原始分辨率。
    :param input_folder: 输入视频文件夹路径
    :param output_folder: 输出视频文件夹路径
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 获取所有视频文件
    video_files = [f for f in os.listdir(input_folder) if f.endswith(('.MP4', '.avi', '.mkv', '.mov'))]

    if not video_files:
        logging.warning("没有找到支持的视频文件。")
        print("没有找到支持的视频文件。")
        return

    # 使用 tqdm 为处理视频文件添加进度条
    for filename in tqdm(video_files, desc="处理视频", unit="个", ncols=100):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"processed_{filename}")

        # 使用 FFmpeg 调整视频属性并进行旋转及分辨率调整
        command = [
            'ffmpeg', '-i', input_path,
            '-vf', (
                f"eq=brightness=0.21:contrast=1.4:saturation=1.10:"
                f"gamma_r=0.93:gamma_g=0.93:gamma_b=1.07,"
                f"unsharp=5:5:1.0,"  # 增强清晰度
                f"transpose=2,"  # 旋转视频 270 度（相当于逆时针90度）
                f"scale=1080:1920,"  # 调整分辨率为 1080x1920 (9:16)
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2"  # 填充视频，使其完全覆盖 9:16
            ),
            '-c:v', 'libx264',  # H.264 编码
            '-preset', 'fast',  # 编码速度设置，可调为 'slow', 'medium', 'fast'
            '-crf', '23',  # 控制质量的参数，值越低质量越高，范围为 0-51
            '-c:a', 'copy',  # 保留原音频
            output_path
        ]

        try:
            logging.info(f"开始处理视频: {filename}")
            print(f"Processing {filename}...")
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            # 如果命令执行成功，记录成功日志
            logging.info(f"视频处理成功: {filename}")
        except subprocess.CalledProcessError as e:
            # 记录错误日志
            logging.error(f"处理视频失败: {filename}, 错误: {e.stderr.decode()}")
            print(f"Error processing {filename}: {e.stderr.decode()}")

    print("所有视频已处理完成！")
    logging.info("所有视频已处理完成！")


# 输入与输出文件夹路径
input_folder = r"D:\桌面\作文模板有一套" # 替换为您的输入文件夹路径
output_folder = r"D:\桌面\教辅111"  # 替换为您的输出文件夹路径

# 执行视频处理
adjust_video_properties(input_folder, output_folder)
