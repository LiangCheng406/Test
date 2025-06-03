import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# ========== 配置部分 ==========
input_folder = r"D:\桌面\延长石化\河津耿都\河津耿都"  # 输入文件夹路径
output_folder = r"D:\桌面\延长石化\河津耿都"   # 输出文件夹路径（建议不要和输入一样）

x = 0    # 裁剪起始X坐标
y = 0     # 裁剪起始Y坐标
width = 720  # 裁剪宽度
height = 863 # 裁剪高度
threads = 4  # 并行线程数

# ========== 裁剪函数 ==========
def crop_video(input_path, output_path, x, y, width, height):
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-filter:v', f'crop={width}:{height}:{x}:{y}',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        output_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# ========== 主处理函数 ==========
def process_folder(input_folder, output_folder, x, y, width, height, threads):
    os.makedirs(output_folder, exist_ok=True)
    video_files = [
        f for f in os.listdir(input_folder)
        if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))
    ]

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for video in video_files:
            input_path = os.path.join(input_folder, video)
            output_path = os.path.join(output_folder, f"cropped_{video}")
            futures.append(executor.submit(crop_video, input_path, output_path, x, y, width, height))

        for _ in tqdm(as_completed(futures), total=len(futures), desc="裁剪进度"):
            pass

# ========== 主程序入口 ==========
if __name__ == "__main__":
    process_folder(
        input_folder=input_folder,
        output_folder=output_folder,
        x=x,
        y=y,
        width=width,
        height=height,
        threads=threads
    )
