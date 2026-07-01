#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频批量裁剪工具 (PySide6 Pro 增强无闪烁版)
功能：批量裁剪视频、调整分辨率、GPU加速崩溃自动降级、拖拽路径、进程级秒杀、高DPI支持
"""

import os
import sys
import time
import platform
import shutil
import threading
import subprocess
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from pathlib import Path
from moviepy.editor import VideoFileClip

# PySide6 导入
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QCheckBox, QComboBox, QSpinBox, QGroupBox,
                               QTextEdit, QFileDialog, QMessageBox, QGridLayout)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QTextCursor

# Windows 专属隐身符，用于完全隐藏 subprocess 调用的闪烁黑框
CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0


# --- 安全数值转换器 (防止输入框留空导致崩溃) ---
def safe_int(text, default=0):
    try:
        return int(str(text).strip())
    except (ValueError, TypeError):
        return default


def safe_float(text, default=0.0):
    try:
        return float(str(text).strip())
    except (ValueError, TypeError):
        return default


class EmittingStream(QObject):
    """标准输出重定向器，通过 Qt 信号安全推送到 GUI 的文本框"""
    textWritten = Signal(str)

    def write(self, text):
        if text:
            self.textWritten.emit(str(text))

    def flush(self):
        pass


class DragLineEdit(QLineEdit):
    """支持拖拽文件/文件夹自动获取路径的输入框"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.setText(path)
            event.acceptProposedAction()


class VideoTrimmer:
    def __init__(self):
        self.supported_formats = {'.mp4', '.MP4', '.avi', '.AVI', '.mov', '.MOV',
                                  '.mkv', '.MKV', '.wmv', '.WMV', '.flv', '.FLV',
                                  '.webm', '.WEBM', '.m4v', '.M4V'}

        self.stop_processing = False
        self.gpu_acceleration = None
        self.max_workers = min(4, multiprocessing.cpu_count())

        self.process_lock = threading.Lock()
        self.active_processes = []

        self.detect_gpu_acceleration()

    def _run_ffmpeg_cmd(self, cmd):
        """核心：Popen 托管，实时读取解决死锁，支持 PID 强杀"""
        error_logs = []
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding='utf-8', errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)
            with self.process_lock:
                self.active_processes.append(proc)

            for line in proc.stdout:
                if self.stop_processing:
                    break
                print(line, end="")
                error_logs.append(line.strip())
                if len(error_logs) > 15:
                    error_logs.pop(0)

            proc.wait()

            with self.process_lock:
                if proc in self.active_processes:
                    self.active_processes.remove(proc)

            if self.stop_processing:
                return False

            if proc.returncode != 0:
                print(f"❌ FFmpeg 底层崩溃! 退出码: {proc.returncode}，最后日志:\n" + "\n".join(error_logs[-5:]))
                return False

            return True
        except Exception as e:
            print(f"FFmpeg 子进程执行异常: {e}")
            return False

    def stop_processing_task(self):
        self.stop_processing = True
        print("\n[!] 接收到中断指令，正在向底层下发 taskkill /PID 秒杀进程...")
        with self.process_lock:
            for proc in self.active_processes:
                try:
                    if platform.system() == "Windows":
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                       creationflags=CREATE_NO_WINDOW)
                    else:
                        proc.kill()
                except:
                    pass
            self.active_processes.clear()

    def detect_gpu_acceleration(self):
        self.gpu_acceleration = None
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5,
                                    encoding='utf-8', errors='ignore', creationflags=CREATE_NO_WINDOW)
            if result.returncode == 0:
                output = result.stdout.lower()
                if 'h264_nvenc' in output:
                    self.gpu_acceleration = 'cuda'
                elif 'h264_amf' in output:
                    self.gpu_acceleration = 'amd'
                elif 'h264_qsv' in output:
                    self.gpu_acceleration = 'intel'
        except:
            pass

    def get_gpu_codec_params(self):
        if self.gpu_acceleration == 'cuda':
            return {'codec': 'h264_nvenc',
                    'ffmpeg_params': ['-preset', 'p4', '-profile:v', 'high', '-rc', 'vbr', '-cq', '20', '-pix_fmt',
                                      'yuv420p']}
        elif self.gpu_acceleration == 'amd':
            return {'codec': 'h264_amf', 'ffmpeg_params': ['-quality', 'balanced', '-b:v', '5M', '-pix_fmt', 'yuv420p']}
        elif self.gpu_acceleration == 'intel':
            return {'codec': 'h264_qsv', 'ffmpeg_params': ['-q:v', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p']}
        return {'codec': 'libx264', 'ffmpeg_params': ['-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p']}

    def parse_resolution(self, resolution_str):
        if not resolution_str or resolution_str == "原始分辨率":
            return None, None
        try:
            parts = resolution_str.lower().split('x')
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        except Exception:
            pass
        return None, None

    def _get_video_duration(self, video_path):
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(video_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore',
                                    creationflags=CREATE_NO_WINDOW)
            return float(result.stdout.strip()) if result.returncode == 0 else None
        except:
            return None

    def trim_video(self, input_path, output_path, trim_start=0, trim_end=0, target_resolution=None, crop_params=None,
                   enable_time_trim=False):
        try:
            if self.stop_processing: return False
            print(f"\n▶ 开始处理视频: {input_path.name}")

            has_crop = bool(crop_params)
            has_time = enable_time_trim and (trim_start > 0 or trim_end > 0)
            has_res = target_resolution and target_resolution != "原始分辨率"

            name_parts = []
            if has_crop: name_parts.append("cropped")
            if has_time: name_parts.append("trimmed")
            if has_res: name_parts.append("resized")
            output_file = Path(output_path) / f"{'_'.join(name_parts) if name_parts else 'processed'}_{input_path.name}"

            # 🌟 [关键修复1]：分步策略。如果同时启用裁剪和调分辨率，强制两阶段处理
            if has_crop and has_res:
                print(f"=> [执行策略] 触发复合要求，拆分为两阶段处理...")
                temp_file = output_file.with_name(f"temp_step1_{output_file.name}")

                print("   -> 阶段一：仅执行画面裁剪与时长截取...")
                success1 = self._ffmpeg_combined_process(input_path, temp_file, crop_params, trim_start, trim_end, None,
                                                         has_time)

                if not success1 or self.stop_processing:
                    if temp_file.exists(): temp_file.unlink()
                    return False

                print("   -> 阶段二：仅修改视频分辨率...")
                success2 = self._ffmpeg_combined_process(temp_file, output_file, None, 0, 0, target_resolution, False)

                # 扫尾：删除临时文件
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass

                success = success2

            elif has_crop or input_path.suffix.isupper():
                success = self._ffmpeg_combined_process(input_path, output_file, crop_params, trim_start, trim_end,
                                                        target_resolution, has_time)
            elif has_time or has_res:
                success = self._moviepy_process(input_path, output_file, trim_start, trim_end, target_resolution,
                                                has_time)
            else:
                shutil.copy2(input_path, output_file)
                success = True

            if success:
                print(f"✓ 视频打包成功: {output_file.name}")
            return success
        except Exception as e:
            print(f"✗ 致命异常 '{input_path.name}': {e}")
            return False

    def _ffmpeg_combined_process(self, input_path, output_file, crop_params, trim_start, trim_end, target_resolution,
                                 enable_time_trim):
        def build_cmd(force_cpu=False):
            cmd = ['ffmpeg', '-y', '-i', str(input_path)]
            filters = []

            if crop_params:
                cw, ch = crop_params['width'], crop_params['height']
                cx, cy = crop_params['x'], crop_params['y']
                cw, ch = cw - (cw % 2), ch - (ch % 2)  # 强制变为偶数
                filters.append(f"crop={cw}:{ch}:{cx}:{cy}")

            w, h = self.parse_resolution(target_resolution)
            if w and h:
                w, h = w - (w % 2), h - (h % 2)
                filters.append(f"scale={w}:{h},setsar=1:1")  # 强制重置SAR，防止拉伸报错

            if filters:
                cmd.extend(['-vf', ','.join(filters)])

            if enable_time_trim:
                if trim_start > 0: cmd.extend(['-ss', str(trim_start)])
                if trim_end > 0:
                    duration = self._get_video_duration(input_path)
                    if duration and (duration - trim_end > trim_start):
                        cmd.extend(['-t', str(duration - trim_end - trim_start)])

            # 🌟 [关键修复2]：支持强制 CPU 退避
            if force_cpu or not self.gpu_acceleration:
                cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p'])
            else:
                codec_data = self.get_gpu_codec_params()
                cmd.extend(['-c:v', codec_data['codec']])
                cmd.extend(codec_data['ffmpeg_params'])

            cmd.extend(['-c:a', 'aac', '-b:a', '128k', str(output_file)])
            return cmd

        # 第一次尝试 (可能带有硬件加速)
        cmd = build_cmd(force_cpu=False)
        success = self._run_ffmpeg_cmd(cmd)

        # 如果因为 nvcuda.dll 等硬件原因崩溃，瞬间切回 CPU 重跑
        if not success and not self.stop_processing and self.gpu_acceleration:
            print(
                "\n⚠️ [异常捕获] 探测到 GPU 硬件加速崩溃(驱动缺失或显存溢出)！\n🔄 正在自动降级为纯 CPU 模式重新执行...")
            cmd_cpu = build_cmd(force_cpu=True)
            success = self._run_ffmpeg_cmd(cmd_cpu)

        return success

    def _moviepy_process(self, input_path, output_file, trim_start, trim_end, target_resolution, enable_time_trim):
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

            w, h = self.parse_resolution(target_resolution)
            if w and h:
                w, h = w - (w % 2), h - (h % 2)
                resized_video = current_video.resize((w, h))
                if current_video != video: current_video.close()
                current_video = resized_video

            write_params = {
                'codec': 'libx264', 'audio_codec': 'aac', 'temp_audiofile': 'temp-audio.m4a',
                'remove_temp': True, 'verbose': False, 'logger': None,
                'ffmpeg_params': ['-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p'],
                'fps': original_fps,
            }
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if self.stop_processing: return False
            current_video.write_videofile(str(output_file), **write_params)
            return True
        except Exception as e:
            print(f"MoviePy处理失败: {e}")
            return False
        finally:
            try:
                if current_video and current_video != video: current_video.close()
                if video: video.close()
            except:
                pass

    def batch_trim_videos(self, input_folder, output_folder, trim_start=0, trim_end=0,
                          target_resolution=None, progress_callback=None, use_multithreading=True,
                          crop_params=None, enable_time_trim=False):
        self.stop_processing = False
        folder = Path(input_folder)
        video_files = [p for p in folder.iterdir() if p.is_file() and p.suffix in self.supported_formats]

        if not video_files:
            print("在指定文件夹中未找到支持的视频文件")
            return

        print(f"共找到 {len(video_files)} 个视频文件准备处理。")
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        success_count = failed_count = completed_count = 0

        def process_single(vf):
            if self.stop_processing: return False
            return self.trim_video(vf, output_folder, trim_start, trim_end, target_resolution, crop_params,
                                   enable_time_trim)

        if use_multithreading and len(video_files) > 1 and (not self.gpu_acceleration or crop_params):
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
                    except Exception as e:
                        failed_count += 1
                    if progress_callback: progress_callback(completed_count, len(video_files), vf.name)
        else:
            for i, video_file in enumerate(video_files, 1):
                if self.stop_processing: break
                if process_single(video_file):
                    success_count += 1
                else:
                    failed_count += 1
                if progress_callback: progress_callback(i, len(video_files), video_file.name)

        if not self.stop_processing:
            print(f"\n批量处理完成！成功：{success_count}，失败：{failed_count}")


class VideoTrimmerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.trimmer = VideoTrimmer()
        self.is_processing = False

        self.setWindowTitle("视频批量裁剪引擎 (PySide6 Pro 版)")
        self.resize(800, 850)

        self.setup_ui()
        self.setup_logging()

    def setup_logging(self):
        self.emitter = EmittingStream()
        self.emitter.textWritten.connect(self.append_log)
        sys.stdout = self.emitter
        sys.stderr = self.emitter

    def append_log(self, text):
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertPlainText(text)
        self.log_text.moveCursor(QTextCursor.End)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        path_group = QGroupBox(" 📁 文件路径配置 (支持将文件/文件夹拖拽入输入框内) ")
        path_layout = QGridLayout(path_group)

        path_layout.addWidget(QLabel("输入目录:"), 0, 0)
        self.input_edit = DragLineEdit()
        self.input_edit.setPlaceholderText("选择或拖拽输入路径...")
        path_layout.addWidget(self.input_edit, 0, 1)
        btn_in = QPushButton("选择...")
        btn_in.clicked.connect(self.select_input_folder)
        path_layout.addWidget(btn_in, 0, 2)

        path_layout.addWidget(QLabel("输出目录:"), 1, 0)
        self.output_edit = DragLineEdit()
        path_layout.addWidget(self.output_edit, 1, 1)
        btn_out = QPushButton("选择...")
        btn_out.clicked.connect(self.select_output_folder)
        path_layout.addWidget(btn_out, 1, 2)

        main_layout.addWidget(path_group)

        opt_group = QGroupBox(" ✂️ 裁剪与分辨率设置 ")
        opt_layout = QVBoxLayout(opt_group)

        time_layout = QHBoxLayout()
        self.chk_time_trim = QCheckBox("启用时间裁剪")
        self.chk_time_trim.toggled.connect(self.on_time_trim_toggle)
        time_layout.addWidget(self.chk_time_trim)

        self.time_widget = QWidget()
        tw_layout = QHBoxLayout(self.time_widget)
        tw_layout.setContentsMargins(0, 0, 0, 0)
        tw_layout.addWidget(QLabel("裁剪片头(秒):"))
        self.spin_trim_start = QLineEdit("0")
        tw_layout.addWidget(self.spin_trim_start)
        tw_layout.addWidget(QLabel("裁剪片尾(秒):"))
        self.spin_trim_end = QLineEdit("0")
        tw_layout.addWidget(self.spin_trim_end)
        time_layout.addWidget(self.time_widget)
        time_layout.addStretch()
        opt_layout.addLayout(time_layout)
        self.time_widget.setVisible(False)

        crop_layout = QHBoxLayout()
        self.chk_crop = QCheckBox("启用画面区域裁剪")
        self.chk_crop.toggled.connect(self.on_crop_toggle)
        crop_layout.addWidget(self.chk_crop)

        self.crop_widget = QWidget()
        cw_layout = QHBoxLayout(self.crop_widget)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.addWidget(QLabel("X:"))
        self.crop_x = QLineEdit("0")
        cw_layout.addWidget(self.crop_x)
        cw_layout.addWidget(QLabel("Y:"))
        self.crop_y = QLineEdit("0")
        cw_layout.addWidget(self.crop_y)
        cw_layout.addWidget(QLabel("宽:"))
        self.crop_w = QLineEdit("1040")
        cw_layout.addWidget(self.crop_w)
        cw_layout.addWidget(QLabel("高:"))
        self.crop_h = QLineEdit("1920")
        cw_layout.addWidget(self.crop_h)
        crop_layout.addWidget(self.crop_widget)
        crop_layout.addStretch()
        opt_layout.addLayout(crop_layout)
        self.crop_widget.setVisible(False)

        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("输出分辨率:"))
        self.combo_res = QComboBox()
        self.combo_res.addItems(["原始分辨率", "1920x1080", "1080x1920", "1280x720", "854x480", "自定义"])
        self.combo_res.currentTextChanged.connect(self.on_res_change)
        res_layout.addWidget(self.combo_res)

        self.custom_res_widget = QWidget()
        cr_layout = QHBoxLayout(self.custom_res_widget)
        cr_layout.setContentsMargins(0, 0, 0, 0)
        cr_layout.addWidget(QLabel("宽:"))
        self.custom_w = QLineEdit("1080")
        cr_layout.addWidget(self.custom_w)
        cr_layout.addWidget(QLabel("高:"))
        self.custom_h = QLineEdit("1920")
        cr_layout.addWidget(self.custom_h)
        res_layout.addWidget(self.custom_res_widget)
        res_layout.addStretch()
        opt_layout.addLayout(res_layout)
        self.custom_res_widget.setVisible(False)

        main_layout.addWidget(opt_group)

        hw_group = QGroupBox(" ⚙️ 硬件与性能 ")
        hw_layout = QVBoxLayout(hw_group)

        gpu_status = f"可用 ({self.trimmer.gpu_acceleration.upper()})" if self.trimmer.gpu_acceleration else "不可用 (已回退 CPU)"
        lbl_gpu = QLabel(f"探索到GPU指令集: {gpu_status} (若运行崩溃将自动降级)")
        lbl_gpu.setStyleSheet(
            "color: #4CAF50; font-weight: bold;" if self.trimmer.gpu_acceleration else "color: #FF5722; font-weight: bold;")
        hw_layout.addWidget(lbl_gpu)

        th_layout = QHBoxLayout()
        self.chk_multi = QCheckBox("启用多线程并发加速")
        self.chk_multi.setChecked(True)
        self.chk_multi.toggled.connect(self.on_multi_toggle)
        th_layout.addWidget(self.chk_multi)

        th_layout.addWidget(QLabel("分配线程数:"))
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, multiprocessing.cpu_count())
        self.spin_threads.setValue(self.trimmer.max_workers)
        th_layout.addWidget(self.spin_threads)
        th_layout.addStretch()
        hw_layout.addLayout(th_layout)

        if self.trimmer.gpu_acceleration:
            self.chk_multi.setChecked(False)
            self.spin_threads.setEnabled(False)

        main_layout.addWidget(hw_group)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ 开始批量裁剪")
        self.btn_start.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_processing)

        self.btn_stop = QPushButton("■ 停止任务")
        self.btn_stop.setStyleSheet(
            "background-color: #f44336; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_processing)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        main_layout.addLayout(btn_layout)

        self.lbl_progress = QLabel(">> 系统就绪。等待执行命令...")
        self.lbl_progress.setStyleSheet("color: #2196F3; font-weight: bold;")
        main_layout.addWidget(self.lbl_progress)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #cccccc; font-family: Consolas, Courier New;")
        main_layout.addWidget(self.log_text)

    def on_time_trim_toggle(self, checked):
        self.time_widget.setVisible(checked)

    def on_crop_toggle(self, checked):
        self.crop_widget.setVisible(checked)

    def on_res_change(self, text):
        self.custom_res_widget.setVisible(text == "自定义")

    def on_multi_toggle(self, checked):
        self.spin_threads.setEnabled(checked)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输入目录")
        if folder:
            self.input_edit.setText(folder)
            import datetime
            out_path = Path(
                folder).parent / f"{Path(folder).name}_output_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
            self.output_edit.setText(str(out_path))

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_edit.setText(folder)

    def stop_processing(self):
        if self.is_processing:
            self.trimmer.stop_processing_task()
            self.lbl_progress.setText(">> 正在强行截断进程，请稍候...")

    def update_progress(self, current, total, filename):
        self.lbl_progress.setText(f">> 进度: [{current}/{total}] | 当前目标: {filename}")

    def start_processing(self):
        if not self.input_edit.text() or not self.output_edit.text():
            QMessageBox.critical(self, "异常", "未指定输入或输出目录！")
            return

        trim_start = safe_float(self.spin_trim_start.text(), 0)
        trim_end = safe_float(self.spin_trim_end.text(), 0)

        target_resolution = self.combo_res.currentText()
        if target_resolution == "自定义":
            target_resolution = f"{safe_int(self.custom_w.text(), 1080)}x{safe_int(self.custom_h.text(), 1920)}"

        crop_params = None
        if self.chk_crop.isChecked():
            crop_params = {
                'x': safe_int(self.crop_x.text(), 0), 'y': safe_int(self.crop_y.text(), 0),
                'width': safe_int(self.crop_w.text(), 1920), 'height': safe_int(self.crop_h.text(), 1080)
            }

        self.trimmer.max_workers = self.spin_threads.value()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.is_processing = True
        self.log_text.clear()

        def process_thread():
            try:
                self.trimmer.batch_trim_videos(
                    self.input_edit.text(), self.output_edit.text(), trim_start, trim_end,
                    target_resolution, self.update_progress, self.chk_multi.isChecked(),
                    crop_params, self.chk_time_trim.isChecked()
                )
                if not self.trimmer.stop_processing:
                    self.lbl_progress.setText(">> 任务完全结束。")
                else:
                    self.lbl_progress.setText(">> 任务已被安全终止。")
            except Exception as e:
                print(f"[ERROR] 发生异常: {e}")
            finally:
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
                self.is_processing = False

        threading.Thread(target=process_thread, daemon=True).start()


def main():
    multiprocessing.freeze_support()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    gui = VideoTrimmerGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()