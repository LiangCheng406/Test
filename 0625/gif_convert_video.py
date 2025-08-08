import os
import time
from pathlib import Path
from moviepy.editor import VideoFileClip
from tqdm import tqdm

def gif_to_mp4_batch(input_folder):
    input_path = Path(input_folder)
    if not input_path.exists():
        print(f"输入路径不存在: {input_path}")
        return

    # 生成输出文件夹：同目录下加上时间戳
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = input_path.parent / f"{input_path.name}_mp4_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    # 获取所有gif文件
    gif_files = list(input_path.glob("*.gif"))
    if not gif_files:
        print("❌ 未找到GIF文件")
        return

    print(f"开始转换，共 {len(gif_files)} 个 GIF 文件...")
    for gif_file in tqdm(gif_files, desc="转换中"):
        try:
            clip = VideoFileClip(str(gif_file))
            output_file = output_path / (gif_file.stem + ".mp4")
            clip.write_videofile(str(output_file), codec="libx264", audio=False, logger=None)
            clip.close()
        except Exception as e:
            print(f"❌ 转换失败: {gif_file.name}，错误: {e}")

    print(f"✅ 全部完成，输出文件夹为: {output_path}")

if __name__ == "__main__":
    # 固定输入路径为 D:\桌面\国画\裁剪后
    input_folder = r"D:\桌面\切图\input"
    gif_to_mp4_batch(input_folder)
