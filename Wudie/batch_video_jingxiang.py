import os
import subprocess
import time


def batch_mirror_ffmpeg(input_dir, output_dir):
    # 支持的视频后缀
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.ts', '.flv')

    # 如果输出文件夹不存在则创建
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    # 获取文件夹内所有视频文件
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(video_extensions)]

    if not files:
        print("文件夹内没有找到视频素材！")
        return

    print(f"找到 {len(files)} 个视频，准备开始处理...")
    start_time = time.time()

    for index, filename in enumerate(files, 1):
        input_path = os.path.join(input_dir, filename)
        # 加上 mirror_ 前缀，避免同名冲突
        output_path = os.path.join(output_dir, f"mirror_{filename}")

        print(f"[{index}/{len(files)}] 正在镜像翻转: {filename}...")

        # FFmpeg 命令
        # -y: 覆盖已存在文件
        # -i: 输入路径
        # -vf "hflip": 核心滤镜，水平翻转
        # -c:v libx264: 视频编码器
        # -crf 18: 设置画质（0-51，18为几乎无损，23是默认）
        # -c:a copy: 音频流直接复制，不重编码
        command = [
            'ffmpeg',
            '-y',
            '-i', input_path,
            '-vf', 'hflip',
            '-c:v', 'libx264',
            '-crf', '18',
            '-c:a', 'copy',
            output_path
        ]

        try:
            # 执行命令，关闭 stdout 输出以保持控制台整洁
            subprocess.run(command, check=True, capture_output=True)
            print(f"   ✅ 完成")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ 处理 {filename} 失败: {e}")

    end_time = time.time()
    print(f"\n✨ 全部任务已完成！")
    print(f"总耗时: {end_time - start_time:.2f} 秒")


if __name__ == "__main__":
    # === 在这里配置你的文件夹路径 ===
    INPUT_FOLDER = r'D:\桌面\素材玲姐\TK\自行车20260610\裁剪后'  # 原始素材文件夹
    OUTPUT_FOLDER = r'D:\桌面\素材玲姐\TK\自行车20260610\output'  # 镜像素材保存位置

    # 路径中如果有中文，建议使用绝对路径或在字符串前加 r
    batch_mirror_ffmpeg(INPUT_FOLDER, OUTPUT_FOLDER)