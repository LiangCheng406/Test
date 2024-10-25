import argparse
from PIL import Image
import os
import sys
import logging
from multiprocessing import Pool

# 设置编码为UTF-8，特别适用于处理中文文件名
sys.stdout.reconfigure(encoding='utf-8')

# 配置日志记录
logging.basicConfig(filename='logs/image_processing.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def validate_crop_area(crop_area, image_size):
    """
    验证裁剪区域是否合法
    :param crop_area: 裁剪区域 (left, upper, right, lower)
    :param image_size: 图片的尺寸 (width, height)
    """
    left, upper, right, lower = crop_area
    img_width, img_height = image_size

    if left < 0 or upper < 0 or right > img_width or lower > img_height or left >= right or upper >= lower:
        raise ValueError(f"Invalid crop area {crop_area} for image size {image_size}")

def crop_image(image_path, output_folder, crop_area):
    """
    裁剪图片并保存到指定文件夹
    :param image_path: 图片路径
    :param output_folder: 输出文件夹
    :param crop_area: 裁剪区域 (left, upper, right, lower)
    """
    try:
        img = Image.open(image_path)
        validate_crop_area(crop_area, img.size)  # 验证裁剪区域
        cropped_img = img.crop(crop_area)
        base_name = os.path.basename(image_path)
        output_path = os.path.join(output_folder, base_name)
        cropped_img.save(output_path, format='JPEG', optimize=True, quality=85)  # 保存优化后的图片
        logging.info(f"Processed and saved: {output_path}")
    except FileNotFoundError:
        logging.error(f"File not found: {image_path}")
    except OSError:
        logging.error(f"Invalid image file: {image_path}")
    except Exception as e:
        logging.error(f"Error processing {image_path}: {e}")

def process_images_in_parallel(input_folder, output_folder, crop_area, num_workers=4):
    """
    使用多进程并行处理文件夹下的所有图片
    :param input_folder: 输入文件夹
    :param output_folder: 输出文件夹
    :param crop_area: 裁剪区域 (left, upper, right, lower)
    :param num_workers: 进程数
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    image_files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, f))]

    with Pool(num_workers) as pool:
        pool.starmap(crop_image, [(image_file, output_folder, crop_area) for image_file in image_files])

def main(input_folder, output_folder, crop_area):
    """
    主函数，用于处理输入参数并调用图片处理函数
    :param input_folder: 输入文件夹
    :param output_folder: 输出文件夹
    :param crop_area: 裁剪区域 (left, upper, right, lower)
    """
    process_images_in_parallel(input_folder, output_folder, crop_area)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Batch crop images from a folder.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing images.')
    parser.add_argument('output_folder', type=str, help='Path to the output folder to save cropped images.')
    parser.add_argument('crop_area', type=int, nargs=4, help='Crop area as four integers: left, upper, right, lower.')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers (default is 4).')

    args = parser.parse_args()

    try:
        main(args.input_folder, args.output_folder, tuple(args.crop_area))
    except Exception as e:
        logging.error(f"Error in processing: {e}")
        print(f"Error: {e}")
