import os
from PIL import Image
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

def resize_and_crop(image_path, output_folder, target_width, target_height):
    try:
        # 支持中文路径
        image = Image.open(image_path).convert("RGB")
        src_width, src_height = image.size

        # 计算放大比例
        scale = max(target_width / src_width, target_height / src_height)
        new_size = (int(src_width * scale), int(src_height * scale))
        image = image.resize(new_size, Image.LANCZOS)

        # 居中裁剪
        left = (new_size[0] - target_width) // 2
        top = (new_size[1] - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        image = image.crop((left, top, right, bottom))

        # 保存
        filename = os.path.basename(image_path)
        save_path = os.path.join(output_folder, filename)
        image.save(save_path)

    except Exception as e:
        print(f"处理失败: {image_path} 错误: {e}")

def process_image(args):
    image_path, output_folder, target_width, target_height = args
    resize_and_crop(image_path, output_folder, target_width, target_height)

def batch_process(input_folder, output_folder, target_width, target_height):
    os.makedirs(output_folder, exist_ok=True)

    # 获取所有图片路径
    image_files = [os.path.join(input_folder, f)
                   for f in os.listdir(input_folder)
                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))]

    # 多进程处理
    pool = Pool(processes=cpu_count())

    tasks = [(img, output_folder, target_width, target_height) for img in image_files]

    list(tqdm(pool.imap(process_image, tasks), total=len(tasks), desc="批量处理中"))

    pool.close()
    pool.join()

if __name__ == "__main__":
    # ======== 修改为你的输入输出文件夹路径和目标分辨率 ========
    input_folder = r"D:\桌面\加油站云连锁\砚云读书背景"
    output_folder = r"D:\桌面\加油站云连锁\砚云读书背景output"
    target_width = 1920
    target_height = 1080

    batch_process(input_folder, output_folder, target_width, target_height)
