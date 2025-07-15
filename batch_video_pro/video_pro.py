import subprocess
import random
import os
import platform


def detect_gpu_info():
    """检测系统中的GPU信息"""
    gpu_info = {
        'nvidia': False,
        'amd': False,
        'intel': False,
        'nvidia_devices': [],
        'amd_devices': [],
        'intel_devices': []
    }

    try:
        # 使用wmic命令检测GPU（Windows）
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )

            if result.returncode == 0:
                output = result.stdout.lower()
                lines = [line.strip() for line in output.split('\n') if line.strip() and 'name' not in line.lower()]

                for line in lines:
                    if 'nvidia' in line or 'geforce' in line or 'rtx' in line or 'gtx' in line:
                        gpu_info['nvidia'] = True
                        gpu_info['nvidia_devices'].append(line)
                    elif 'amd' in line or 'radeon' in line:
                        gpu_info['amd'] = True
                        gpu_info['amd_devices'].append(line)
                    elif 'intel' in line:
                        gpu_info['intel'] = True
                        gpu_info['intel_devices'].append(line)

        # 也可以尝试通过nvidia-smi检测NVIDIA GPU
        try:
            nvidia_result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
            if nvidia_result.returncode == 0:
                nvidia_gpus = [gpu.strip() for gpu in nvidia_result.stdout.split('\n') if gpu.strip()]
                if nvidia_gpus:
                    gpu_info['nvidia'] = True
                    gpu_info['nvidia_devices'].extend(nvidia_gpus)
        except:
            pass

    except Exception as e:
        print(f"⚠️ GPU检测遇到问题: {e}")

    return gpu_info


def check_ffmpeg_gpu_support():
    """检查FFmpeg支持的GPU编码器"""
    encoders = {
        'h264_nvenc': False,  # NVIDIA
        'h264_amf': False,  # AMD
        'h264_qsv': False,  # Intel Quick Sync
        'hevc_nvenc': False,  # NVIDIA HEVC
        'hevc_amf': False,  # AMD HEVC
        'hevc_qsv': False  # Intel HEVC
    }

    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode == 0:
            output = result.stdout.lower()
            for encoder in encoders.keys():
                if encoder in output:
                    encoders[encoder] = True

    except Exception as e:
        print(f"⚠️ FFmpeg编码器检测失败: {e}")

    return encoders


def get_optimal_gpu_config(gpu_info, ffmpeg_encoders):
    """根据GPU信息获取最佳配置"""
    config = {
        'use_gpu': False,
        'encoder': 'libx264',
        'hwaccel': None,
        'gpu_type': None,
        'recommended': []
    }

    # 优先级：NVIDIA > AMD > Intel
    if gpu_info['nvidia'] and ffmpeg_encoders['h264_nvenc']:
        config.update({
            'use_gpu': True,
            'encoder': 'h264_nvenc',
            'hwaccel': 'cuda',
            'gpu_type': 'NVIDIA',
            'recommended': ['nvenc_basic', 'nvenc_cuda', 'nvenc_software']
        })

    elif gpu_info['amd'] and ffmpeg_encoders['h264_amf']:
        config.update({
            'use_gpu': True,
            'encoder': 'h264_amf',
            'hwaccel': 'd3d11va',  # AMD推荐使用D3D11
            'gpu_type': 'AMD',
            'recommended': ['amf_basic', 'amf_d3d11', 'amf_software']
        })

    elif gpu_info['intel'] and ffmpeg_encoders['h264_qsv']:
        config.update({
            'use_gpu': True,
            'encoder': 'h264_qsv',
            'hwaccel': 'qsv',
            'gpu_type': 'Intel',
            'recommended': ['qsv_basic', 'qsv_software']
        })

    return config


def print_system_info(gpu_info, ffmpeg_encoders, optimal_config):
    """显示系统GPU信息"""
    print("🖥️ 系统GPU信息:")
    print("-" * 40)

    if gpu_info['nvidia_devices']:
        print("🟢 NVIDIA GPU:")
        for device in gpu_info['nvidia_devices']:
            print(f"   - {device}")

    if gpu_info['amd_devices']:
        print("🔴 AMD GPU:")
        for device in gpu_info['amd_devices']:
            print(f"   - {device}")

    if gpu_info['intel_devices']:
        print("🔵 Intel GPU:")
        for device in gpu_info['intel_devices']:
            print(f"   - {device}")

    print("\n🎬 FFmpeg GPU编码器支持:")
    print("-" * 40)

    if ffmpeg_encoders['h264_nvenc']:
        print("✅ NVIDIA NVENC (h264_nvenc)")
    else:
        print("❌ NVIDIA NVENC (h264_nvenc)")

    if ffmpeg_encoders['h264_amf']:
        print("✅ AMD AMF (h264_amf)")
    else:
        print("❌ AMD AMF (h264_amf)")

    if ffmpeg_encoders['h264_qsv']:
        print("✅ Intel QSV (h264_qsv)")
    else:
        print("❌ Intel QSV (h264_qsv)")

    print(f"\n🚀 推荐配置:")
    print("-" * 40)
    if optimal_config['use_gpu']:
        print(f"GPU类型: {optimal_config['gpu_type']}")
        print(f"编码器: {optimal_config['encoder']}")
        print(f"硬件加速: {optimal_config['hwaccel']}")
    else:
        print("推荐使用CPU编码 (未检测到可用的GPU加速)")


def get_video_duration(video_path):
    """获取视频的总时长（以秒为单位）"""
    try:
        result = subprocess.run(
            ["ffprobe.exe", "-v", "quiet", "-show_entries", "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1",
             video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            encoding='utf-8',
            errors='ignore'
        )
        return float(result.stdout.strip())
    except:
        print(f"❌ 无法获取视频时长: {video_path}")
        return None


def extract_random_frame(video_path, output_image):
    """从视频中随机抽取一帧并保存为图片"""
    duration = get_video_duration(video_path)
    if duration is None:
        return False

    random_time = random.uniform(0, duration)

    ffmpeg_command = [
        "ffmpeg.exe",
        "-ss", f"{random_time:.2f}",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        "-y",
        output_image
    ]

    try:
        result = subprocess.run(
            ffmpeg_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode == 0:
            print(f"帧已抽取并保存为: {output_image} (抽取时间点: {random_time:.2f} 秒)")
            return True
        else:
            print(f"❌ 抽取失败")
            return False
    except Exception as e:
        print(f"❌ 抽取过程中出现错误: {str(e)}")
        return False


def change_video_resolution_nvidia(input_video, output_video, width, height, quality, method):
    """NVIDIA GPU处理方案"""
    quality_settings = {"high": "18", "medium": "23", "low": "28"}
    crf_value = quality_settings.get(quality, "23")

    methods = {
        'nvenc_basic': [
            "ffmpeg.exe",
            "-i", input_video,
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", "h264_nvenc",
            "-cq", crf_value,
            "-preset", "p4",
            "-profile:v", "main",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_video
        ],
        'nvenc_cuda': [
            "ffmpeg.exe",
            "-hwaccel", "cuda",
            "-i", input_video,
            "-vf", f"hwdownload,format=yuv420p,scale={width}:{height}:flags=lanczos",
            "-c:v", "h264_nvenc",
            "-cq", crf_value,
            "-preset", "p6",
            "-profile:v", "main",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_video
        ],
        'nvenc_software': [
            "ffmpeg.exe",
            "-i", input_video,
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", "h264_nvenc",
            "-b:v", "5M", "-maxrate", "8M", "-bufsize", "10M",
            "-preset", "slow", "-profile:v", "main",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_video
        ]
    }

    return methods.get(method, methods['nvenc_basic'])


def change_video_resolution_amd(input_video, output_video, width, height, quality, method):
    """AMD GPU处理方案"""
    quality_settings = {"high": "18", "medium": "23", "low": "28"}
    crf_value = quality_settings.get(quality, "23")

    methods = {
        'amf_basic': [
            "ffmpeg.exe",
            "-i", input_video,
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", "h264_amf",
            "-qp_i", crf_value, "-qp_p", crf_value,
            "-quality", "balanced",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_video
        ],
        'amf_d3d11': [
            "ffmpeg.exe",
            "-hwaccel", "d3d11va",
            "-i", input_video,
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", "h264_amf",
            "-qp_i", crf_value, "-qp_p", crf_value,
            "-quality", "balanced",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_video
        ],
        'amf_software': [
            "ffmpeg.exe",
            "-i", input_video,
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", "h264_amf",
            "-b:v", "5M", "-maxrate", "8M",
            "-quality", "speed",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_video
        ]
    }

    return methods.get(method, methods['amf_basic'])


def change_video_resolution_intel(input_video, output_video, width, height, quality, method):
    """Intel GPU处理方案"""
    quality_settings = {"high": "18", "medium": "23", "low": "28"}
    crf_value = quality_settings.get(quality, "23")

    methods = {
        'qsv_basic': [
            "ffmpeg.exe",
            "-i", input_video,
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", "h264_qsv",
            "-q", crf_value,
            "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_video
        ],
        'qsv_software': [
            "ffmpeg.exe",
            "-i", input_video,
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", "h264_qsv",
            "-b:v", "5M", "-maxrate", "8M",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_video
        ]
    }

    return methods.get(method, methods['qsv_basic'])


def change_video_resolution(input_video, output_video, width, height, quality="medium", gpu_config=None,
                            force_gpu=False):
    """使用FFmpeg修改视频分辨率"""

    if gpu_config and gpu_config['use_gpu']:
        gpu_type = gpu_config['gpu_type']
        methods = gpu_config['recommended']

        print(f"🚀 使用{gpu_type} GPU加速转换视频分辨率: {width}x{height}")

        for i, method in enumerate(methods, 1):
            print(f"🧪 尝试{gpu_type}方案{i}: {method}")

            # 根据GPU类型选择命令
            if gpu_type == 'NVIDIA':
                ffmpeg_command = change_video_resolution_nvidia(input_video, output_video, width, height, quality,
                                                                method)
            elif gpu_type == 'AMD':
                ffmpeg_command = change_video_resolution_amd(input_video, output_video, width, height, quality, method)
            elif gpu_type == 'Intel':
                ffmpeg_command = change_video_resolution_intel(input_video, output_video, width, height, quality,
                                                               method)
            else:
                continue

            try:
                print(f"输入文件: {input_video}")
                print(f"输出文件: {output_video}")

                result = subprocess.run(
                    ffmpeg_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    encoding='utf-8',
                    errors='ignore'
                )

                if result.returncode == 0:
                    print(f"✅ {gpu_type}方案{i}成功！")
                    return True
                else:
                    print(f"❌ {gpu_type}方案{i}失败")

            except Exception as e:
                print(f"❌ {gpu_type}方案{i}异常: {str(e)}")

        if not force_gpu:
            print("🔄 所有GPU方案失败，切换到CPU编码...")
        else:
            print("❌ 所有GPU方案都失败")
            return False

    # CPU编码方案
    if not gpu_config or not gpu_config['use_gpu'] or not force_gpu:
        quality_settings = {"high": "18", "medium": "23", "low": "28"}
        crf_value = quality_settings.get(quality, "23")

        ffmpeg_command = [
            "ffmpeg.exe",
            "-i", input_video,
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", "libx264",
            "-crf", crf_value,
            "-preset", "medium",
            "-profile:v", "main",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", output_video
        ]

        print(f"💻 使用CPU转换视频分辨率: {width}x{height}")

        try:
            print(f"输入文件: {input_video}")
            print(f"输出文件: {output_video}")

            result = subprocess.run(
                ffmpeg_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode == 0:
                print(f"✅ CPU处理成功！")
                return True
            else:
                print(f"❌ CPU处理失败")
                return False

        except Exception as e:
            print(f"❌ CPU处理异常: {str(e)}")
            return False


def get_acceleration_choice(optimal_config):
    """获取用户的加速选择"""
    if not optimal_config['use_gpu']:
        print("💻 将使用CPU编码（未检测到可用的GPU加速）")
        return False, False

    gpu_type = optimal_config['gpu_type']
    print(f"\n加速选择 (检测到{gpu_type} GPU):")
    print(f"1. 智能{gpu_type}模式 (推荐，GPU失败时自动切换CPU)")
    print(f"2. 强制{gpu_type}模式 (只使用{gpu_type}，不降级)")
    print("3. 仅使用CPU编码")

    while True:
        choice = input("请选择加速方式 (1-3, 默认1): ").strip() or "1"
        if choice == "1":
            print(f"🤖 已选择智能{gpu_type}模式")
            return True, False
        elif choice == "2":
            print(f"💪 已选择强制{gpu_type}模式")
            return True, True
        elif choice == "3":
            print("💻 已选择CPU编码")
            return False, False
        else:
            print("❌ 无效选择，请输入1-3")


def batch_change_resolution(input_folder, output_folder, width, height, quality="medium", gpu_config=None,
                            force_gpu=False):
    """批量修改文件夹中所有视频的分辨率"""
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v')
    os.makedirs(output_folder, exist_ok=True)

    video_files = []
    for file in os.listdir(input_folder):
        if file.lower().endswith(video_extensions):
            video_files.append(file)

    if not video_files:
        print(f"❌ 在文件夹 {input_folder} 中未找到支持的视频文件")
        return

    print(f"📁 找到 {len(video_files)} 个视频文件")

    if gpu_config and gpu_config['use_gpu']:
        gpu_type = gpu_config['gpu_type']
        if force_gpu:
            print(f"💪 使用强制{gpu_type}模式批量处理")
        else:
            print(f"🚀 使用智能{gpu_type}模式批量处理")
    else:
        print("💻 使用CPU批量处理")

    success_count = 0
    failed_files = []

    for i, video_file in enumerate(video_files, 1):
        input_path = os.path.join(input_folder, video_file)
        name, ext = os.path.splitext(video_file)
        output_filename = f"{name}_{width}x{height}{ext}"
        output_path = os.path.join(output_folder, output_filename)

        print(f"\n🎬 处理第 {i}/{len(video_files)} 个视频: {video_file}")

        if change_video_resolution(input_path, output_path, width, height, quality, gpu_config, force_gpu):
            success_count += 1
        else:
            failed_files.append(video_file)

    print(f"\n🎉 批量处理完成！")
    print(f"✅ 成功处理: {success_count}/{len(video_files)} 个视频")

    if failed_files:
        print(f"❌ 处理失败的文件:")
        for file in failed_files:
            print(f"   - {file}")


if __name__ == "__main__":
    print("🎬 智能视频处理工具 (多GPU支持)")
    print("=" * 60)

    # 检测系统GPU信息
    print("🔍 检测系统GPU配置...")
    gpu_info = detect_gpu_info()
    ffmpeg_encoders = check_ffmpeg_gpu_support()
    optimal_config = get_optimal_gpu_config(gpu_info, ffmpeg_encoders)

    print_system_info(gpu_info, ffmpeg_encoders, optimal_config)
    print("=" * 60)

    print("功能选择:")
    print("1. 抽取随机帧")
    print("2. 修改视频分辨率")
    print("3. 批量修改视频分辨率")

    choice = input("\n请选择功能 (1-3): ").strip()

    if choice == "1":
        video_file = input("请输入视频文件路径: ").strip()
        output_image = input("请输入输出图片路径 (如: output.png): ").strip()

        if not os.path.isfile(video_file):
            print(f"❌ 视频文件 {video_file} 不存在！")
        else:
            extract_random_frame(video_file, output_image)

    elif choice == "2":
        input_video = input("请输入视频文件路径: ").strip()
        output_video = input("请输入输出视频路径: ").strip()

        if not os.path.isfile(input_video):
            print(f"❌ 视频文件 {input_video} 不存在！")
        else:
            print("\n常用分辨率:")
            print("1. 1920x1080 (1080p)")
            print("2. 1280x720 (720p)")
            print("3. 854x480 (480p)")
            print("4. 640x360 (360p)")
            print("5. 自定义")

            res_choice = input("请选择分辨率 (1-5): ").strip()

            if res_choice == "1":
                width, height = 1920, 1080
            elif res_choice == "2":
                width, height = 1280, 720
            elif res_choice == "3":
                width, height = 854, 480
            elif res_choice == "4":
                width, height = 640, 360
            elif res_choice == "5":
                try:
                    width = int(input("请输入宽度: "))
                    height = int(input("请输入高度: "))
                except ValueError:
                    print("❌ 请输入有效的数字！")
                    exit(1)
            else:
                print("❌ 无效选择！")
                exit(1)

            print("\n质量选择:")
            print("1. 高质量 (文件较大)")
            print("2. 中等质量 (推荐)")
            print("3. 低质量 (文件较小)")

            quality_choice = input("请选择质量 (1-3, 默认2): ").strip() or "2"
            quality_map = {"1": "high", "2": "medium", "3": "low"}
            quality = quality_map.get(quality_choice, "medium")

            use_gpu, force_gpu = get_acceleration_choice(optimal_config)
            gpu_config = optimal_config if use_gpu else None
            change_video_resolution(input_video, output_video, width, height, quality, gpu_config, force_gpu)

    elif choice == "3":
        input_folder = input("请输入视频文件夹路径: ").strip()
        output_folder = input("请输入输出文件夹路径: ").strip()

        if not os.path.isdir(input_folder):
            print(f"❌ 文件夹 {input_folder} 不存在！")
        else:
            print("\n常用分辨率:")
            print("1. 1920x1080 (1080p)")
            print("2. 1280x720 (720p)")
            print("3. 854x480 (480p)")
            print("4. 640x360 (360p)")
            print("5. 自定义")

            res_choice = input("请选择分辨率 (1-5): ").strip()

            if res_choice == "1":
                width, height = 1920, 1080
            elif res_choice == "2":
                width, height = 1280, 720
            elif res_choice == "3":
                width, height = 854, 480
            elif res_choice == "4":
                width, height = 640, 360
            elif res_choice == "5":
                try:
                    width = int(input("请输入宽度: "))
                    height = int(input("请输入高度: "))
                except ValueError:
                    print("❌ 请输入有效的数字！")
                    exit(1)
            else:
                print("❌ 无效选择！")
                exit(1)

            print("\n质量选择:")
            print("1. 高质量 (文件较大)")
            print("2. 中等质量 (推荐)")
            print("3. 低质量 (文件较小)")

            quality_choice = input("请选择质量 (1-3, 默认2): ").strip() or "2"
            quality_map = {"1": "high", "2": "medium", "3": "low"}
            quality = quality_map.get(quality_choice, "medium")

            use_gpu, force_gpu = get_acceleration_choice(optimal_config)
            gpu_config = optimal_config if use_gpu else None
            batch_change_resolution(input_folder, output_folder, width, height, quality, gpu_config, force_gpu)

    else:
        print("❌ 无效选择！")