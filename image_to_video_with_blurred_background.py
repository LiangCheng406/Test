from moviepy.editor import ImageClip, CompositeVideoClip
from PIL import Image, ImageFilter
import os
from tqdm import tqdm

def create_video_from_image(image_path, output_path, duration=3, resolution=(1920, 1080), codec="libx264"):
    """
    将单张图片转换为指定时长的视频，并填充空白区域为模糊背景
    :param image_path: 图片文件路径
    :param output_path: 输出视频文件路径
    :param duration: 视频时长，默认3秒
    :param resolution: 视频分辨率 (宽, 高)，默认 1920x1080
    :param codec: 视频编码格式，默认 'libx264'
    """
    try:
        # 加载图片
        clip = ImageClip(image_path, duration=duration)

        # 目标分辨率
        target_width, target_height = resolution

        # 计算图片比例
        img_width, img_height = clip.size
        img_ratio = img_width / img_height
        target_ratio = target_width / target_height

        # 按比例缩放图片以适应目标分辨率
        if img_ratio > target_ratio:
            # 图片更宽，宽度适配，留空白在上下
            resized_clip = clip.resize(width=target_width)
        else:
            # 图片更高，高度适配，留空白在左右
            resized_clip = clip.resize(height=target_height)

        # 使用 Pillow 创建模糊背景
        img = Image.open(image_path)
        blurred_bg = img.resize(resolution).filter(ImageFilter.GaussianBlur(20))
        blurred_bg_path = "temp_blurred_bg.jpg"
        blurred_bg.save(blurred_bg_path)

        # 创建模糊背景剪辑
        background_clip = ImageClip(blurred_bg_path, duration=duration)

        # 合成图片和模糊背景
        final_clip = CompositeVideoClip([background_clip, resized_clip.set_position("center")]).set_duration(duration).set_fps(24)

        # 保存为视频文件
        final_clip.write_videofile(output_path, codec=codec, audio=False)
        print(f"视频已生成: {output_path}")

        # 删除临时模糊背景文件
        os.remove(blurred_bg_path)

    except Exception as e:
        print(f"发生错误处理图片 {image_path}: {e}")


def batch_process_images(input_folder, output_folder, duration=3, resolution=(1920, 1080), codec="libx264"):
    """
    批量将文件夹中的图片转换为视频
    :param input_folder: 输入图片文件夹路径
    :param output_folder: 输出视频文件夹路径
    :param duration: 视频时长，默认3秒
    :param resolution: 视频分辨率 (宽, 高)，默认 1920x1080
    :param codec: 视频编码格式，默认 'libx264'
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    # 获取所有图片文件
    image_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

    # 使用 tqdm 显示进度条
    for file_name in tqdm(image_files, desc="Processing images", unit="file"):
        image_path = os.path.join(input_folder, file_name)
        output_path = os.path.join(output_folder, os.path.splitext(file_name)[0] + ".mp4")
        create_video_from_image(image_path, output_path, duration, resolution, codec)

    print("批量处理完成！")


if __name__ == "__main__":
    # 输入参数
    input_folder = r"D:\桌面\图\历史的遗憾" # 图片文件夹路径
    output_folder = r"D:\桌面\图\历史的遗憾1"  # 视频输出文件夹路径
    duration = 3  # 每个视频持续时间（秒）
    resolution = (1280, 720)  # 视频分辨率（宽, 高）
    codec = "libx264"  # 视频编码

    # 批量处理
    batch_process_images(input_folder, output_folder, duration, resolution, codec)
