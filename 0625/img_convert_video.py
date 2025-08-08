import os
from PIL import Image
import cv2
import numpy as np
from pathlib import Path


def read_image_unicode(image_path):
    """
    使用支持中文路径的方式读取图片

    Args:
        image_path (str): 图片路径

    Returns:
        numpy.ndarray: 图片数组，失败返回None
    """
    try:
        # 使用PIL读取然后转换为OpenCV格式
        pil_image = Image.open(image_path)
        # 转换为RGB格式
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # 转换为numpy数组
        img_array = np.array(pil_image)
        # 转换颜色通道从RGB到BGR（OpenCV格式）
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        return img_bgr

    except Exception as e:
        print(f"无法读取图片 {image_path}: {e}")
        return None


def get_best_codec():
    """
    获取系统中最佳可用的视频编码器

    Returns:
        tuple: (fourcc, codec_name, description)
    """
    # 按优先级测试编码器
    codecs_to_test = [
        ('mp4v', 'MPEG-4', '通用MPEG-4编码'),
        ('XVID', 'XVID', 'XVID编码'),
        ('MJPG', 'MJPG', 'Motion JPEG编码'),
        ('X264', 'X264', 'x264编码'),
        ('avc1', 'AVC1', 'H.264 AVC编码'),
        ('h264', 'H264', 'H.264编码'),
        ('H264', 'H264', 'H.264编码'),
    ]

    print("正在测试可用的编码器...")

    for codec, name, desc in codecs_to_test:
        try:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            # 创建测试文件
            test_path = 'codec_test.mp4'
            test_writer = cv2.VideoWriter(test_path, fourcc, 30.0, (640, 480))

            if test_writer.isOpened():
                # 写入一帧测试
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                test_writer.write(test_frame)
                test_writer.release()

                # 检查文件是否成功创建
                if os.path.exists(test_path) and os.path.getsize(test_path) > 0:
                    os.remove(test_path)
                    print(f"✓ 可用编码器: {codec} ({desc})")
                    return fourcc, codec, desc
                elif os.path.exists(test_path):
                    os.remove(test_path)
            else:
                test_writer.release()

        except Exception as e:
            print(f"✗ 编码器 {codec} 测试失败: {e}")
            continue

    # 如果所有编码器都失败，使用默认
    print("警告: 所有编码器测试失败，使用默认编码器")
    return cv2.VideoWriter_fourcc(*'mp4v'), 'mp4v', '默认编码器'


def write_video_safe(output_path, fps, frame_size):
    """
    创建安全的视频写入器

    Args:
        output_path (str): 输出路径
        fps (int): 帧率
        frame_size (tuple): 帧尺寸

    Returns:
        tuple: (video_writer, final_output_path, codec_info)
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 确保输出文件是.mp4格式
        if not output_path.lower().endswith('.mp4'):
            output_path = os.path.splitext(output_path)[0] + '.mp4'

        # 获取最佳可用编码器
        fourcc, codec_name, codec_desc = get_best_codec()

        # 尝试创建视频写入器，使用多种参数组合
        writer_configs = [
            (fourcc, float(fps)),
            (fourcc, int(fps)),
            (cv2.VideoWriter_fourcc(*'mp4v'), float(fps)),
            (cv2.VideoWriter_fourcc(*'XVID'), float(fps)),
        ]

        for config_fourcc, config_fps in writer_configs:
            try:
                video_writer = cv2.VideoWriter(output_path, config_fourcc, config_fps, frame_size)

                if video_writer.isOpened():
                    # 测试写入一帧
                    test_frame = np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)
                    video_writer.write(test_frame)

                    print(f"成功创建视频写入器")
                    print(f"  文件: {output_path}")
                    print(f"  编码器: {codec_desc}")
                    print(f"  帧率: {config_fps}")
                    print(f"  分辨率: {frame_size[0]}x{frame_size[1]}")

                    return video_writer, output_path, codec_desc
                else:
                    video_writer.release()

            except Exception as e:
                print(f"编码器配置失败: {e}")
                continue

        print(f"错误：无法创建任何视频写入器")
        return None, output_path, "无"

    except Exception as e:
        print(f"创建视频写入器失败: {e}")
        return None, output_path, "无"


def image_to_video(image_path, output_path, duration=10, fps=30, effect="static"):
    """
    将图片转换为视频（使用最兼容的编码器）

    Args:
        image_path (str): 输入图片路径
        output_path (str): 输出视频路径
        duration (int): 视频时长（秒）
        fps (int): 帧率
        effect (str): 效果类型

    Returns:
        bool: 是否成功
    """
    try:
        print(f"正在读取图片: {image_path}")

        # 使用支持中文路径的方式读取图片
        img = read_image_unicode(image_path)
        if img is None:
            print(f"错误：无法读取图片 {image_path}")
            return False

        height, width, channels = img.shape
        total_frames = duration * fps

        print(f"图片读取成功: {width}x{height}")
        print(f"视频参数: {fps}fps, {duration}s, 总帧数: {total_frames}")

        # 创建视频写入器
        video_writer, final_output_path, codec_info = write_video_safe(output_path, fps, (width, height))
        if video_writer is None:
            return False

        print("开始生成视频帧...")

        for frame_num in range(total_frames):
            progress = frame_num / total_frames

            if effect == "static":
                frame = img.copy()
            elif effect == "zoom_in":
                scale = 1.0 + progress * 0.3
                frame = apply_zoom(img, scale)
            elif effect == "zoom_out":
                scale = 1.3 - progress * 0.3
                frame = apply_zoom(img, scale)
            elif effect == "pan_left":
                frame = apply_pan(img, progress, direction="left")
            elif effect == "pan_right":
                frame = apply_pan(img, progress, direction="right")
            else:
                frame = img.copy()

            video_writer.write(frame)

            # 显示进度
            if frame_num % fps == 0:  # 每秒显示一次进度
                print(f"进度: {frame_num}/{total_frames} ({progress * 100:.1f}%)")

        video_writer.release()

        # 验证生成的视频文件
        if os.path.exists(final_output_path):
            file_size = os.path.getsize(final_output_path)
            print(f"视频转换完成: {final_output_path}")
            print(f"编码器: {codec_info}")
            print(f"文件大小: {file_size / (1024 * 1024):.2f} MB")

            # 验证视频信息
            verify_video_info(final_output_path)
            return True
        else:
            print("错误：视频文件生成失败")
            return False

    except Exception as e:
        print(f"转换失败: {e}")
        return False


def verify_video_info(video_path):
    """验证视频信息"""
    try:
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            print(f"视频信息:")
            print(f"  分辨率: {width}x{height}")
            print(f"  帧率: {fps:.2f}")
            print(f"  总帧数: {frame_count}")
            print(f"  时长: {frame_count / fps:.2f}秒")

            cap.release()
        else:
            print("无法读取生成的视频文件进行验证")
    except Exception as e:
        print(f"验证视频信息失败: {e}")


def apply_zoom(img, scale):
    """应用缩放效果"""
    height, width = img.shape[:2]

    new_width = int(width * scale)
    new_height = int(height * scale)

    resized = cv2.resize(img, (new_width, new_height))

    if scale > 1.0:
        start_x = (new_width - width) // 2
        start_y = (new_height - height) // 2
        frame = resized[start_y:start_y + height, start_x:start_x + width]
    else:
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        start_x = (width - new_width) // 2
        start_y = (height - new_height) // 2
        frame[start_y:start_y + new_height, start_x:start_x + new_width] = resized

    return frame


def apply_pan(img, progress, direction="left"):
    """应用平移效果"""
    height, width = img.shape[:2]

    enlarged = cv2.resize(img, (int(width * 1.2), int(height * 1.2)))
    enlarged_height, enlarged_width = enlarged.shape[:2]

    if direction == "left":
        start_x = int((enlarged_width - width) * (1 - progress))
    else:
        start_x = int((enlarged_width - width) * progress)

    start_y = (enlarged_height - height) // 2
    frame = enlarged[start_y:start_y + height, start_x:start_x + width]
    return frame


def validate_image_file(image_path):
    """验证图片文件是否有效"""
    if not os.path.exists(image_path):
        return False, "文件不存在"

    try:
        with Image.open(image_path) as img:
            img.verify()
        return True, "文件有效"
    except Exception as e:
        return False, f"文件损坏或格式不支持: {e}"


def batch_convert_images(input_folder, output_folder, duration=10, fps=30, effect="static"):
    """批量转换文件夹中的所有图片为视频"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

    Path(output_folder).mkdir(parents=True, exist_ok=True)

    converted_count = 0
    failed_count = 0
    total_files = 0

    print(f"开始扫描文件夹: {input_folder}")
    print(f"输出格式: MP4视频文件")

    for root, dirs, files in os.walk(input_folder):
        for file in files:
            file_extension = Path(file).suffix.lower()
            if file_extension in image_extensions:
                total_files += 1
                input_path = os.path.join(root, file)

                print(f"\n--- 处理第 {total_files} 张图片 ---")
                print(f"文件: {file}")

                # 验证图片文件
                is_valid, message = validate_image_file(input_path)
                if not is_valid:
                    print(f"跳过无效文件: {message}")
                    failed_count += 1
                    continue

                # 生成输出文件名
                base_name = Path(file).stem
                output_filename = f"{base_name}_{effect}_{duration}s.mp4"
                output_path = os.path.join(output_folder, output_filename)

                if image_to_video(input_path, output_path, duration, fps, effect):
                    converted_count += 1
                else:
                    failed_count += 1

    print(f"\n批量视频转换完成!")
    print(f"总共处理: {total_files} 张图片")
    print(f"成功转换: {converted_count} 个视频")
    print(f"转换失败: {failed_count} 个")
    print(f"输出文件夹: {output_folder}")


def convert_single_image():
    """转换单张图片为视频的交互式函数"""
    print("图片转视频工具 (智能编码器选择)")
    print("=" * 50)

    image_path = input("请输入图片路径: ").strip().strip('"')

    # 验证文件
    is_valid, message = validate_image_file(image_path)
    if not is_valid:
        print(f"错误: {message}")
        return

    print(f"文件验证通过: {message}")

    # 生成默认输出路径
    input_path_obj = Path(image_path)
    default_output = input_path_obj.parent / f"{input_path_obj.stem}_video.mp4"

    output_path = input(f"输出视频路径 (默认: {default_output}): ").strip().strip('"')
    if not output_path:
        output_path = str(default_output)

    duration = input("视频时长(秒，默认10): ").strip()
    duration = int(duration) if duration else 10

    fps = input("帧率(默认30): ").strip()
    fps = int(fps) if fps else 30

    print("\n可用效果:")
    print("1. static - 静态图片")
    print("2. zoom_in - 放大效果")
    print("3. zoom_out - 缩小效果")
    print("4. pan_left - 左移效果")
    print("5. pan_right - 右移效果")

    effect_choice = input("选择效果 (1-5，默认1): ").strip()
    effect_map = {
        "1": "static", "2": "zoom_in", "3": "zoom_out",
        "4": "pan_left", "5": "pan_right"
    }
    effect = effect_map.get(effect_choice, "static")

    print(f"\n开始转换...")
    print(f"输入: {image_path}")
    print(f"输出: {output_path}")
    print(f"参数: {duration}秒, {fps}fps, 效果: {effect}")

    image_to_video(image_path, output_path, duration, fps, effect)


# 使用示例
if __name__ == "__main__":
    print("图片转视频工具 (兼容性增强版)")
    print("=" * 50)

    print("请选择模式:")
    print("1. 转换单张图片")
    print("2. 批量转换文件夹")

    choice = input("\n请输入选择 (1/2): ").strip()

    if choice == "1":
        convert_single_image()
    elif choice == "2":
        input_folder = input("请输入图片文件夹路径: ").strip().strip('"')
        output_folder = input("请输入输出视频文件夹路径: ").strip().strip('"')

        if not os.path.exists(input_folder):
            print(f"错误：输入文件夹 '{input_folder}' 不存在！")
        else:
            duration = input("视频时长(秒，默认10): ").strip()
            duration = int(duration) if duration else 10

            fps = input("帧率(默认30): ").strip()
            fps = int(fps) if fps else 30

            print("\n可用效果:")
            effects = ["static", "zoom_in", "zoom_out", "pan_left", "pan_right"]
            for i, eff in enumerate(effects, 1):
                print(f"{i}. {eff}")

            effect_choice = input("选择效果 (1-5，默认1): ").strip()
            effect_map = {str(i): eff for i, eff in enumerate(effects, 1)}
            effect = effect_map.get(effect_choice, "static")

            print(f"\n系统将自动选择最佳编码器")
            batch_convert_images(input_folder, output_folder, duration, fps, effect)
    else:
        print("无效选择！")