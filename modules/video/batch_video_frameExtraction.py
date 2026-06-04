import os
import subprocess
import time
import shutil
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
except ImportError:
    os.system('pip install tqdm')
    from tqdm import tqdm

# ==================== ⚠️ 核心参数设置区 ====================

# 1. 路径设置 (网络磁盘路径)
video_folder = r"Z:\火牛商家素材\【小舒仙采耳】\调色\【小舒仙采耳】- 全身按摩"
output_folder = r"Z:\火牛商家素材\【小舒仙采耳】\调色\output"

# 2. 抽帧数量控制
num_videos_per_folder = None
total_frames = 2

# 3. 调色模式选择 (1:原色, 2:美食暖调, 3:酒店冷调)
color_mode = 1

# 4. 性能与【网络容错】设置
max_workers = 4  # 并行任务数
network_max_retries = 3  # ⚠️ 单个视频断网/失败最大重试次数
network_wait_time = 10  # ⚠️ 每次重试前等待的秒数 (给网络恢复的时间)
ffmpeg_timeout = 30  # ⚠️ FFmpeg防卡死超时时间(秒)


# ==========================================================

def wait_for_network_drive(path):
    """主程序网络盘就绪检测"""
    if os.path.exists(path):
        return True

    print(f"⚠️ 检测到目标路径不可达: {path}")
    print("⏳ 正在等待网络磁盘恢复连通...")

    # 尝试等待5次，每次10秒
    for i in range(5):
        time.sleep(10)
        if os.path.exists(path):
            print("✅ 网络磁盘已恢复！")
            return True
        print(f"   等待中... ({i + 1}/5)")

    return False


def get_video_duration(video_path):
    """获取视频时长"""
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
           video_path]
    try:
        # 加入防卡死 timeout
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='ignore',
                                timeout=15)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        return None
    return None


def get_color_filter(mode):
    """根据模式返回 FFmpeg 滤镜字符串"""
    if mode == 2:
        return "colorbalance=rs=0.1:gs=0.05:bs=-0.05,eq=brightness=0.05:saturation=1.3,unsharp=7:7:1.0:7:7:0.5"
    elif mode == 3:
        return "colorbalance=bs=0.08,eq=brightness=0.04:contrast=1.15:saturation=1.1,unsharp=5:5:0.7:5:5:0.3"
    else:
        return "unsharp=5:5:0.8:5:5:0.4"


def process_video_core(video_file, timestamp_folder):
    """单个视频处理核心逻辑 (不含重试)"""
    video_name = os.path.basename(video_file)
    pure_name = os.path.splitext(video_name)[0]

    # 检查文件是否在网络上可读 (防断网第一关)
    if not os.path.exists(video_file):
        raise FileNotFoundError(f"文件不可达(网络可能断开): {video_file}")

    video_output_dir = os.path.join(output_folder, pure_name)
    os.makedirs(video_output_dir, exist_ok=True)

    duration = get_video_duration(video_file)
    if duration is None:
        raise ValueError("无法读取视频时长(文件可能损坏或网络异常)")

    if duration <= 5:
        random_timestamps = [random.uniform(0, duration) for _ in range(total_frames)]
    else:
        random_timestamps = []
        segment_dur = duration / total_frames
        for i in range(total_frames):
            start = i * segment_dur + (segment_dur * 0.1)
            end = (i + 1) * segment_dur - (segment_dur * 0.1)
            random_timestamps.append(random.uniform(start, end))

    filter_str = get_color_filter(color_mode)
    extracted_count = 0
    error_logs = []

    for i, ts in enumerate(random_timestamps):
        img_filename = f"{i + 1:04d}.jpg"
        local_img_path = os.path.join(video_output_dir, img_filename)

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(round(ts, 3)),
            '-i', video_file,
            '-frames:v', '1',
            '-q:v', '2',
            '-vf', filter_str,
            local_img_path
        ]

        # 核心防卡死：设置 timeout
        sub_res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, errors='ignore', timeout=ffmpeg_timeout)

        if sub_res.returncode != 0:
            error_msg = sub_res.stderr.strip().split('\n')[-1] if sub_res.stderr else "转换失败(网络丢失或格式不支持)"
            error_logs.append(f"帧{i + 1}报错: {error_msg}")
            continue

        # 校验 2：物理文件是否存在，防断网第二关
        if os.path.exists(local_img_path) and os.path.getsize(local_img_path) > 0:
            summary_name = f"{pure_name}_part{i + 1}.jpg"
            shutil.copy2(local_img_path, os.path.join(timestamp_folder, summary_name))  # 这里可能触发 OSError
            extracted_count += 1
        else:
            error_logs.append(f"帧{i + 1}空图")

    if extracted_count > 0:
        return True, pure_name
    else:
        return False, " | ".join(error_logs)


def process_video_with_retry(video_file, timestamp_folder):
    """带网络断开重试机制的包装器"""
    video_name = os.path.basename(video_file)
    last_error = ""

    for attempt in range(1, network_max_retries + 1):
        try:
            success, msg = process_video_core(video_file, timestamp_folder)
            if success:
                return True, msg
            else:
                last_error = msg
                # 如果明确是 FFmpeg 转换错误且非致命，也尝试重试

        except Exception as e:
            last_error = str(e)

        # 如果走到这里，说明当前尝试失败了。如果还没到最后一次，就等待重试
        if attempt < network_max_retries:
            # tqdm.write 可以不打断进度条显示打印信息
            tqdm.write(
                f"⚠️ [{video_name}] 处理异常(可能断网)，等待 {network_wait_time}s 后进行第 {attempt + 1} 次重试...")
            time.sleep(network_wait_time)

    # 重试次数用尽，宣告彻底失败
    return False, f"[{video_name}] 重试{network_max_retries}次后最终失败: {last_error}"


def main():
    # 启动前检测网络盘
    if not wait_for_network_drive(video_folder):
        print("❌ 网络磁盘长时间未响应，程序终止。")
        return

    os.makedirs(output_folder, exist_ok=True)

    mode_names = {1: "原色", 2: "美食暖调", 3: "酒店冷调"}
    current_mode_name = mode_names.get(color_mode, "未知")
    t_str = str(int(time.time()))
    t_folder = os.path.join(os.path.dirname(output_folder), f"{current_mode_name}_抽帧_{t_str}")
    os.makedirs(t_folder, exist_ok=True)

    all_videos_to_process = []

    try:
        # os.walk 也可能因为突然断网抛出异常
        for root, dirs, files in os.walk(video_folder):
            if os.path.abspath(output_folder) in os.path.abspath(root):
                continue

            current_folder_videos = [
                os.path.join(root, f) for f in files
                if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
            ]

            if not current_folder_videos:
                continue

            if num_videos_per_folder is None:
                selected_videos = current_folder_videos
            else:
                count = min(len(current_folder_videos), num_videos_per_folder)
                selected_videos = random.sample(current_folder_videos, count)

            all_videos_to_process.extend(selected_videos)
    except OSError as e:
        print(f"❌ 扫描文件夹时网络连接中断: {e}")
        return

    if not all_videos_to_process:
        print("❌ 未发现可处理的视频，请检查路径。")
        return

    print(f"🚀 任务启动！(已开启网络断开重试保护)")
    print(f"🎨 当前模式: {current_mode_name}")
    print(f"🎥 待处理视频总数: {len(all_videos_to_process)}")
    print(f"--------------------------------------------------")

    success_cnt = 0
    # 使用修改后的 process_video_with_retry
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_video_with_retry, v, t_folder): v for v in all_videos_to_process}
        with tqdm(total=len(all_videos_to_process), desc="正在智能处理", unit="视频") as pbar:
            for future in as_completed(futures):
                success, msg = future.result()
                if success:
                    success_cnt += 1
                else:
                    tqdm.write(f"❌ {msg}")
                pbar.update(1)

    print(f"\n✅ 处理完成！")
    print(f"📈 成功: {success_cnt} / 预计: {len(all_videos_to_process)}")
    if success_cnt > 0:
        print(f"📁 图片汇总目录: {t_folder}")


if __name__ == "__main__":
    main()