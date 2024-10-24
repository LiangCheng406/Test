import argparse
from PIL import Image
import os


def crop_image(image_path, output_folder, crop_area):
    """
    裁剪图片并保存到指定文件夹
    :param image_path: 图片路径
    :param output_folder: 输出文件夹
    :param crop_area: 裁剪区域 (left, upper, right, lower)
    """
    img = Image.open(image_path)
    cropped_img = img.crop(crop_area)
    base_name = os.path.basename(image_path)
    output_path = os.path.join(output_folder, base_name)
    cropped_img.save(output_path)
    print(f"Processed and saved: {output_path}")


def process_images(input_folder, output_folder, crop_area):
    """
    批量处理文件夹下的所有图片
    :param input_folder: 输入文件夹
    :param output_folder: 输出文件夹
    :param crop_area: 裁剪区域 (left, upper, right, lower)
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file_name)
        if os.path.isfile(file_path):
            try:
                crop_image(file_path, output_folder, crop_area)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")


def main(input_folder, output_folder, crop_area):
    """
    主函数，用于处理输入参数并调用图片处理函数
    :param input_folder: 输入文件夹
    :param output_folder: 输出文件夹
    :param crop_area: 裁剪区域 (left, upper, right, lower)
    """
    process_images(input_folder, output_folder, crop_area)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Batch crop images from a folder.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing images.')
    parser.add_argument('output_folder', type=str, help='Path to the output folder to save cropped images.')
    parser.add_argument('crop_area', type=int, nargs=4, help='Crop area as four integers: left, upper, right, lower.')

    args = parser.parse_args()

    main(args.input_folder, args.output_folder, tuple(args.crop_area))