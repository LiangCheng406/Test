import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
except ImportError:
    os.system('pip install tqdm')
    from tqdm import tqdm

# ==================== ⚠️ 核心参数设置区 ====================

# 1. 路径设置 (将这里的路径换成你的图片所在文件夹)
input_folder = r"Z:\BD商家素材\酒店类\简阳可玺潮牌酒店(1)\房间"
output_folder = r"Z:\BD商家素材\酒店类\简阳可玺潮牌酒店(1)\房间\output"

# 2. 性能设置
max_workers = 4  # 并行任务数，取决于你的电脑性能（一般 4-8 即可）

# 3. 滤镜参数 (美食专属：暖色调、高饱和、微提亮、强锐化)
# ⚠️ 注意：unsharp 矩阵必须为奇数 (这里已经使用修复后的 7:7)
FOOD_FILTER = "colorbalance=rs=0.1:gs=0.05:bs=-0.05,eq=brightness=0.06:saturation=1.3,unsharp=7:7:1.0:7:7:0.5"


# ==========================================================

def process_image(img_path, output_dir):
    """处理单张图片的调色逻辑"""
    img_name = os.path.basename(img_path)
    pure_name, ext = os.path.splitext(img_name)

    # 为了保证高质量压缩和跨平台兼容，统一输出为 .jpg 格式
    output_filename = f"{pure_name}_美食调色.jpg"
    output_path = os.path.join(output_dir, output_filename)

    try:
        # FFmpeg 图片处理命令
        cmd = [
            'ffmpeg', '-y',  # -y 覆盖同名文件
            '-i', img_path,  # 输入文件
            '-vf', FOOD_FILTER,  # 应用美食调色滤镜
            '-q:v', '2',  # 设置极高的 JPEG 输出质量 (1-3 最佳，2 是极佳平衡)
            output_path
        ]

        sub_res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='ignore')

        # 校验 1：命令是否执行失败
        if sub_res.returncode != 0:
            error_msg = sub_res.stderr.strip().split('\n')[-1] if sub_res.stderr else "未知错误"
            return False, f"[{img_name}] 失败: {error_msg}"

        # 校验 2：物理文件是否存在，且大小是否大于 0 字节
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, img_name
        else:
            return False, f"[{img_name}] 失败: 生成了空文件"

    except Exception as e:
        return False, f"[{img_name}] 代码异常: {str(e)}"


def main():
    if not os.path.exists(input_folder):
        print(f"❌ 找不到输入路径: {input_folder}")
        return

    # 创建带有时间戳的输出总文件夹，避免多次运行覆盖
    t_str = str(int(time.time()))
    current_output_dir = os.path.join(output_folder, f"美食调色批处理_{t_str}")
    os.makedirs(current_output_dir, exist_ok=True)

    all_images = []

    # 支持的图片格式
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')

    # 扫描输入文件夹下的所有图片 (支持多层级子文件夹)
    for root, dirs, files in os.walk(input_folder):
        # 如果把输出目录建在了输入目录里面，防死循环跳过它
        if os.path.abspath(output_folder) in os.path.abspath(root):
            continue

        for f in files:
            if f.lower().endswith(valid_extensions):
                all_images.append(os.path.join(root, f))

    if not all_images:
        print("❌ 未在指定文件夹中发现图片，请检查路径或文件格式。")
        return

    print(f"🚀[美食图片一键调色] 任务启动！")
    print(f"📸 发现待处理图片: {len(all_images)} 张")
    print(f"✨ 核心滤镜: 暖色温叠加 + 提亮增艳 + 高级锐化\n")
    print("-" * 50)

    success_cnt = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有图片处理任务
        futures = {executor.submit(process_image, img_path, current_output_dir): img_path for img_path in all_images}

        with tqdm(total=len(all_images), desc="正在给美食注入灵魂", unit="张") as pbar:
            for future in as_completed(futures):
                success, msg = future.result()
                if success:
                    success_cnt += 1
                else:
                    tqdm.write(f"⚠️ {msg}")  # 失败时打印醒目日志
                pbar.update(1)

    print("-" * 50)
    print(f"✅ 批量处理完成！")
    print(f"📈 成功调色: {success_cnt} / {len(all_images)} 张图片")
    if success_cnt > 0:
        print(f"📁 请查收你的大片: {current_output_dir}")


if __name__ == "__main__":
    main()