import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from pydub import AudioSegment
from pydub.utils import which
import json
import time
from datetime import datetime


class AudioProcessor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("音频批量处理工具 v2.1")
        self.root.geometry("900x800")

        # 支持的音频格式
        self.supported_formats = ['.mp3', '.wav', '.ogg', '.mp4', '.m4a', '.flac', '.aac', '.wma']

        # 音频文件列表
        self.audio_files = []

        # 处理统计
        self.processing_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'current': 0,
            'start_time': None
        }

        # 输出设置
        self.output_dir = tk.StringVar()
        self.output_format = tk.StringVar(value="mp3")
        self.output_prefix = tk.StringVar()
        self.output_suffix = tk.StringVar()

        # 处理选项
        self.enable_trim = tk.BooleanVar()
        self.trim_mode = tk.StringVar(value="from_start")
        self.trim_seconds = tk.DoubleVar(value=5.0)
        self.trim_start_time = tk.DoubleVar(value=0.0)
        self.trim_end_time = tk.DoubleVar(value=10.0)

        self.enable_volume = tk.BooleanVar()
        self.volume_change = tk.DoubleVar()

        self.enable_format_convert = tk.BooleanVar()

        # 日志相关
        self.auto_scroll = tk.BooleanVar(value=True)
        self.show_detailed_log = tk.BooleanVar(value=True)

        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        # 创建主要的Notebook（标签页）
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # 主处理页面
        main_frame = ttk.Frame(notebook, padding="10")
        notebook.add(main_frame, text="音频处理")

        # 日志页面
        log_frame = ttk.Frame(notebook, padding="10")
        notebook.add(log_frame, text="处理日志")

        self.setup_main_page(main_frame)
        self.setup_log_page(log_frame)

    def setup_main_page(self, parent):
        # 文件选择区域
        file_frame = ttk.LabelFrame(parent, text="文件选择", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Button(file_frame, text="选择音频文件",
                   command=self.select_files).grid(row=0, column=0, padx=5)
        ttk.Button(file_frame, text="清空列表",
                   command=self.clear_files).grid(row=0, column=1, padx=5)

        # 文件列表
        list_frame = ttk.Frame(file_frame)
        list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.file_listbox = tk.Listbox(list_frame, height=5)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 输出设置区域
        output_frame = ttk.LabelFrame(parent, text="输出设置", padding="5")
        output_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(output_frame, text="输出目录:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(output_frame, textvariable=self.output_dir, width=40).grid(row=0, column=1, padx=5)
        ttk.Button(output_frame, text="浏览",
                   command=self.select_output_dir).grid(row=0, column=2)

        ttk.Label(output_frame, text="文件名前缀:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(output_frame, textvariable=self.output_prefix, width=20).grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(output_frame, text="文件名后缀:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(output_frame, textvariable=self.output_suffix, width=20).grid(row=2, column=1, sticky=tk.W, padx=5)

        # 处理选项区域
        options_frame = ttk.LabelFrame(parent, text="处理选项", padding="5")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # 格式转换选项
        format_frame = ttk.Frame(options_frame)
        format_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.format_checkbox = ttk.Checkbutton(format_frame, text="启用格式转换",
                                               variable=self.enable_format_convert,
                                               command=self.on_format_toggle)
        self.format_checkbox.grid(row=0, column=0, sticky=tk.W)

        ttk.Label(format_frame, text="目标格式:").grid(row=0, column=1, sticky=tk.W, padx=(20, 5))
        self.format_combo = ttk.Combobox(format_frame, textvariable=self.output_format,
                                         values=['mp3', 'wav', 'ogg', 'mp4', 'm4a', 'flac', 'aac'],
                                         state='disabled', width=10)
        self.format_combo.grid(row=0, column=2, padx=5)

        # 裁剪选项
        trim_frame = ttk.LabelFrame(options_frame, text="音频裁剪", padding="5")
        trim_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.trim_checkbox = ttk.Checkbutton(trim_frame, text="启用音频裁剪",
                                             variable=self.enable_trim,
                                             command=self.on_trim_toggle)
        self.trim_checkbox.grid(row=0, column=0, sticky=tk.W)

        # 裁剪模式选择
        mode_frame = ttk.Frame(trim_frame)
        mode_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(mode_frame, text="裁剪模式:").grid(row=0, column=0, sticky=tk.W)
        self.trim_mode_combo = ttk.Combobox(mode_frame, textvariable=self.trim_mode,
                                            values=['from_start', 'from_end', 'middle'],
                                            state='disabled', width=15)
        self.trim_mode_combo.grid(row=0, column=1, padx=5)
        self.trim_mode_combo.bind('<<ComboboxSelected>>', self.on_trim_mode_change)

        # 创建模式说明标签
        self.mode_label = ttk.Label(mode_frame, text="从开头裁剪指定秒数", foreground="blue")
        self.mode_label.grid(row=0, column=2, padx=10)

        # 前后裁剪设置
        self.simple_trim_frame = ttk.Frame(trim_frame)
        self.simple_trim_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(self.simple_trim_frame, text="裁剪时长(秒):").grid(row=0, column=0, sticky=tk.W)
        self.trim_seconds_entry = ttk.Entry(self.simple_trim_frame, textvariable=self.trim_seconds,
                                            width=10, state='disabled')
        self.trim_seconds_entry.grid(row=0, column=1, padx=5)

        # 中间裁剪设置
        self.middle_trim_frame = ttk.Frame(trim_frame)

        ttk.Label(self.middle_trim_frame, text="开始时间(秒):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_time_entry = ttk.Entry(self.middle_trim_frame, textvariable=self.trim_start_time,
                                          width=10, state='disabled')
        self.start_time_entry.grid(row=0, column=1, padx=5)

        ttk.Label(self.middle_trim_frame, text="结束时间(秒):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.end_time_entry = ttk.Entry(self.middle_trim_frame, textvariable=self.trim_end_time,
                                        width=10, state='disabled')
        self.end_time_entry.grid(row=1, column=1, padx=5)

        # 音量调整选项
        volume_frame = ttk.LabelFrame(options_frame, text="音量调整", padding="5")
        volume_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.volume_checkbox = ttk.Checkbutton(volume_frame, text="启用音量调整",
                                               variable=self.enable_volume,
                                               command=self.on_volume_toggle)
        self.volume_checkbox.grid(row=0, column=0, sticky=tk.W)

        ttk.Label(volume_frame, text="音量变化(dB):").grid(row=0, column=1, sticky=tk.W, padx=(20, 5))
        self.volume_entry = ttk.Entry(volume_frame, textvariable=self.volume_change,
                                      width=10, state='disabled')
        self.volume_entry.grid(row=0, column=2, padx=5)
        ttk.Label(volume_frame, text="(正数增大，负数减小)").grid(row=0, column=3, sticky=tk.W)

        # 处理按钮和进度条
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=3, column=0, columnspan=2, pady=10)

        self.process_button = ttk.Button(control_frame, text="开始处理",
                                         command=self.start_processing)
        self.process_button.grid(row=0, column=0, padx=5)

        ttk.Button(control_frame, text="验证设置",
                   command=self.validate_settings).grid(row=0, column=1, padx=5)

        ttk.Button(control_frame, text="清空日志",
                   command=self.clear_log).grid(row=0, column=2, padx=5)

        self.progress = ttk.Progressbar(control_frame, length=300, mode='determinate')
        self.progress.grid(row=1, column=0, columnspan=3, pady=5)

        # 状态信息
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=4, column=0, columnspan=2, pady=5)

        self.status_label = ttk.Label(status_frame, text="就绪", font=('Arial', 10, 'bold'))
        self.status_label.grid(row=0, column=0, padx=5)

        self.stats_label = ttk.Label(status_frame, text="", foreground="blue")
        self.stats_label.grid(row=0, column=1, padx=20)

        # 简化的日志显示（主页面）
        mini_log_frame = ttk.LabelFrame(parent, text="最近日志", padding="5")
        mini_log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.mini_log_text = tk.Text(mini_log_frame, height=4, width=70, state='disabled')
        mini_log_scrollbar = ttk.Scrollbar(mini_log_frame, orient="vertical", command=self.mini_log_text.yview)
        self.mini_log_text.configure(yscrollcommand=mini_log_scrollbar.set)

        self.mini_log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        mini_log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 配置网格权重
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(5, weight=1)
        mini_log_frame.columnconfigure(0, weight=1)
        mini_log_frame.rowconfigure(0, weight=1)

    def setup_log_page(self, parent):
        # 日志控制区域
        log_control_frame = ttk.Frame(parent)
        log_control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Checkbutton(log_control_frame, text="自动滚动",
                        variable=self.auto_scroll).grid(row=0, column=0, padx=5)

        ttk.Checkbutton(log_control_frame, text="详细日志",
                        variable=self.show_detailed_log).grid(row=0, column=1, padx=5)

        ttk.Button(log_control_frame, text="清空日志",
                   command=self.clear_log).grid(row=0, column=2, padx=5)

        ttk.Button(log_control_frame, text="保存日志",
                   command=self.save_log).grid(row=0, column=3, padx=5)

        ttk.Button(log_control_frame, text="导出报告",
                   command=self.export_report).grid(row=0, column=4, padx=5)

        # 统计信息显示
        stats_frame = ttk.LabelFrame(parent, text="处理统计", padding="5")
        stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.detailed_stats_label = ttk.Label(stats_frame, text="等待开始处理...",
                                              font=('Arial', 9))
        self.detailed_stats_label.grid(row=0, column=0, sticky=tk.W)

        # 详细日志显示
        detailed_log_frame = ttk.LabelFrame(parent, text="详细处理日志", padding="5")
        detailed_log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # 创建带有文本标签的日志文本框
        log_text_frame = ttk.Frame(detailed_log_frame)
        log_text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.detailed_log_text = tk.Text(log_text_frame, height=20, width=80,
                                         wrap=tk.WORD, state='disabled')
        detailed_log_scrollbar = ttk.Scrollbar(log_text_frame, orient="vertical",
                                               command=self.detailed_log_text.yview)
        self.detailed_log_text.configure(yscrollcommand=detailed_log_scrollbar.set)

        self.detailed_log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        detailed_log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 配置文本标签
        self.detailed_log_text.tag_configure("timestamp", foreground="gray")
        self.detailed_log_text.tag_configure("info", foreground="black")
        self.detailed_log_text.tag_configure("success", foreground="green", font=('Arial', 9, 'bold'))
        self.detailed_log_text.tag_configure("error", foreground="red", font=('Arial', 9, 'bold'))
        self.detailed_log_text.tag_configure("warning", foreground="orange", font=('Arial', 9, 'bold'))
        self.detailed_log_text.tag_configure("processing", foreground="blue")
        self.detailed_log_text.tag_configure("header", foreground="purple", font=('Arial', 10, 'bold'))

        # 配置网格权重
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(2, weight=1)
        detailed_log_frame.columnconfigure(0, weight=1)
        detailed_log_frame.rowconfigure(0, weight=1)
        log_text_frame.columnconfigure(0, weight=1)
        log_text_frame.rowconfigure(0, weight=1)

    def setup_bindings(self):
        """设置控件绑定"""
        self.update_trim_mode_description()

    def log(self, message, level="info", show_timestamp=True):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S") if show_timestamp else ""

        # 更新简化日志（主页面）
        self.mini_log_text.config(state='normal')
        if timestamp:
            self.mini_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        else:
            self.mini_log_text.insert(tk.END, f"{message}\n")

        # 保持简化日志只显示最后10行
        lines = self.mini_log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 11:  # 10行 + 1个空行
            self.mini_log_text.delete("1.0", "2.0")

        self.mini_log_text.config(state='disabled')
        self.mini_log_text.see(tk.END)

        # 更新详细日志（日志页面）
        self.detailed_log_text.config(state='normal')

        if timestamp:
            self.detailed_log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")

        # 根据级别应用不同的标签
        if level == "success":
            self.detailed_log_text.insert(tk.END, f"✓ {message}\n", "success")
        elif level == "error":
            self.detailed_log_text.insert(tk.END, f"✗ {message}\n", "error")
        elif level == "warning":
            self.detailed_log_text.insert(tk.END, f"⚠ {message}\n", "warning")
        elif level == "processing":
            self.detailed_log_text.insert(tk.END, f"▶ {message}\n", "processing")
        elif level == "header":
            self.detailed_log_text.insert(tk.END, f"{'=' * 50}\n", "header")
            self.detailed_log_text.insert(tk.END, f"{message}\n", "header")
            self.detailed_log_text.insert(tk.END, f"{'=' * 50}\n", "header")
        else:
            self.detailed_log_text.insert(tk.END, f"{message}\n", "info")

        self.detailed_log_text.config(state='disabled')

        if self.auto_scroll.get():
            self.detailed_log_text.see(tk.END)

        self.root.update_idletasks()

    def update_stats(self):
        """更新统计信息"""
        stats = self.processing_stats

        if stats['start_time']:
            elapsed = time.time() - stats['start_time']
            elapsed_str = f"{elapsed:.1f}秒"

            # 计算预计剩余时间
            if stats['current'] > 0:
                avg_time = elapsed / stats['current']
                remaining = (stats['total'] - stats['current']) * avg_time
                remaining_str = f"{remaining:.1f}秒"
            else:
                remaining_str = "计算中..."
        else:
            elapsed_str = "0秒"
            remaining_str = "未开始"

        # 主页面统计
        main_stats = f"进度: {stats['current']}/{stats['total']} | 成功: {stats['success']} | 失败: {stats['failed']}"
        self.stats_label.config(text=main_stats)

        # 详细统计
        detailed_stats = (
            f"总文件数: {stats['total']} | "
            f"已处理: {stats['current']} | "
            f"成功: {stats['success']} | "
            f"失败: {stats['failed']} | "
            f"已用时: {elapsed_str} | "
            f"预计剩余: {remaining_str}"
        )
        self.detailed_stats_label.config(text=detailed_stats)

    def clear_log(self):
        """清空日志"""
        self.mini_log_text.config(state='normal')
        self.mini_log_text.delete(1.0, tk.END)
        self.mini_log_text.config(state='disabled')

        self.detailed_log_text.config(state='normal')
        self.detailed_log_text.delete(1.0, tk.END)
        self.detailed_log_text.config(state='disabled')

        self.log("日志已清空", "info")

    def save_log(self):
        """保存日志到文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="保存日志文件"
        )

        if filename:
            try:
                log_content = self.detailed_log_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"音频处理日志 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 60 + "\n")
                    f.write(log_content)

                self.log(f"日志已保存到: {filename}", "success")
            except Exception as e:
                self.log(f"保存日志失败: {str(e)}", "error")

    def export_report(self):
        """导出处理报告"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="导出处理报告"
        )

        if filename:
            try:
                stats = self.processing_stats
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("音频批量处理报告\n")
                    f.write("=" * 40 + "\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                    f.write("处理统计:\n")
                    f.write(f"  总文件数: {stats['total']}\n")
                    f.write(f"  成功处理: {stats['success']}\n")
                    f.write(f"  处理失败: {stats['failed']}\n")
                    f.write(f"  成功率: {(stats['success'] / stats['total'] * 100):.1f}%\n\n" if stats[
                                                                                                     'total'] > 0 else "  成功率: 0%\n\n")

                    f.write("处理设置:\n")
                    f.write(f"  格式转换: {'是' if self.enable_format_convert.get() else '否'}\n")
                    if self.enable_format_convert.get():
                        f.write(f"  目标格式: {self.output_format.get()}\n")
                    f.write(f"  音频裁剪: {'是' if self.enable_trim.get() else '否'}\n")
                    if self.enable_trim.get():
                        f.write(f"  裁剪模式: {self.trim_mode.get()}\n")
                    f.write(f"  音量调整: {'是' if self.enable_volume.get() else '否'}\n")
                    if self.enable_volume.get():
                        f.write(f"  音量变化: {self.volume_change.get():+.1f}dB\n")

                    f.write("\n详细日志:\n")
                    f.write("-" * 40 + "\n")
                    f.write(self.detailed_log_text.get(1.0, tk.END))

                self.log(f"处理报告已导出到: {filename}", "success")
            except Exception as e:
                self.log(f"导出报告失败: {str(e)}", "error")

    # 其他方法保持不变，但增加详细日志记录
    def on_format_toggle(self):
        """格式转换复选框切换事件"""
        state = 'normal' if self.enable_format_convert.get() else 'disabled'
        self.format_combo.config(state=state)

    def on_trim_toggle(self):
        """裁剪复选框切换事件"""
        state = 'normal' if self.enable_trim.get() else 'disabled'
        readonly_state = 'readonly' if self.enable_trim.get() else 'disabled'

        self.trim_mode_combo.config(state=readonly_state)
        self.trim_seconds_entry.config(state=state)
        self.start_time_entry.config(state=state)
        self.end_time_entry.config(state=state)

        if not self.enable_trim.get():
            self.simple_trim_frame.grid_remove()
            self.middle_trim_frame.grid_remove()
        else:
            self.on_trim_mode_change()

    def on_volume_toggle(self):
        """音量调整复选框切换事件"""
        state = 'normal' if self.enable_volume.get() else 'disabled'
        self.volume_entry.config(state=state)

    def on_trim_mode_change(self, event=None):
        """裁剪模式改变事件"""
        if not self.enable_trim.get():
            return

        mode = self.trim_mode.get()

        self.simple_trim_frame.grid_remove()
        self.middle_trim_frame.grid_remove()

        if mode == 'middle':
            self.middle_trim_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        else:
            self.simple_trim_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.update_trim_mode_description()

    def update_trim_mode_description(self):
        """更新裁剪模式说明"""
        mode = self.trim_mode.get()
        descriptions = {
            'from_start': '从开头裁剪指定秒数',
            'from_end': '从结尾裁剪指定秒数',
            'middle': '提取中间时间段'
        }
        self.mode_label.config(text=descriptions.get(mode, ''))

    def validate_settings(self):
        """验证设置是否合理"""
        errors = []
        warnings = []

        if not self.audio_files:
            errors.append("请先选择音频文件")

        if not self.output_dir.get():
            errors.append("请选择输出目录")
        elif not os.path.exists(self.output_dir.get()):
            errors.append("输出目录不存在")

        if not any([self.enable_trim.get(), self.enable_volume.get(), self.enable_format_convert.get()]):
            warnings.append("未启用任何处理功能，将只复制文件")

        if self.enable_trim.get():
            mode = self.trim_mode.get()
            if mode == 'middle':
                start_time = self.trim_start_time.get()
                end_time = self.trim_end_time.get()
                if start_time >= end_time:
                    errors.append("中间裁剪：开始时间必须小于结束时间")
                if start_time < 0 or end_time < 0:
                    errors.append("时间不能为负数")
            else:
                trim_seconds = self.trim_seconds.get()
                if trim_seconds <= 0:
                    errors.append("裁剪时长必须大于0")

        if self.enable_volume.get():
            volume = self.volume_change.get()
            if volume < -60 or volume > 60:
                warnings.append("音量调整范围建议在-60dB到+60dB之间")

        if errors:
            messagebox.showerror("设置错误", "\n".join(errors))
            self.log("设置验证失败: " + "; ".join(errors), "error")
            return False
        elif warnings:
            result = messagebox.askwarning("设置警告",
                                           "\n".join(warnings) + "\n\n是否继续？",
                                           type=messagebox.YESNO)
            if result == messagebox.YES:
                self.log("设置验证通过（有警告）: " + "; ".join(warnings), "warning")
            return result == messagebox.YES
        else:
            messagebox.showinfo("验证通过", "所有设置验证通过！")
            self.log("设置验证通过", "success")
            return True

    def select_files(self):
        filetypes = [
            ("音频文件", "*.mp3 *.wav *.ogg *.mp4 *.m4a *.flac *.aac *.wma"),
            ("所有文件", "*.*")
        ]

        files = filedialog.askopenfilenames(
            title="选择音频文件",
            filetypes=filetypes
        )

        added_count = 0
        for file in files:
            if file not in self.audio_files:
                self.audio_files.append(file)
                self.file_listbox.insert(tk.END, os.path.basename(file))
                added_count += 1

        self.log(f"已添加 {added_count} 个文件，总计 {len(self.audio_files)} 个文件", "info")

    def clear_files(self):
        count = len(self.audio_files)
        self.audio_files.clear()
        self.file_listbox.delete(0, tk.END)
        self.log(f"已清空 {count} 个文件", "info")

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
            self.log(f"输出目录设置为: {directory}", "info")

    def start_processing(self):
        if not self.validate_settings():
            return

        # 初始化统计信息
        self.processing_stats = {
            'total': len(self.audio_files),
            'success': 0,
            'failed': 0,
            'current': 0,
            'start_time': time.time()
        }

        self.log("开始批量处理音频文件", "header")
        self.log(f"计划处理 {self.processing_stats['total']} 个文件", "info")

        # 记录处理设置
        settings = []
        if self.enable_format_convert.get():
            settings.append(f"格式转换: {self.output_format.get()}")
        if self.enable_trim.get():
            if self.trim_mode.get() == 'middle':
                settings.append(f"裁剪: 提取 {self.trim_start_time.get()}-{self.trim_end_time.get()}秒")
            else:
                mode_desc = "从开头" if self.trim_mode.get() == 'from_start' else "从结尾"
                settings.append(f"裁剪: {mode_desc}裁剪{self.trim_seconds.get()}秒")
        if self.enable_volume.get():
            settings.append(f"音量调整: {self.volume_change.get():+.1f}dB")

        if settings:
            self.log("处理设置: " + "; ".join(settings), "info")
        else:
            self.log("仅复制文件（未启用处理功能）", "warning")

        self.process_button.config(state='disabled')
        threading.Thread(target=self.process_audio_files, daemon=True).start()

    def process_audio_files(self):
        try:
            total_files = len(self.audio_files)
            self.progress['maximum'] = total_files

            for i, file_path in enumerate(self.audio_files):
                self.processing_stats['current'] = i + 1
                filename = os.path.basename(file_path)

                self.status_label.config(text=f"处理中: {filename}")
                self.log(f"开始处理第 {i + 1}/{total_files} 个文件: {filename}", "processing")

                try:
                    # 加载音频文件
                    start_time = time.time()
                    audio = AudioSegment.from_file(file_path)
                    load_time = time.time() - start_time

                    original_duration = len(audio) / 1000
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB

                    self.log(
                        f"  文件信息: 时长 {original_duration:.2f}秒, 大小 {file_size:.2f}MB, 加载耗时 {load_time:.2f}秒",
                        "info")

                    # 处理步骤
                    processed_steps = []

                    # 裁剪处理
                    if self.enable_trim.get():
                        trim_start = time.time()
                        audio = self.trim_audio(audio)
                        trim_time = time.time() - trim_start

                        new_duration = len(audio) / 1000
                        mode = self.trim_mode.get()
                        if mode == 'middle':
                            trim_desc = f"提取 {self.trim_start_time.get()}-{self.trim_end_time.get()}秒"
                        else:
                            mode_desc = "从开头" if mode == 'from_start' else "从结尾"
                            trim_desc = f"{mode_desc}裁剪{self.trim_seconds.get()}秒"

                        processed_steps.append(f"裁剪({trim_desc})")
                        self.log(f"  裁剪完成: {original_duration:.2f}s → {new_duration:.2f}s, 耗时 {trim_time:.2f}秒",
                                 "info")

                    # 音量调整
                    if self.enable_volume.get():
                        volume_start = time.time()
                        audio = self.adjust_volume(audio)
                        volume_time = time.time() - volume_start

                        processed_steps.append(f"音量调整({self.volume_change.get():+.1f}dB)")
                        self.log(f"  音量调整完成: {self.volume_change.get():+.1f}dB, 耗时 {volume_time:.2f}秒", "info")

                    # 生成输出文件名
                    output_filename = self.generate_output_filename(file_path)
                    output_path = os.path.join(self.output_dir.get(), output_filename)

                    # 导出音频
                    export_start = time.time()
                    if self.enable_format_convert.get():
                        format_params = self.get_format_params()
                        audio.export(output_path, format=self.output_format.get(), **format_params)
                        processed_steps.append(f"格式转换({self.output_format.get().upper()})")
                    else:
                        original_format = os.path.splitext(file_path)[1][1:].lower()
                        if original_format in ['mp4', 'm4a']:
                            original_format = 'mp4'
                        audio.export(output_path, format=original_format)
                        processed_steps.append("保持原格式")

                    export_time = time.time() - export_start
                    output_size = os.path.getsize(output_path) / (1024 * 1024)  # MB

                    total_time = time.time() - start_time
                    process_desc = " + ".join(processed_steps) if processed_steps else "仅复制"

                    self.log(f"  导出完成: {output_size:.2f}MB, 耗时 {export_time:.2f}秒", "info")
                    self.log(f"处理完成: {filename} → {output_filename}", "success")
                    self.log(f"  处理内容: {process_desc}", "info")
                    self.log(f"  总耗时: {total_time:.2f}秒", "info")

                    self.processing_stats['success'] += 1

                except Exception as e:
                    error_msg = str(e)
                    self.log(f"处理失败: {filename}", "error")
                    self.log(f"  错误详情: {error_msg}", "error")
                    self.processing_stats['failed'] += 1

                self.progress['value'] = i + 1
                self.update_stats()
                self.root.update_idletasks()

            # 处理完成统计
            total_time = time.time() - self.processing_stats['start_time']
            success_rate = (self.processing_stats['success'] / total_files * 100) if total_files > 0 else 0

            self.status_label.config(text="处理完成")
            self.log("批量处理完成", "header")
            self.log(f"处理结果统计:", "info")
            self.log(f"  总文件数: {total_files}", "info")
            self.log(f"  成功处理: {self.processing_stats['success']}", "success")
            self.log(f"  处理失败: {self.processing_stats['failed']}", "error")
            self.log(f"  成功率: {success_rate:.1f}%", "info")
            self.log(f"  总耗时: {total_time:.2f}秒", "info")
            self.log(f"  平均耗时: {total_time / total_files:.2f}秒/文件", "info")

            messagebox.showinfo("完成",
                                f"音频处理完成！\n"
                                f"成功处理: {self.processing_stats['success']}/{total_files} 个文件\n"
                                f"成功率: {success_rate:.1f}%\n"
                                f"总耗时: {total_time:.1f}秒")

        except Exception as e:
            self.log(f"处理过程中发生严重错误: {str(e)}", "error")
            messagebox.showerror("错误", f"处理失败: {str(e)}")

        finally:
            self.process_button.config(state='normal')
            self.progress['value'] = 0

    def trim_audio(self, audio):
        """裁剪音频"""
        duration_ms = len(audio)
        mode = self.trim_mode.get()

        if mode == "from_start":
            trim_ms = self.trim_seconds.get() * 1000
            if trim_ms < duration_ms:
                audio = audio[int(trim_ms):]
            else:
                raise ValueError(f"裁剪时长({self.trim_seconds.get()}秒)超过音频总时长({duration_ms / 1000:.2f}秒)")

        elif mode == "from_end":
            trim_ms = self.trim_seconds.get() * 1000
            if trim_ms < duration_ms:
                audio = audio[:-int(trim_ms)]
            else:
                raise ValueError(f"裁剪时长({self.trim_seconds.get()}秒)超过音频总时长({duration_ms / 1000:.2f}秒)")

        elif mode == "middle":
            start_ms = self.trim_start_time.get() * 1000
            end_ms = self.trim_end_time.get() * 1000

            if end_ms > duration_ms:
                raise ValueError(f"结束时间({self.trim_end_time.get()}秒)超过音频总时长({duration_ms / 1000:.2f}秒)")

            audio = audio[int(start_ms):int(end_ms)]

        return audio

    def adjust_volume(self, audio):
        """调整音量"""
        volume_change = self.volume_change.get()
        return audio + volume_change

    def generate_output_filename(self, input_path):
        """生成输出文件名"""
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        prefix = self.output_prefix.get()
        suffix = self.output_suffix.get()

        if self.enable_format_convert.get():
            extension = f".{self.output_format.get()}"
        else:
            extension = os.path.splitext(input_path)[1]

        return f"{prefix}{base_name}{suffix}{extension}"

    def get_format_params(self):
        """获取格式参数"""
        format_params = {}
        output_format = self.output_format.get()

        if output_format == "mp3":
            format_params = {"bitrate": "192k"}
        elif output_format == "wav":
            format_params = {"parameters": ["-acodec", "pcm_s16le"]}
        elif output_format == "ogg":
            format_params = {"codec": "libvorbis"}
        elif output_format == "m4a":
            format_params = {"codec": "aac", "bitrate": "192k"}
        elif output_format == "flac":
            format_params = {"parameters": ["-acodec", "flac"]}

        return format_params

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        import pydub
    except ImportError:
        print("请安装pydub库: pip install pydub")
        exit(1)

    app = AudioProcessor()
    app.run()

