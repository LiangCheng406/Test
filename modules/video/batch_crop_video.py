#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频批量裁剪工具 (Pro UI 增强无闪烁版)
功能：批量裁剪视频前几秒、调整分辨率、GPU加速
"""

import os
import sys
import time
import queue
import platform
import shutil
from pathlib import Path
from moviepy.editor import VideoFileClip
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import subprocess
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# 🌟 关键修复：Windows 专属隐身符，用于完全隐藏 subprocess 调用的闪烁黑框
CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0


class PrintRedirector:
    """标准输出重定向器，将 print 信息安全推送到 GUI 的队列中"""

    def __init__(self, text_queue):
        self.text_queue = text_queue

    def write(self, string):
        if string:
            self.text_queue.put(string)

    def flush(self):
        pass


class VideoTrimmer:
    def __init__(self):
        # 支持的视频格式（包含大写和小写）
        lowercase_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        uppercase_formats = {fmt.upper() for fmt in lowercase_formats}
        self.supported_formats = lowercase_formats | uppercase_formats

        self.stop_processing = False  # 停止处理标志
        self.gpu_acceleration = None  # GPU加速类型
        self.max_workers = min(4, multiprocessing.cpu_count())  # 多线程数量
        self.detect_gpu_acceleration()

    def diagnose_amd_acceleration(self):
        """诊断AMD加速问题"""
        print("\n" + "=" * 60)
        print("AMD GPU加速诊断报告")
        print("=" * 60)

        diagnosis_results = {
            'amd_gpu_detected': False,
            'ffmpeg_available': False,
            'amf_encoder_available': False,
            'driver_version': None,
            'gpu_info': None,
            'memory_info': None,
            'recommendations': []
        }

        # 1. 检测AMD GPU硬件
        print("1. 检测AMD GPU硬件...")
        try:
            result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name,DriverVersion,AdapterRAM'],
                                    capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)  # 隐身符
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:
                    if line.strip() and ('AMD' in line or 'Radeon' in line):
                        diagnosis_results['amd_gpu_detected'] = True
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            diagnosis_results['memory_info'] = parts[0] if parts[0].isdigit() else "未知"
                            diagnosis_results['driver_version'] = parts[1] if len(parts) > 1 else "未知"
                            diagnosis_results['gpu_info'] = " ".join(parts[2:]) if len(parts) > 2 else "AMD GPU"
                        print(f"   ✓ 检测到AMD GPU: {diagnosis_results['gpu_info']}")
                        print(f"   - 驱动版本: {diagnosis_results['driver_version']}")
                        if diagnosis_results['memory_info'] != "未知":
                            memory_gb = int(diagnosis_results['memory_info']) / (1024 ** 3) if diagnosis_results[
                                'memory_info'].isdigit() else 0
                            print(f"   - 显存大小: {memory_gb:.1f}GB")
                        break

                if not diagnosis_results['amd_gpu_detected']:
                    print("   ✗ 未检测到AMD GPU")
                    diagnosis_results['recommendations'].append("确认您的电脑确实安装了AMD独立显卡")
            else:
                print("   ✗ 无法获取GPU信息")
        except Exception as e:
            print(f"   ✗ GPU检测失败: {e}")

        # 2. 检测FFmpeg可用性
        print("\n2. 检测FFmpeg可用性...")
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5, encoding='utf-8',
                                    errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)  # 隐身符
            if result.returncode == 0:
                diagnosis_results['ffmpeg_available'] = True
                print("   ✓ FFmpeg已安装")
                version_line = result.stdout.split('\n')[0]
                print(f"   - 版本: {version_line}")
            else:
                print("   ✗ FFmpeg不可用")
                diagnosis_results['recommendations'].append("安装FFmpeg或确保FFmpeg在系统PATH中")
        except Exception as e:
            print(f"   ✗ FFmpeg检测失败: {e}")
            diagnosis_results['recommendations'].append("安装FFmpeg并添加到系统PATH")

        # 3. 检测AMF编码器支持
        print("\n3. 检测AMD AMF编码器支持...")
        if diagnosis_results['ffmpeg_available']:
            try:
                result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=5,
                                        encoding='utf-8', errors='ignore',
                                        creationflags=CREATE_NO_WINDOW)  # 隐身符
                if result.returncode == 0:
                    if 'h264_amf' in result.stdout:
                        diagnosis_results['amf_encoder_available'] = True
                        print("   ✓ h264_amf编码器可用")
                        amf_encoders = []
                        for line in result.stdout.split('\n'):
                            if 'amf' in line.lower() and ('h264' in line or 'h265' in line or 'hevc' in line):
                                encoder_name = line.split()[1] if len(line.split()) > 1 else line.strip()
                                amf_encoders.append(encoder_name)
                        if amf_encoders:
                            print(f"   - 可用的AMF编码器: {', '.join(amf_encoders)}")
                    else:
                        print("   ✗ h264_amf编码器不可用")
                        diagnosis_results['recommendations'].append("更新AMD驱动至最新版本")
                        diagnosis_results['recommendations'].append("确保安装了完整版AMD驱动（包含AMF组件）")
                else:
                    print("   ✗ 无法获取编码器列表")
            except Exception as e:
                print(f"   ✗ 编码器检测失败: {e}")
        else:
            print("   - 跳过（FFmpeg不可用）")

        return diagnosis_results

    def detect_gpu_info(self):
        """检测系统中的GPU信息（增强版）"""
        gpu_info = {
            'nvidia': False, 'amd': False, 'intel': False,
            'nvidia_devices': [], 'amd_devices': [], 'intel_devices': []
        }
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name,DriverVersion,AdapterRAM"],
                    capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore',
                    creationflags=CREATE_NO_WINDOW)  # 隐身符
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

            try:
                nvidia_result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                               capture_output=True, text=True, timeout=5, encoding='utf-8',
                                               errors='ignore',
                                               creationflags=CREATE_NO_WINDOW)  # 隐身符
                if nvidia_result.returncode == 0:
                    nvidia_gpus = [gpu.strip() for gpu in nvidia_result.stdout.split('\n') if gpu.strip()]
                    if nvidia_gpus:
                        gpu_info['nvidia'] = True
                        for gpu in nvidia_gpus:
                            if gpu not in gpu_info['nvidia_devices']:
                                gpu_info['nvidia_devices'].append(gpu)
            except:
                pass
        except Exception as e:
            print(f"⚠️ GPU检测遇到问题: {e}")
        return gpu_info

    def check_ffmpeg_gpu_support(self):
        encoders = {'h264_nvenc': False, 'h264_amf': False, 'h264_qsv': False, 'hevc_nvenc': False, 'hevc_amf': False,
                    'hevc_qsv': False}
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5,
                                    encoding='utf-8', errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)  # 隐身符
            if result.returncode == 0:
                output = result.stdout.lower()
                for encoder in encoders.keys():
                    if encoder in output: encoders[encoder] = True
        except Exception as e:
            print(f"⚠️ FFmpeg编码器检测失败: {e}")
        return encoders

    def get_optimal_gpu_config(self, gpu_info, ffmpeg_encoders):
        config = {'use_gpu': False, 'encoder': 'libx264', 'hwaccel': None, 'gpu_type': None, 'gpu_devices': []}
        if gpu_info['nvidia'] and ffmpeg_encoders['h264_nvenc']:
            config.update({'use_gpu': True, 'encoder': 'h264_nvenc', 'hwaccel': 'cuda', 'gpu_type': 'NVIDIA',
                           'gpu_devices': gpu_info['nvidia_devices']})
        elif gpu_info['amd'] and ffmpeg_encoders['h264_amf']:
            config.update({'use_gpu': True, 'encoder': 'h264_amf', 'hwaccel': 'd3d11va', 'gpu_type': 'AMD',
                           'gpu_devices': gpu_info['amd_devices']})
        elif gpu_info['intel'] and ffmpeg_encoders['h264_qsv']:
            config.update({'use_gpu': True, 'encoder': 'h264_qsv', 'hwaccel': 'qsv', 'gpu_type': 'Intel',
                           'gpu_devices': gpu_info['intel_devices']})
        return config

    def print_detailed_gpu_info(self, gpu_info, ffmpeg_encoders, optimal_config):
        print("\n🖥️ 系统GPU详细信息:")
        print("-" * 50)
        if gpu_info['nvidia_devices']:
            print("🟢 NVIDIA GPU:")
            for device in gpu_info['nvidia_devices']: print(f"   - {device}")
        if gpu_info['amd_devices']:
            print("🔴 AMD GPU:")
            for device in gpu_info['amd_devices']: print(f"   - {device}")
        if gpu_info['intel_devices']:
            print("🔵 Intel GPU:")
            for device in gpu_info['intel_devices']: print(f"   - {device}")

        if optimal_config['use_gpu']:
            print(f"\n🚀 推荐配置: {optimal_config['gpu_type']} | 编码器: {optimal_config['encoder']}")

    def detect_gpu_acceleration(self):
        print("🔍 正在检测GPU加速配置...")
        gpu_info = self.detect_gpu_info()
        ffmpeg_encoders = self.check_ffmpeg_gpu_support()
        optimal_config = self.get_optimal_gpu_config(gpu_info, ffmpeg_encoders)
        self.print_detailed_gpu_info(gpu_info, ffmpeg_encoders, optimal_config)

        if optimal_config['use_gpu']:
            if optimal_config['gpu_type'] == 'NVIDIA':
                self.gpu_acceleration = 'cuda'
            elif optimal_config['gpu_type'] == 'AMD':
                self.gpu_acceleration = 'amd'
            elif optimal_config['gpu_type'] == 'Intel':
                self.gpu_acceleration = 'intel'
            print(f"✅ 检测到 {optimal_config['gpu_type']} GPU，启用硬件加速")
        else:
            self.gpu_acceleration = None
            print(f"⚠️ 未检测到可用的GPU加速，将使用CPU处理")
        self.gpu_config = optimal_config

    def get_gpu_codec_params(self):
        if self.gpu_acceleration == 'cuda':
            return {'codec': 'h264_nvenc', 'ffmpeg_params': ['-preset', 'fast', '-cq', '18', '-pix_fmt', 'yuv420p']}
        elif self.gpu_acceleration == 'amd':
            return {'codec': 'h264_amf',
                    'ffmpeg_params': ['-quality', 'balanced', '-b:v', '5M', '-maxrate', '8M', '-bufsize', '10M',
                                      '-pix_fmt', 'yuv420p']}
        elif self.gpu_acceleration == 'intel':
            return {'codec': 'h264_qsv', 'ffmpeg_params': ['-q:v', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p']}
        else:
            return {'codec': 'libx264', 'ffmpeg_params': ['-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p']}

    def get_video_files(self, folder_path):
        video_files = []
        folder = Path(folder_path)
        if not folder.exists(): return video_files
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                video_files.append(file_path)
        return video_files

    def create_output_folder(self, output_path):
        output_folder = Path(output_path)
        if not output_folder.exists():
            try:
                output_folder.mkdir(parents=True, exist_ok=True)
                return True
            except Exception as e:
                print(f"创建文件夹失败：{e}")
                return False
        return True

    def crop_video_region(self, input_path, output_path, x, y, width, height):
        try:
            cmd = ['ffmpeg', '-y', '-i', str(input_path), '-filter:v', f'crop={width}:{height}:{x}:{y}',
                   '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'aac', '-b:a', '128k', str(output_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8', errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)  # 隐身符
            return result.returncode == 0
        except Exception as e:
            print(f"视频裁剪异常: {e}")
            return False

    def trim_video(self, input_path, output_path, trim_start_seconds=0, trim_end_seconds=0, target_resolution=None,
                   crop_params=None, enable_time_trim=False):
        try:
            print(f"\n▶ 开始处理视频: {input_path.name}")
            file_suffix = input_path.suffix
            is_uppercase_format = file_suffix.isupper()
            has_crop = bool(crop_params)
            has_time_trim = enable_time_trim and (trim_start_seconds > 0 or trim_end_seconds > 0)
            has_resolution = target_resolution and target_resolution != "原始分辨率"

            name_parts = []
            if has_crop: name_parts.append("cropped")
            if has_time_trim: name_parts.append("trimmed")
            if has_resolution: name_parts.append("resized")
            output_file = Path(output_path) / f"{'_'.join(name_parts) if name_parts else 'processed'}_{input_path.name}"

            if has_crop:
                if self._ffmpeg_combined_process(input_path, output_file, crop_params, trim_start_seconds,
                                                 trim_end_seconds, target_resolution, has_time_trim):
                    print(f"✓ 处理成功: {output_file.name}")
                    return True
                return False
            elif is_uppercase_format:
                success = self._ffmpeg_uppercase_process(input_path, output_file, trim_start_seconds, trim_end_seconds,
                                                         target_resolution, enable_time_trim)
                if success: print(f"✓ FFmpeg处理成功: {output_file.name}")
                return success
            elif has_time_trim or has_resolution:
                success = self._moviepy_process(input_path, output_file, trim_start_seconds, trim_end_seconds,
                                                target_resolution, has_time_trim)
                if success: print(f"✓ MoviePy处理成功: {output_file.name}")
                return success
            else:
                shutil.copy2(input_path, output_file)
                print(f"✓ 文件复制完成: {output_file.name}")
                return True
        except Exception as e:
            print(f"✗ 处理视频 '{input_path.name}' 时出错：{e}")
            return False

    def _ffmpeg_uppercase_process(self, input_path, output_file, trim_start, trim_end, target_resolution,
                                  enable_time_trim):
        # 简化处理逻辑，避免冗长
        try:
            cmd = ['ffmpeg', '-y', '-i', str(input_path)]
            if enable_time_trim:
                if trim_start > 0: cmd.extend(['-ss', str(trim_start)])
                if trim_end > 0:
                    duration = self._get_video_duration(input_path)
                    if duration and (duration - trim_end > trim_start):
                        cmd.extend(['-t', str(duration - trim_end - trim_start)])

            if target_resolution and target_resolution != "原始分辨率":
                res_map = {"1920x1080": (1920, 1080), "1280x720": (1280, 720), "854x480": (854, 480),
                           "640x360": (640, 360), "426x240": (426, 240)}
                w, h = res_map.get(target_resolution, (None, None))
                if w and h: cmd.extend(['-vf', f'scale={w}:{h}'])

            cmd.extend(
                ['-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a',
                 '128k', '-avoid_negative_ts', 'make_zero', '-fflags', '+genpts'])
            output_path = Path(output_file)
            final_cmd = cmd + ['-f', 'mp4', '-movflags', '+faststart', str(output_path.with_suffix('.mp4'))]
            result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=600, encoding='utf-8',
                                    errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)  # 隐身符
            return result.returncode == 0
        except Exception:
            return False

    def _ffmpeg_combined_process(self, input_path, output_file, crop_params, trim_start, trim_end, target_resolution,
                                 enable_time_trim):
        try:
            cmd = ['ffmpeg', '-y', '-i', str(input_path)]
            filters = []
            if crop_params:
                filters.append(
                    f"crop={crop_params['width']}:{crop_params['height']}:{crop_params['x']}:{crop_params['y']}")

            if target_resolution and target_resolution != "原始分辨率":
                res_map = {"1920x1080": (1920, 1080), "1280x720": (1280, 720), "854x480": (854, 480),
                           "640x360": (640, 360), "426x240": (426, 240)}
                w, h = res_map.get(target_resolution, (None, None))
                if w and h: filters.append(f"scale={w}:{h}")

            if filters: cmd.extend(['-vf', ','.join(filters)])

            if enable_time_trim:
                if trim_start > 0: cmd.extend(['-ss', str(trim_start)])
                if trim_end > 0:
                    duration = self._get_video_duration(input_path)
                    if duration and (duration - trim_end > trim_start):
                        cmd.extend(['-t', str(duration - trim_end - trim_start)])

            cmd.extend(
                ['-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'aac', '-b:a', '128k', str(output_file)])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, encoding='utf-8', errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)  # 隐身符
            return result.returncode == 0
        except Exception:
            return False

    def _moviepy_process(self, input_path, output_file, trim_start, trim_end, target_resolution, enable_time_trim):
        if input_path.suffix.lower() == '.mov':
            return self._ffmpeg_uppercase_process(input_path, output_file, trim_start, trim_end, target_resolution,
                                                  enable_time_trim)

        video = current_video = None
        try:
            video = VideoFileClip(str(input_path))
            original_fps, original_duration = video.fps, video.duration
            current_video = video

            if enable_time_trim:
                start_time = trim_start if trim_start > 0 else 0
                end_time = original_duration - trim_end if trim_end > 0 else original_duration
                if start_time < original_duration and end_time > start_time:
                    current_video = video.subclip(start_time, end_time)

            if target_resolution and target_resolution != "原始分辨率":
                res_map = {"1920x1080": (1920, 1080), "1280x720": (1280, 720), "854x480": (854, 480),
                           "640x360": (640, 360), "426x240": (426, 240)}
                new_size = res_map.get(target_resolution, None)
                if new_size:
                    resized_video = current_video.resize(new_size)
                    if current_video != video: current_video.close()
                    current_video = resized_video

            codec_params = self.get_gpu_codec_params()
            write_params = {
                'codec': codec_params['codec'], 'audio_codec': 'aac', 'temp_audiofile': 'temp-audio.m4a',
                'remove_temp': True, 'verbose': False, 'logger': None, 'ffmpeg_params': codec_params['ffmpeg_params'],
                'fps': original_fps,
            }
            return self._write_video_with_fallback(current_video, output_file, write_params, original_fps, False)
        except Exception as e:
            print(f"MoviePy处理失败: {e}")
            return False
        finally:
            try:
                if current_video and current_video != video: current_video.close()
                if video: video.close()
            except:
                pass

    def _write_video_with_fallback(self, video, output_file, write_params, original_fps, is_mov_format=False):
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            video.write_videofile(str(output_file), **write_params)
            return True
        except Exception as e:
            print(f"✗ 编码失败，尝试基础CPU降级编码: {e}")
            try:
                video.write_videofile(str(output_file), codec='libx264', audio_codec='aac', threads=1, preset='fast')
                return True
            except Exception as e2:
                print(f"✗ 降级编码也失败了: {e2}")
                return False

    def _get_video_duration(self, video_path):
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(video_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)  # 隐身符
            return float(result.stdout.strip()) if result.returncode == 0 else None
        except:
            return None

    def batch_trim_videos(self, input_folder, output_folder, trim_start_seconds=0, trim_end_seconds=0,
                          target_resolution=None, progress_callback=None, use_multithreading=True, crop_params=None,
                          enable_time_trim=False):
        self.stop_processing = False
        video_files = self.get_video_files(input_folder)
        if not video_files:
            print("在指定文件夹中未找到支持的视频文件")
            return

        print(f"共找到 {len(video_files)} 个视频文件准备处理。")
        if not self.create_output_folder(output_folder): return

        if use_multithreading and len(video_files) > 1 and (not self.gpu_acceleration or crop_params):
            self._process_with_multithreading(video_files, output_folder, trim_start_seconds, trim_end_seconds,
                                              target_resolution, progress_callback, crop_params, enable_time_trim)
        else:
            self._process_sequentially(video_files, output_folder, trim_start_seconds, trim_end_seconds,
                                       target_resolution, progress_callback, crop_params, enable_time_trim)

    def _process_sequentially(self, video_files, output_folder, trim_start_seconds, trim_end_seconds, target_resolution,
                              progress_callback, crop_params=None, enable_time_trim=False):
        success_count = failed_count = 0
        for i, video_file in enumerate(video_files, 1):
            if self.stop_processing: break
            if progress_callback: progress_callback(i, len(video_files), video_file.name)
            if self.trim_video(video_file, output_folder, trim_start_seconds, trim_end_seconds, target_resolution,
                               crop_params, enable_time_trim):
                success_count += 1
            else:
                failed_count += 1
        print(f"\n处理完成！成功：{success_count} 个，失败：{failed_count} 个")

    def _process_with_multithreading(self, video_files, output_folder, trim_start_seconds, trim_end_seconds,
                                     target_resolution, progress_callback, crop_params=None, enable_time_trim=False):
        success_count = failed_count = completed_count = 0

        def process_single(vf):
            if self.stop_processing: return False
            return self.trim_video(vf, output_folder, trim_start_seconds, trim_end_seconds, target_resolution,
                                   crop_params, enable_time_trim)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_video = {executor.submit(process_single, vf): vf for vf in video_files}
            for future in concurrent.futures.as_completed(future_to_video):
                if self.stop_processing: break
                vf = future_to_video[future]
                completed_count += 1
                try:
                    if future.result():
                        success_count += 1
                    else:
                        failed_count += 1
                except:
                    failed_count += 1
                if progress_callback: progress_callback(completed_count, len(video_files), vf.name)
        print(f"\n多线程处理完成！成功：{success_count} 个，失败：{failed_count} 个")

    def stop_processing_task(self):
        self.stop_processing = True
        print("正在停止处理...")


class VideoTrimmerGUI:
    def __init__(self):
        self.trimmer = VideoTrimmer()
        self.root = tk.Tk()
        self.root.title("视频批量裁剪引擎 (Pro 版)")
        self.root.geometry("750x780")
        self.root.minsize(700, 750)

        # UI 样式初始化
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # 数据绑定
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.trim_start_seconds = tk.StringVar(value="")
        self.trim_end_seconds = tk.StringVar(value="")
        self.target_resolution = tk.StringVar(value="原始分辨率")
        self.custom_width = tk.StringVar(value="1920")
        self.custom_height = tk.StringVar(value="1080")
        self.use_multithreading = tk.BooleanVar(value=True)
        self.thread_count = tk.StringVar(value=str(self.trimmer.max_workers))
        self.is_processing = False
        self.enable_crop = tk.BooleanVar(value=False)
        self.crop_x = tk.StringVar(value="0")
        self.crop_y = tk.StringVar(value="0")
        self.crop_width = tk.StringVar(value="1920")
        self.crop_height = tk.StringVar(value="1080")
        self.enable_time_trim = tk.BooleanVar(value=False)

        # 核心：将 stdout 输出重定向到队列，实现黑客终端视觉效果且不卡界面
        self.log_queue = queue.Queue()
        sys.stdout = PrintRedirector(self.log_queue)
        sys.stderr = PrintRedirector(self.log_queue)

        self.setup_ui()
        self.start_log_listener()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 路径设置
        path_frame = ttk.LabelFrame(main_frame, text=" 📁 文件路径配置 ", padding=10)
        path_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(path_frame, text="输入目录:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(path_frame, textvariable=self.input_folder, width=55, state="readonly").grid(row=0, column=1, padx=10,
                                                                                               sticky="ew")
        ttk.Button(path_frame, text="选择...", command=self.select_input_folder).grid(row=0, column=2)

        ttk.Label(path_frame, text="输出目录:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(path_frame, textvariable=self.output_folder, width=55).grid(row=1, column=1, padx=10, sticky="ew")
        ttk.Button(path_frame, text="选择...", command=self.select_output_folder).grid(row=1, column=2)
        path_frame.columnconfigure(1, weight=1)

        # 2. 裁剪参数设置
        opt_frame = ttk.LabelFrame(main_frame, text=" ✂️ 裁剪与分辨率设置 ", padding=10)
        opt_frame.pack(fill=tk.X, pady=(0, 10))

        # 时间裁剪
        time_frame = ttk.Frame(opt_frame)
        time_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(time_frame, text="启用时间裁剪", variable=self.enable_time_trim,
                        command=self.on_time_trim_toggle).pack(side=tk.LEFT)
        self.time_trim_frame = ttk.Frame(opt_frame)
        ttk.Label(self.time_trim_frame, text="裁剪片头(秒):").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(self.time_trim_frame, textvariable=self.trim_start_seconds, width=8).pack(side=tk.LEFT)
        ttk.Label(self.time_trim_frame, text="裁剪片尾(秒):").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(self.time_trim_frame, textvariable=self.trim_end_seconds, width=8).pack(side=tk.LEFT)

        # 画面裁剪
        crop_wrapper = ttk.Frame(opt_frame)
        crop_wrapper.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(crop_wrapper, text="启用画面区域裁剪", variable=self.enable_crop,
                        command=self.on_crop_toggle).pack(side=tk.LEFT)
        self.crop_params_frame = ttk.Frame(opt_frame)
        ttk.Label(self.crop_params_frame, text="X:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(self.crop_params_frame, textvariable=self.crop_x, width=6).pack(side=tk.LEFT)
        ttk.Label(self.crop_params_frame, text="Y:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(self.crop_params_frame, textvariable=self.crop_y, width=6).pack(side=tk.LEFT)
        ttk.Label(self.crop_params_frame, text="保留宽:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(self.crop_params_frame, textvariable=self.crop_width, width=6).pack(side=tk.LEFT)
        ttk.Label(self.crop_params_frame, text="保留高:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(self.crop_params_frame, textvariable=self.crop_height, width=6).pack(side=tk.LEFT)

        # 分辨率
        res_frame = ttk.Frame(opt_frame)
        res_frame.pack(fill=tk.X, pady=5)
        ttk.Label(res_frame, text="输出分辨率:").pack(side=tk.LEFT)
        res_options = ["原始分辨率", "1920x1080", "1280x720", "854x480", "640x360", "426x240", "自定义"]
        res_combo = ttk.Combobox(res_frame, textvariable=self.target_resolution, values=res_options, state="readonly",
                                 width=15)
        res_combo.pack(side=tk.LEFT, padx=(10, 5))
        res_combo.bind("<<ComboboxSelected>>", self.on_resolution_change)

        self.custom_frame = ttk.Frame(res_frame)
        ttk.Label(self.custom_frame, text="宽:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(self.custom_frame, textvariable=self.custom_width, width=6).pack(side=tk.LEFT)
        ttk.Label(self.custom_frame, text="高:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(self.custom_frame, textvariable=self.custom_height, width=6).pack(side=tk.LEFT)

        # 3. 硬件加速与性能
        hw_frame = ttk.LabelFrame(main_frame, text=" ⚙️ 硬件与性能 ", padding=10)
        hw_frame.pack(fill=tk.X, pady=(0, 10))

        gpu_status = f"可用 ({self.trimmer.gpu_acceleration.upper()})" if self.trimmer.gpu_acceleration else "不可用 (回退 CPU)"
        tk.Label(hw_frame, text=f"GPU加速状态: {gpu_status}",
                 fg="#4CAF50" if self.trimmer.gpu_acceleration else "#FF5722",
                 font=("Microsoft YaHei", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))

        th_frame = ttk.Frame(hw_frame)
        th_frame.pack(fill=tk.X)
        ttk.Checkbutton(th_frame, text="启用多线程并发加速", variable=self.use_multithreading,
                        command=self.on_multithreading_change).pack(side=tk.LEFT)
        ttk.Label(th_frame, text="分配线程数:").pack(side=tk.LEFT, padx=(20, 5))
        self.thread_spinbox = tk.Spinbox(th_frame, textvariable=self.thread_count, from_=1,
                                         to=multiprocessing.cpu_count(), width=5)
        self.thread_spinbox.pack(side=tk.LEFT)

        if self.trimmer.gpu_acceleration:
            self.use_multithreading.set(False)
            self.thread_spinbox.config(state="disabled")

        # 4. 控制按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        self.start_button = tk.Button(btn_frame, text="▶ 开始批量裁剪", command=self.start_processing, bg="#4CAF50",
                                      fg="white", font=("Microsoft YaHei", 11, "bold"), relief="flat", cursor="hand2",
                                      width=15)
        self.start_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=3)

        self.stop_button = tk.Button(btn_frame, text="■ 停止任务", command=self.stop_processing, bg="#f44336",
                                     fg="white", font=("Microsoft YaHei", 11, "bold"), relief="flat", cursor="hand2",
                                     state="disabled", width=15)
        self.stop_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=3)

        # 5. 黑客日志终端
        self.progress_label = tk.Label(main_frame, text=">> 系统就绪。等待执行命令...", fg="#2196F3",
                                       font=("Microsoft YaHei", 9, "bold"))
        self.progress_label.pack(anchor=tk.W, pady=5)

        log_frame = ttk.LabelFrame(main_frame, text=" 💻 终端日志 (Terminal) ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # 核心黑客视觉特效
        self.log_text = tk.Text(log_frame, bg="#1e1e1e", fg="#cccccc", insertbackground="white",
                                font=("Consolas", 9), bd=0, padx=10, pady=10, wrap="word", highlightthickness=0)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        print(f"初始化成功... OS: {platform.system()} | 逻辑核: {multiprocessing.cpu_count()}")

    def start_log_listener(self):
        """线程安全的日志刷新器"""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg)
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.start_log_listener)

    def on_time_trim_toggle(self):
        if self.enable_time_trim.get():
            self.time_trim_frame.pack(fill=tk.X, pady=5, after=self.time_trim_frame.master.winfo_children()[0])
        else:
            self.time_trim_frame.pack_forget()

    def on_crop_toggle(self):
        if self.enable_crop.get():
            self.crop_params_frame.pack(fill=tk.X, pady=5, after=self.crop_params_frame.master.winfo_children()[0])
        else:
            self.crop_params_frame.pack_forget()

    def on_resolution_change(self, event=None):
        if self.target_resolution.get() == "自定义":
            self.custom_frame.pack(side=tk.LEFT)
        else:
            self.custom_frame.pack_forget()

    def on_multithreading_change(self):
        self.thread_spinbox.config(state="normal" if self.use_multithreading.get() else "disabled")

    def select_input_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_folder.set(folder)
            print(f"[*] 输入目录已挂载: {folder}")
            import datetime
            out_path = Path(
                folder).parent / f"{Path(folder).name}_trimmed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.output_folder.set(str(out_path))

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
            print(f"[*] 输出目录已指向: {folder}")

    def stop_processing(self):
        if self.is_processing:
            self.trimmer.stop_processing_task()
            print("[!] 用户中断指令已发送，正在安全终止进程...")

    def update_progress(self, current, total, filename):
        self.progress_label.config(text=f">> 进度: [{current}/{total}] | 当前目标: {filename}")

    def start_processing(self):
        if not self.input_folder.get() or not self.output_folder.get():
            messagebox.showerror("异常", "未指定输入或输出目录！")
            return

        trim_start = float(self.trim_start_seconds.get() or 0)
        trim_end = float(self.trim_end_seconds.get() or 0)
        target_resolution = self.target_resolution.get()
        if target_resolution == "自定义":
            target_resolution = f"{self.custom_width.get()}x{self.custom_height.get()}"

        crop_params = None
        if self.enable_crop.get():
            crop_params = {'x': int(self.crop_x.get()), 'y': int(self.crop_y.get()),
                           'width': int(self.crop_width.get()), 'height': int(self.crop_height.get())}

        if self.use_multithreading.get(): self.trimmer.max_workers = int(self.thread_count.get())

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.is_processing = True
        self.log_text.delete(1.0, tk.END)

        def process_thread():
            try:
                self.trimmer.batch_trim_videos(
                    self.input_folder.get(), self.output_folder.get(), trim_start, trim_end,
                    target_resolution, self.update_progress, self.use_multithreading.get(),
                    crop_params, self.enable_time_trim.get()
                )
                if not self.trimmer.stop_processing:
                    self.progress_label.config(text=">> 任务完全结束。")
                    messagebox.showinfo("完成", "所有视频处理完毕！")
                else:
                    self.progress_label.config(text=">> 任务已被安全终止。")
            except Exception as e:
                print(f"[ERROR] 发生致命错误: {e}")
                messagebox.showerror("错误", f"发生异常: {e}")
            finally:
                self.start_button.config(state="normal")
                self.stop_button.config(state="disabled")
                self.is_processing = False

        threading.Thread(target=process_thread, daemon=True).start()

    def run(self):
        self.root.mainloop()


def main():
    # 删除原先的 input() 和 CLI 代码，直接安全呼出 GUI
    app = VideoTrimmerGUI()
    app.run()


if __name__ == "__main__":
    # 多进程安全锁，必须在 Windows 第一行
    multiprocessing.freeze_support()

    # 启用高清 DPI 感知（拒绝模糊）
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    main()