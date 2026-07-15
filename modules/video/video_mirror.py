import os
import subprocess
import time
import platform
from pathlib import Path

# Windows 下隐藏命令行黑框的标志
if platform.system() == "Windows":
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


class VideoMirrorEngine:
    def __init__(self):
        # 支持的视频格式（包含大小写）
        lowercase_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.ts'}
        self.supported_formats = lowercase_formats | {fmt.upper() for fmt in lowercase_formats}

        self.stop_processing = False
        self.gpu_acceleration = None
        self.gpu_config = {}

        # 初始化时自动检测系统最佳 GPU 加速方案
        self.detect_gpu_acceleration()

    # ==========================================
    # GPU 硬件检测与配置模块（与之前一致，保持极致性能）
    # ==========================================
    def detect_gpu_info(self):
        gpu_info = {'nvidia': False, 'amd': False, 'intel': False, 'nvidia_devices': [], 'amd_devices': [],
                    'intel_devices': []}
        try:
            if platform.system() == "Windows":
                result = subprocess.run(["wmic", "path", "win32_VideoController", "get", "name"],
                                        capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore',
                                        creationflags=CREATE_NO_WINDOW)
                if result.returncode == 0:
                    lines = [line.strip() for line in result.stdout.lower().split('\n') if
                             line.strip() and 'name' not in line.lower()]
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
        except Exception:
            pass
        return gpu_info

    def check_ffmpeg_gpu_support(self):
        encoders = {'h264_nvenc': False, 'h264_amf': False, 'h264_qsv': False}
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5,
                                    encoding='utf-8', errors='ignore', creationflags=CREATE_NO_WINDOW)
            if result.returncode == 0:
                output = result.stdout.lower()
                for encoder in encoders.keys():
                    if encoder in output: encoders[encoder] = True
        except Exception:
            pass
        return encoders

    def get_optimal_gpu_config(self, gpu_info, ffmpeg_encoders):
        config = {'use_gpu': False, 'encoder': 'libx264', 'gpu_type': None}
        if gpu_info['nvidia'] and ffmpeg_encoders['h264_nvenc']:
            config.update({'use_gpu': True, 'encoder': 'h264_nvenc', 'gpu_type': 'NVIDIA'})
        elif gpu_info['amd'] and ffmpeg_encoders['h264_amf']:
            config.update({'use_gpu': True, 'encoder': 'h264_amf', 'gpu_type': 'AMD'})
        elif gpu_info['intel'] and ffmpeg_encoders['h264_qsv']:
            config.update({'use_gpu': True, 'encoder': 'h264_qsv', 'gpu_type': 'Intel'})
        return config

    def detect_gpu_acceleration(self):
        print("\n" + "=" * 50)
        print("🔍 正在检测系统硬件与加速配置...")
        gpu_info = self.detect_gpu_info()
        ffmpeg_encoders = self.check_ffmpeg_gpu_support()
        optimal_config = self.get_optimal_gpu_config(gpu_info, ffmpeg_encoders)

        if optimal_config['use_gpu']:
            self.gpu_acceleration = optimal_config['gpu_type'].lower()
            print(f"✅ 检测到 {optimal_config['gpu_type']} GPU。将启用极速硬件加速！")
        else:
            self.gpu_acceleration = None
            print("⚠️ 未检测到适用的 GPU 加速，将自动降级使用 CPU 处理。")
        self.gpu_config = optimal_config
        print("=" * 50 + "\n")

    def get_gpu_codec_params(self):
        if self.gpu_acceleration == 'nvidia':
            return {'codec': 'h264_nvenc', 'ffmpeg_params': ['-preset', 'p4', '-cq', '20', '-pix_fmt', 'yuv420p']}
        elif self.gpu_acceleration == 'amd':
            return {'codec': 'h264_amf', 'ffmpeg_params': ['-quality', 'balanced', '-pix_fmt', 'yuv420p']}
        elif self.gpu_acceleration == 'intel':
            return {'codec': 'h264_qsv', 'ffmpeg_params': ['-preset', 'medium', '-pix_fmt', 'yuv420p']}
        else:
            return {'codec': 'libx264',
                    'ffmpeg_params': ['-preset', 'superfast', '-crf', '23', '-threads', '4', '-pix_fmt', 'yuv420p']}

    # ==========================================
    # 核心业务模块：多项目批量隔离处理
    # ==========================================
    def process_master_folder(self, master_input_dir, master_output_dir):
        """
        处理主文件夹：遍历里面的一级子文件夹，将它们视为独立的项目(项目池)
        """
        if not os.path.exists(master_input_dir):
            print(f"❌ 错误：主文件夹不存在 {master_input_dir}")
            return

        print(f"🚀 开始扫描主文件夹: {master_input_dir}")

        # 获取所有的子文件夹（视为任务包），以及主文件夹里散落的视频
        project_folders = []
        loose_videos = []

        # 只扫描第一层（区分出 文件夹 和 独立文件）
        for item in os.listdir(master_input_dir):
            item_path = os.path.join(master_input_dir, item)
            if os.path.isdir(item_path):
                project_folders.append(item)
            elif os.path.isfile(item_path) and Path(item).suffix.lower() in self.supported_formats:
                loose_videos.append(item_path)

        total_projects = len(project_folders)
        print(f"📦 共发现 {total_projects} 个项目文件夹，以及 {len(loose_videos)} 个散装视频。")

        # 1. 挨个处理每一个项目文件夹
        for idx, project_name in enumerate(project_folders, 1):
            if self.stop_processing:
                break

            print(f"\n" + "-" * 40)
            print(f"🎯 正在处理第 {idx}/{total_projects} 个项目: 【{project_name}】")
            project_input_path = os.path.join(master_input_dir, project_name)

            # 为该项目创建独立的隔离输出房间
            project_output_path = os.path.join(master_output_dir, f"{project_name}_mirror")

            # 调用内部处理器去执行这个项目
            self._process_single_project(project_input_path, project_output_path)

        # 2. 如果主文件夹下面本身就扔了几个零散的视频，帮它们也建一个暂存室处理掉
        if loose_videos and not self.stop_processing:
            print(f"\n" + "-" * 40)
            print(f"🎯 正在处理散装视频...")
            misc_output_path = os.path.join(master_output_dir, "散装视频_mirror")
            self._process_loose_videos(loose_videos, misc_output_path)

        print("\n" + "🎉" * 10 + " 所有项目全部处理完毕！ " + "🎉" * 10)

    def _process_single_project(self, input_dir, output_dir):
        """
        处理单个项目的深度提取与镜像
        """
        os.makedirs(output_dir, exist_ok=True)
        tasks = []

        # 深度挖出该项目里所有的视频
        for root, dirs, files in os.walk(input_dir):
            for f in files:
                ext = Path(f).suffix
                if ext.lower() in self.supported_formats:
                    input_path = os.path.join(root, f)
                    name = Path(f).stem
                    new_filename = f"{name}_mirror{ext}"
                    output_path = os.path.join(output_dir, new_filename)

                    # 防止扁平化后同名文件覆盖机制
                    counter = 1
                    while output_path in [t[1] for t in tasks]:
                        new_filename = f"{name}_mirror_{counter}{ext}"
                        output_path = os.path.join(output_dir, new_filename)
                        counter += 1

                    tasks.append((input_path, output_path))

        self._execute_ffmpeg_tasks(tasks, output_dir)

    def _process_loose_videos(self, video_paths, output_dir):
        """
        处理零散视频
        """
        os.makedirs(output_dir, exist_ok=True)
        tasks = []
        for input_path in video_paths:
            name = Path(input_path).stem
            ext = Path(input_path).suffix
            new_filename = f"{name}_mirror{ext}"
            output_path = os.path.join(output_dir, new_filename)
            tasks.append((input_path, output_path))

        self._execute_ffmpeg_tasks(tasks, output_dir)

    def _execute_ffmpeg_tasks(self, tasks, output_dir):
        """
        执行 FFmpeg 队列（共用逻辑）
        """
        total_tasks = len(tasks)
        if total_tasks == 0:
            print("   ↳ 该项目为空，跳过。")
            return

        print(f"   ↳ 提取出 {total_tasks} 个视频，目标目录: {output_dir}")

        codec_info = self.get_gpu_codec_params()
        video_codec = codec_info['codec']
        codec_params = codec_info['ffmpeg_params']

        success_count = 0
        for idx, (in_path, out_path) in enumerate(tasks, 1):
            if self.stop_processing:
                break

            file_name = os.path.basename(in_path)

            cmd = [
                      'ffmpeg', '-y',
                      '-i', in_path,
                      '-map', '0:v', '-map', '0:a?',
                      '-vf', 'hflip',
                      '-c:v', video_codec
                  ] + codec_params + [
                      '-c:a', 'copy',
                      out_path
                  ]

            try:
                t0 = time.time()
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore',
                                        creationflags=CREATE_NO_WINDOW)
                if result.returncode == 0:
                    success_count += 1
                    cost = time.time() - t0
                    print(f"      [{idx}/{total_tasks}] ✅ {cost:.2f}s | {file_name}")
                else:
                    print(f"      [{idx}/{total_tasks}] ❌ 失败 | {file_name}")
            except Exception as e:
                print(f"      [{idx}/{total_tasks}] ❌ 崩溃 | {e}")


if __name__ == "__main__":
    # ⬇️ 你的主文件夹和输出文件夹
    MASTER_INPUT = r"D:\桌面\01视频素材\TK\input"  # 里面包含降落伞、滑雪等多个文件夹
    MASTER_OUTPUT = r"D:\桌面\01视频素材\TK\output"

    engine = VideoMirrorEngine()
    engine.process_master_folder(MASTER_INPUT, MASTER_OUTPUT)