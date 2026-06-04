import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QLabel, QLineEdit,
                               QFileDialog, QProgressBar, QTextEdit, QMessageBox)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QIcon


# ----------------- 智能寻找 FFmpeg 核心逻辑 -----------------
def get_bin_path(bin_name):
    if getattr(sys, 'frozen', False):
        app_path = os.path.dirname(sys.executable)
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(app_path, bin_name)
    if os.path.exists(local_path):
        return local_path
    return bin_name


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


FFMPEG_CMD = get_bin_path('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
FFPROBE_CMD = get_bin_path('ffprobe.exe' if os.name == 'nt' else 'ffprobe')


# ----------------- 进阶特性：支持拖拽的输入框 -----------------
class DragLineEdit(QLineEdit):
    def __init__(self, placeholder=""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.setText(file_path)


# ----------------- 核心处理线程 -----------------
class VideoWorker(QThread):
    progress_update = Signal(int, int)
    log_update = Signal(str)
    finished = Signal()

    def __init__(self, overlay_folder, input_folder, output_folder, encoder):
        super().__init__()
        self.overlay_folder = overlay_folder  # 现在这里接收的是贴片文件夹
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.encoder = encoder
        self.is_running = True
        self.process = None
        self.audit_log = []

    def emit_log(self, msg):
        self.log_update.emit(msg)
        self.audit_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def get_video_duration(self, video_path):
        cmd = [
            FFPROBE_CMD, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding='utf-8', errors='ignore',
                                    creationflags=creationflags)
            return float(result.stdout.strip())
        except Exception as e:
            self.emit_log(f"⚠️ 警告: 获取时长失败 ({video_path.name}): {str(e)}")
            return None

    def run(self):
        # 常见视频及透明通道视频格式
        support_exts = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}

        # --- 进阶功能一：载入所有贴片文件 ---
        overlay_dir = Path(self.overlay_folder)
        overlay_files = [f for f in overlay_dir.iterdir() if f.is_file() and f.suffix.lower() in support_exts]

        if not overlay_files:
            self.emit_log("❌ 贴片文件夹中未找到任何支持的视频文件！请检查。")
            self.finished.emit()
            return

        self.emit_log(f"🧩 成功加载 {len(overlay_files)} 个贴片，将按顺序轮询合成。")

        # --- 进阶功能二：项目两级隔离穿透提取逻辑 ---
        input_dir = Path(self.input_folder)
        output_dir = Path(self.output_folder)
        project_dirs = [d for d in input_dir.iterdir() if d.is_dir()]

        if not project_dirs:
            self.emit_log("❌ 主文件夹中未找到任何一级项目子文件夹！请检查目录结构。")
            self.finished.emit()
            return

        all_tasks = []
        for proj_dir in project_dirs:
            proj_out_dir = output_dir / f"{proj_dir.name}_处理后"
            for file_path in proj_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in support_exts:
                    all_tasks.append((file_path, proj_out_dir))

        total_files = len(all_tasks)

        if total_files == 0:
            self.emit_log("❌ 在所有的项目子文件夹中均未找到支持的视频文件！")
            self.finished.emit()
            return

        self.emit_log(f"🎬 共扫描 {len(project_dirs)} 个项目文件夹，提取主视频 {total_files} 个，准备开始...")
        self.emit_log(f"🚀 当前引擎: {self.encoder}")

        # 统一遍历执行
        for index, (video_path, proj_out_dir) in enumerate(all_tasks):
            if not self.is_running:
                self.emit_log("⚠️ 任务已被用户强制取消。")
                break

            proj_out_dir.mkdir(parents=True, exist_ok=True)
            out_file = proj_out_dir / video_path.name

            duration = self.get_video_duration(video_path)
            duration_info = f" (时长: {duration:.2f}秒)" if duration else ""

            # --- 核心轮询算法：利用取余(%)实现贴片循环使用 ---
            current_overlay = overlay_files[index % len(overlay_files)]

            project_name = proj_out_dir.name.replace("_处理后", "")
            self.emit_log(f"\n⏳ 进度 [{index + 1}/{total_files}] | 归属项目: {project_name}")
            self.emit_log(f"   ➤ 原片: {video_path.name}{duration_info}")
            self.emit_log(f"   ➤ 贴片: {current_overlay.name} (轮询匹配)")

            filter_str = '[1:v][0:v]scale2ref=w=iw:h=ih[ovrl][base];[base][ovrl]overlay=eof_action=pass[out]'

            cmd = [
                FFMPEG_CMD, '-y',
                '-i', str(video_path),
                '-i', str(current_overlay),  # 使用当前轮询到的贴片
                '-filter_complex', filter_str,
                '-map', '[out]',
                '-map', '0:a?'
            ]

            if duration is not None:
                cmd.extend(['-t', str(duration)])

            cmd.extend(['-c:v', self.encoder])
            if self.encoder == 'libx264':
                cmd.extend(['-crf', '23'])
            elif 'nvenc' in self.encoder:
                cmd.extend(['-cq', '24'])

            cmd.extend(['-c:a', 'copy', str(out_file)])

            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                text=True, encoding='utf-8', errors='ignore',
                                                creationflags=creationflags)

                _, stderr = self.process.communicate()

                if self.process.returncode == 0:
                    self.emit_log("   ✅ 成功完成！")
                else:
                    if self.is_running:
                        self.emit_log("   ❌ 处理失败！")
                        self.emit_log(f"   错误详情: {stderr[-500:]}")
            except Exception as e:
                self.emit_log(f"   ❌ 发生异常: {str(e)}")

            self.progress_update.emit(index + 1, total_files)

        self.emit_log("\n🎉 所有项目与贴片轮询匹配处理任务均已结束！")

        try:
            with open(output_dir / "process_error_log.txt", 'w', encoding='utf-8') as f:
                f.write("\n".join(self.audit_log))
        except:
            pass

        self.finished.emit()

    def stop(self):
        self.is_running = False
        if self.process and self.process.poll() is None:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], creationflags=0x08000000)
                else:
                    self.process.terminate()
            except:
                pass


# ----------------- UI 主窗口 -----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("大师级视频批量贴片工具 (项目隔离 + 贴片轮询版)")
        self.resize(800, 500)
        self.setWindowIcon(QIcon(get_resource_path('logo.ico')))

        self.encoder, self.hw_name = self.detect_hardware_encoder()
        self.init_ui()

    def detect_hardware_encoder(self):
        encoders_to_test = {
            'h264_nvenc': 'NVIDIA',
            'h264_amf': 'AMD',
            'h264_qsv': 'Intel',
            'h264_videotoolbox': 'Apple'
        }
        for enc, name in encoders_to_test.items():
            cmd = [FFMPEG_CMD, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=128x128', '-vframes', '1', '-c:v',
                   enc, '-f', 'null', '-']
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                if subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  creationflags=creationflags).returncode == 0:
                    return enc, name
            except Exception:
                continue
        return 'libx264', 'CPU'

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)

        if self.encoder == 'libx264':
            accel_info = f"⚡ 当前编码器: {self.encoder} (未检测到可用独立显卡，使用 CPU 软编码)"
            color = "#d32f2f"
        else:
            accel_info = f"⚡ 检测到 {self.hw_name} 显卡！已开启 GPU 硬件加速 ({self.encoder})"
            color = "#2e7d32"

        self.lbl_hw = QLabel(accel_info)
        self.lbl_hw.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.lbl_hw)

        # 修改了第一行的文字与逻辑，现在是选择“文件夹”而不是“视频文件”
        self.setup_path_row(layout, "1. 贴片总文件夹:", "请选择包含多个透明视频的文件夹...", self.select_overlay_folder,
                            "overlay_input")
        self.setup_path_row(layout, "2. 待处理总目录:", "请选择包含多个子项目文件夹的总目录...",
                            self.select_input_folder, "folder_input")
        self.setup_path_row(layout, "3. 保存总输出目录:", "请选择处理后的数据存放位置...", self.select_output_folder,
                            "folder_output")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(25)
        layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #00FF00; font-family: 'Consolas'; font-size: 12px;")
        layout.addWidget(self.log_text)

        btn_layout = QHBoxLayout()

        self.btn_start = QPushButton("🚀 开始多元素轮询匹配处理")
        self.btn_start.setFixedHeight(45)
        self.btn_start.setStyleSheet(
            "font-size: 16px; font-weight: bold; background-color: #1976d2; color: white; border-radius: 5px;")
        self.btn_start.clicked.connect(self.start_processing)

        self.btn_stop = QPushButton("🛑 强行停止")
        self.btn_stop.setFixedHeight(45)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "font-size: 16px; font-weight: bold; background-color: #d32f2f; color: white; border-radius: 5px;")
        self.btn_stop.clicked.connect(self.stop_processing)

        btn_layout.addWidget(self.btn_start, 8)
        btn_layout.addWidget(self.btn_stop, 2)
        layout.addLayout(btn_layout)

    def setup_path_row(self, parent_layout, label_text, placeholder, btn_func, attr_name):
        row_layout = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setFixedWidth(140)
        lbl.setStyleSheet("font-size: 14px; font-weight: bold;")

        line_edit = DragLineEdit(placeholder)
        line_edit.setFixedHeight(30)
        setattr(self, attr_name, line_edit)

        btn = QPushButton("浏览...")
        btn.setFixedHeight(30)
        btn.clicked.connect(btn_func)

        row_layout.addWidget(lbl)
        row_layout.addWidget(line_edit)
        row_layout.addWidget(btn)
        parent_layout.addLayout(row_layout)

    def select_overlay_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含贴片视频的文件夹")
        if folder: self.overlay_input.setText(folder)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输入总文件夹")
        if folder: self.folder_input.setText(folder)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出总文件夹")
        if folder: self.folder_output.setText(folder)

    def append_log(self, text):
        self.log_text.append(text)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, current, total):
        percentage = int((current / total) * 100)
        self.progress_bar.setValue(percentage)

    def start_processing(self):
        overlay_folder = self.overlay_input.text().strip()
        input_folder = self.folder_input.text().strip()
        output_folder = self.folder_output.text().strip()

        if not all([overlay_folder, input_folder, output_folder]):
            QMessageBox.warning(self, "信息不完整", "请检查这三个路径是否都已经填写完整！")
            return

        if not os.path.isdir(overlay_folder):
            QMessageBox.warning(self, "错误", "透明贴片文件夹不存在！")
            return

        self.btn_start.setEnabled(False)
        self.btn_start.setText("处理中...")
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        self.worker = VideoWorker(overlay_folder, input_folder, output_folder, self.encoder)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.log_update.connect(self.append_log)
        self.worker.finished.connect(self.processing_finished)
        self.worker.start()

    def stop_processing(self):
        self.btn_stop.setEnabled(False)
        self.append_log("⚠️ 正在强行停止底层处理进程，请稍候...")
        if hasattr(self, 'worker'):
            self.worker.stop()

    def processing_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("🚀 开始多元素轮询匹配处理")
        self.btn_stop.setEnabled(False)
        QMessageBox.information(self, "任务结束", "项目数据隔离与贴片轮询合成已结束！\n排错日志已保存在总输出文件夹中。")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())