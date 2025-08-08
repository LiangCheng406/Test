import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image
from pathlib import Path
import threading
from datetime import datetime
import queue
import sys
import subprocess

# 设置编码，解决乱码问题
if sys.platform.startswith('win'):
    import locale

    locale.setlocale(locale.LC_ALL, 'Chinese (Simplified)_China.936')


class ImageCropGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("图片底部裁剪工具 - GUI版本")
        self.root.geometry("800x600")

        # 创建消息队列用于线程间通信
        self.msg_queue = queue.Queue()

        # 添加停止标志
        self.stop_processing = threading.Event()

        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')

        self.setup_ui()

        # 启动消息队列检查
        self.root.after(100, self.check_queue)

    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # 标题
        title_label = ttk.Label(main_frame, text="图片底部裁剪工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # 模式选择
        mode_frame = ttk.LabelFrame(main_frame, text="处理模式", padding="10")
        mode_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        mode_frame.columnconfigure(0, weight=1)
        mode_frame.columnconfigure(1, weight=1)

        self.mode_var = tk.StringVar(value="batch")
        ttk.Radiobutton(mode_frame, text="批量处理文件夹", variable=self.mode_var,
                        value="batch", command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="处理单张图片", variable=self.mode_var,
                        value="single", command=self.on_mode_change).grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="统一分辨率", variable=self.mode_var,
                        value="resize", command=self.on_mode_change).grid(row=1, column=0, sticky=tk.W, padx=(0, 10))

        # 输入路径选择
        input_frame = ttk.LabelFrame(main_frame, text="输入设置", padding="10")
        input_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        self.input_label = ttk.Label(input_frame, text="输入文件夹:")
        self.input_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.input_path = tk.StringVar()
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_path, width=50)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))

        self.browse_input_btn = ttk.Button(input_frame, text="浏览", command=self.browse_input)
        self.browse_input_btn.grid(row=0, column=2)

        # 输出路径设置（仅批量处理时显示）
        self.output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding="10")
        self.output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        self.output_frame.columnconfigure(1, weight=1)

        ttk.Label(self.output_frame, text="输出文件夹:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.output_path = tk.StringVar()
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path, width=50, state="readonly")
        self.output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))

        self.browse_output_btn = ttk.Button(self.output_frame, text="自定义", command=self.browse_output)
        self.browse_output_btn.grid(row=0, column=2)

        # 说明文本
        self.output_info = ttk.Label(self.output_frame, text="输出文件夹将自动命名为：输入文件夹名_时间戳",
                                     foreground="gray")
        self.output_info.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # 裁剪设置
        crop_frame = ttk.LabelFrame(main_frame, text="裁剪设置", padding="10")
        crop_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        crop_frame.columnconfigure(1, weight=1)

        # 多方向裁剪设置（用于批量处理）
        self.multi_crop_frame = ttk.Frame(crop_frame)
        self.multi_crop_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E))

        # 第一行：上下方向
        row1_frame = ttk.Frame(self.multi_crop_frame)
        row1_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(row1_frame, text="顶部裁剪:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.top_pixels_var = tk.StringVar(value="0")
        ttk.Spinbox(row1_frame, from_=0, to=500, textvariable=self.top_pixels_var, width=8).grid(row=0, column=1,
                                                                                                 padx=(0, 20))

        ttk.Label(row1_frame, text="底部裁剪:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.bottom_pixels_var = tk.StringVar(value="30")
        ttk.Spinbox(row1_frame, from_=0, to=500, textvariable=self.bottom_pixels_var, width=8).grid(row=0, column=3,
                                                                                                    padx=(0, 20))

        ttk.Label(row1_frame, text="px").grid(row=0, column=4, sticky=tk.W)

        # 第二行：左右方向
        row2_frame = ttk.Frame(self.multi_crop_frame)
        row2_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))

        ttk.Label(row2_frame, text="左侧裁剪:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.left_pixels_var = tk.StringVar(value="0")
        ttk.Spinbox(row2_frame, from_=0, to=500, textvariable=self.left_pixels_var, width=8).grid(row=0, column=1,
                                                                                                  padx=(0, 20))

        ttk.Label(row2_frame, text="右侧裁剪:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.right_pixels_var = tk.StringVar(value="0")
        ttk.Spinbox(row2_frame, from_=0, to=500, textvariable=self.right_pixels_var, width=8).grid(row=0, column=3,
                                                                                                   padx=(0, 20))

        ttk.Label(row2_frame, text="px").grid(row=0, column=4, sticky=tk.W)

        # 基础裁剪设置（适用于单张图片模式）
        self.basic_crop_frame = ttk.Frame(crop_frame)
        self.basic_crop_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Label(self.basic_crop_frame, text="底部裁剪像素数:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.pixels_var = tk.StringVar(value="30")
        pixels_spinbox = ttk.Spinbox(self.basic_crop_frame, from_=1, to=500, textvariable=self.pixels_var, width=10)
        pixels_spinbox.grid(row=0, column=1, sticky=tk.W)

        # 分辨率设置
        self.resolution_frame = ttk.Frame(crop_frame)
        self.resolution_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Label(self.resolution_frame, text="目标分辨率:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.resolution_var = tk.StringVar(value="1080x1920")
        resolution_combo = ttk.Combobox(self.resolution_frame, textvariable=self.resolution_var,
                                        values=["1080x1920", "1920x1080", "1440x2560", "2560x1440",
                                                "720x1280", "1280x720", "1200x1920", "1920x1200", "自定义"],
                                        state="readonly", width=15)
        resolution_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        resolution_combo.bind('<<ComboboxSelected>>', self.on_resolution_change)

        # 自定义分辨率输入
        self.custom_resolution_frame = ttk.Frame(self.resolution_frame)
        self.custom_resolution_frame.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))

        ttk.Label(self.custom_resolution_frame, text="宽度:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.width_var = tk.StringVar(value="1080")
        width_entry = ttk.Entry(self.custom_resolution_frame, textvariable=self.width_var, width=8)
        width_entry.grid(row=0, column=1, padx=(0, 10))

        ttk.Label(self.custom_resolution_frame, text="高度:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.height_var = tk.StringVar(value="1920")
        height_entry = ttk.Entry(self.custom_resolution_frame, textvariable=self.height_var, width=8)
        height_entry.grid(row=0, column=3)

        # 分辨率处理方式
        self.resize_method_frame = ttk.Frame(self.resolution_frame)
        self.resize_method_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(10, 0))

        ttk.Label(self.resize_method_frame, text="处理方式:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.resize_method = tk.StringVar(value="stretch")
        ttk.Radiobutton(self.resize_method_frame, text="拉伸适应", variable=self.resize_method,
                        value="stretch").grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Radiobutton(self.resize_method_frame, text="保持比例(裁剪)", variable=self.resize_method,
                        value="crop").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        ttk.Radiobutton(self.resize_method_frame, text="保持比例(填充)", variable=self.resize_method,
                        value="pad").grid(row=0, column=3, sticky=tk.W)

        # 单张图片处理选项
        self.single_frame = ttk.Frame(crop_frame)
        self.single_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        self.save_as_new = tk.BooleanVar(value=True)
        self.save_new_check = ttk.Checkbutton(self.single_frame, text="保存为新文件（而不是覆盖原文件）",
                                              variable=self.save_as_new)
        self.save_new_check.grid(row=0, column=0, sticky=tk.W)

        # 操作按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))

        self.process_btn = ttk.Button(button_frame, text="开始处理", command=self.start_processing,
                                      style="Accent.TButton")
        self.process_btn.grid(row=0, column=0, padx=(0, 10))

        self.stop_btn = ttk.Button(button_frame, text="停止处理", command=self.stop_processing_action,
                                   state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))

        ttk.Button(button_frame, text="清空日志", command=self.clear_log).grid(row=0, column=2)

        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        # 日志输出
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="10")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 初始化界面状态
        self.on_mode_change()
        self.on_resolution_change()  # 初始化分辨率显示

    def on_resolution_change(self, event=None):
        """处理分辨率选择变化"""
        resolution = self.resolution_var.get()
        if resolution == "自定义":
            self.custom_resolution_frame.grid()
        else:
            self.custom_resolution_frame.grid_remove()
            if 'x' in resolution:
                width, height = resolution.split('x')
                self.width_var.set(width)
                self.height_var.set(height)

    def on_mode_change(self):
        """处理模式变化"""
        mode = self.mode_var.get()

        # 隐藏所有特殊设置框架
        self.resolution_frame.grid_remove()
        self.single_frame.grid_remove()
        self.basic_crop_frame.grid_remove()

        if mode == "batch":
            self.input_label.config(text="输入文件夹:")
            self.output_frame.grid()
            self.multi_crop_frame.grid()
            self.process_btn.config(text="开始批量处理")
        elif mode == "single":
            self.input_label.config(text="输入图片文件:")
            self.output_frame.grid_remove()
            self.multi_crop_frame.grid()  # 改为使用多方向裁剪设置
            self.single_frame.grid()
            self.process_btn.config(text="处理图片")
        else:  # resize
            self.input_label.config(text="输入文件夹:")
            self.output_frame.grid()
            self.multi_crop_frame.grid_remove()
            self.resolution_frame.grid()
            self.process_btn.config(text="开始统一分辨率")

        # 清空输入路径
        self.input_path.set("")
        self.output_path.set("")

    def browse_input(self):
        """浏览输入路径"""
        mode = self.mode_var.get()

        if mode == "single":
            # 选择单个文件
            filename = filedialog.askopenfilename(
                title="选择图片文件",
                filetypes=[
                    ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"),
                    ("所有文件", "*.*")
                ]
            )
            if filename:
                self.input_path.set(filename)
        else:
            # 选择文件夹
            folder = filedialog.askdirectory(title="选择输入文件夹")
            if folder:
                self.input_path.set(folder)
                # 自动生成输出路径
                if mode in ["batch", "resize"]:
                    self.generate_output_path()

    def browse_output(self):
        """自定义输出路径"""
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_path.set(folder)

    def generate_output_path(self):
        """自动生成输出路径"""
        input_folder = self.input_path.get()
        if input_folder:
            folder_name = Path(input_folder).name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"{folder_name}_{timestamp}"
            output_path = str(Path(input_folder).parent / output_name)
            self.output_path.set(output_path)

    def log_message(self, message):
        """添加日志消息"""
        self.msg_queue.put(("log", message))

    def check_queue(self):
        """检查消息队列"""
        try:
            while True:
                msg_type, message = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.log_text.insert(tk.END, message + "\n")
                    self.log_text.see(tk.END)
                elif msg_type == "progress_start":
                    self.progress.config(value=0)
                    self.process_btn.config(state="disabled")
                    self.stop_btn.config(state="normal")
                elif msg_type == "progress_update":
                    progress_value = message
                    self.progress.config(value=progress_value)
                elif msg_type == "progress_stop":
                    self.progress.config(value=100)
                    self.process_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                elif msg_type == "ask_open_folder":
                    folder_path = message
                    result = messagebox.askyesno("处理完成", f"处理完成！\n是否打开输出文件夹？\n\n{folder_path}")
                    if result:
                        self.open_folder(folder_path)
                elif msg_type == "error":
                    messagebox.showerror("错误", message)
                elif msg_type == "success":
                    messagebox.showinfo("成功", message)
        except queue.Empty:
            pass

        self.root.after(100, self.check_queue)

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)

    def stop_processing_action(self):
        """停止处理"""
        self.stop_processing.set()
        self.log_message("用户请求停止处理...")
        self.msg_queue.put(("progress_stop", ""))

    def open_folder(self, folder_path):
        """打开文件夹"""
        try:
            if sys.platform.startswith('win'):
                os.startfile(folder_path)
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.run(['open', folder_path])
            else:  # linux
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")

    def start_processing(self):
        """开始处理"""
        mode = self.mode_var.get()
        input_path = self.input_path.get().strip()

        if not input_path:
            messagebox.showwarning("警告", "请先选择输入路径！")
            return

        # 重置停止标志
        self.stop_processing.clear()

        if mode == "batch":
            if not os.path.exists(input_path):
                messagebox.showerror("错误", f"输入文件夹不存在: {input_path}")
                return

            # 获取多方向裁剪参数
            try:
                top_pixels = int(self.top_pixels_var.get())
                bottom_pixels = int(self.bottom_pixels_var.get())
                left_pixels = int(self.left_pixels_var.get())
                right_pixels = int(self.right_pixels_var.get())

                if top_pixels < 0 or bottom_pixels < 0 or left_pixels < 0 or right_pixels < 0:
                    raise ValueError("像素数不能为负数")

                if top_pixels == 0 and bottom_pixels == 0 and left_pixels == 0 and right_pixels == 0:
                    messagebox.showwarning("警告", "请至少设置一个方向的裁剪像素数！")
                    return

            except ValueError as e:
                messagebox.showwarning("警告", f"裁剪像素数无效: {e}")
                return

            output_path = self.output_path.get().strip()
            if not output_path:
                self.generate_output_path()
                output_path = self.output_path.get()

            # 在后台线程中处理
            thread = threading.Thread(target=self.batch_process_thread,
                                      args=(
                                      input_path, output_path, top_pixels, bottom_pixels, left_pixels, right_pixels))
            thread.daemon = True
            thread.start()

        elif mode == "single":
            if not os.path.exists(input_path):
                messagebox.showerror("错误", f"输入文件不存在: {input_path}")
                return

            # 获取多方向裁剪参数
            try:
                top_pixels = int(self.top_pixels_var.get())
                bottom_pixels = int(self.bottom_pixels_var.get())
                left_pixels = int(self.left_pixels_var.get())
                right_pixels = int(self.right_pixels_var.get())

                if top_pixels < 0 or bottom_pixels < 0 or left_pixels < 0 or right_pixels < 0:
                    raise ValueError("像素数不能为负数")

                if top_pixels == 0 and bottom_pixels == 0 and left_pixels == 0 and right_pixels == 0:
                    messagebox.showwarning("警告", "请至少设置一个方向的裁剪像素数！")
                    return

            except ValueError as e:
                messagebox.showwarning("警告", f"裁剪像素数无效: {e}")
                return

            save_as_new = self.save_as_new.get()
            thread = threading.Thread(target=self.single_process_thread,
                                      args=(
                                      input_path, top_pixels, bottom_pixels, left_pixels, right_pixels, save_as_new))
            thread.daemon = True
            thread.start()

        else:  # resize
            if not os.path.exists(input_path):
                messagebox.showerror("错误", f"输入文件夹不存在: {input_path}")
                return

            try:
                width = int(self.width_var.get())
                height = int(self.height_var.get())
                if width <= 0 or height <= 0:
                    raise ValueError("宽度和高度必须大于0")
            except ValueError as e:
                messagebox.showwarning("警告", f"分辨率设置无效: {e}")
                return

            output_path = self.output_path.get().strip()
            if not output_path:
                self.generate_output_path()
                output_path = self.output_path.get()

            resize_method = self.resize_method.get()
            thread = threading.Thread(target=self.resize_process_thread,
                                      args=(input_path, output_path, width, height, resize_method))
            thread.daemon = True
            thread.start()

    def resize_process_thread(self, input_folder, output_folder, target_width, target_height, resize_method):
        """统一分辨率处理线程"""
        self.msg_queue.put(("progress_start", ""))
        self.msg_queue.put(("log", f"开始统一分辨率..."))
        self.msg_queue.put(("log", f"输入文件夹: {input_folder}"))
        self.msg_queue.put(("log", f"输出文件夹: {output_folder}"))
        self.msg_queue.put(("log", f"目标分辨率: {target_width}x{target_height}"))
        self.msg_queue.put(("log", f"处理方式: {resize_method}"))
        self.msg_queue.put(("log", "-" * 50))

        try:
            success_count, total_count = self.batch_resize_images(
                input_folder, output_folder, target_width, target_height, resize_method)

            if self.stop_processing.is_set():
                self.msg_queue.put(("log", "=" * 50))
                self.msg_queue.put(("log", f"处理已被用户停止！"))
                self.msg_queue.put(("log", f"已处理: {success_count} 张图片"))
            else:
                self.msg_queue.put(("log", "=" * 50))
                self.msg_queue.put(("log", f"统一分辨率完成！"))
                self.msg_queue.put(("log", f"总共处理: {total_count} 张图片"))
                self.msg_queue.put(("log", f"成功处理: {success_count} 张图片"))
                self.msg_queue.put(("log", f"失败: {total_count - success_count} 张图片"))
                self.msg_queue.put(("log", f"输出文件夹: {output_folder}"))

                # 询问是否打开文件夹
                self.msg_queue.put(("ask_open_folder", output_folder))

        except Exception as e:
            self.msg_queue.put(("log", f"处理过程中出现错误: {e}"))
            self.msg_queue.put(("error", f"处理失败: {e}"))

        finally:
            self.msg_queue.put(("progress_stop", ""))

    def batch_process_thread(self, input_folder, output_folder, top_pixels, bottom_pixels, left_pixels, right_pixels):
        """批量处理线程（多方向裁剪）"""
        self.msg_queue.put(("progress_start", ""))
        self.msg_queue.put(("log", f"开始批量处理..."))
        self.msg_queue.put(("log", f"输入文件夹: {input_folder}"))
        self.msg_queue.put(("log", f"输出文件夹: {output_folder}"))
        self.msg_queue.put(
            ("log", f"裁剪设置: 顶部{top_pixels}px, 底部{bottom_pixels}px, 左侧{left_pixels}px, 右侧{right_pixels}px"))
        self.msg_queue.put(("log", "-" * 50))

        try:
            success_count, total_count = self.batch_crop_images_multi_direction(
                input_folder, output_folder, top_pixels, bottom_pixels, left_pixels, right_pixels)

            if self.stop_processing.is_set():
                self.msg_queue.put(("log", "=" * 50))
                self.msg_queue.put(("log", f"处理已被用户停止！"))
                self.msg_queue.put(("log", f"已处理: {success_count} 张图片"))
            else:
                self.msg_queue.put(("log", "=" * 50))
                self.msg_queue.put(("log", f"批量处理完成！"))
                self.msg_queue.put(("log", f"总共处理: {total_count} 张图片"))
                self.msg_queue.put(("log", f"成功处理: {success_count} 张图片"))
                self.msg_queue.put(("log", f"失败: {total_count - success_count} 张图片"))
                self.msg_queue.put(("log", f"输出文件夹: {output_folder}"))

                # 询问是否打开文件夹
                self.msg_queue.put(("ask_open_folder", output_folder))

        except Exception as e:
            self.msg_queue.put(("log", f"处理过程中出现错误: {e}"))
            self.msg_queue.put(("error", f"处理失败: {e}"))

        finally:
            self.msg_queue.put(("progress_stop", ""))

    def single_process_thread(self, input_path, top_pixels, bottom_pixels, left_pixels, right_pixels, save_as_new):
        """单张图片处理线程"""
        self.msg_queue.put(("progress_start", ""))
        self.msg_queue.put(("log", f"开始处理单张图片..."))
        self.msg_queue.put(("log", f"输入文件: {input_path}"))
        self.msg_queue.put(
            ("log", f"裁剪设置: 顶部{top_pixels}px, 底部{bottom_pixels}px, 左侧{left_pixels}px, 右侧{right_pixels}px"))
        self.msg_queue.put(("log", f"保存方式: {'新文件' if save_as_new else '覆盖原文件'}"))
        self.msg_queue.put(("log", "-" * 50))

        try:
            # 更新进度到50%
            self.msg_queue.put(("progress_update", 50))

            if save_as_new:
                path_obj = Path(input_path)
                output_path = path_obj.parent / f"{path_obj.stem}_cropped{path_obj.suffix}"
            else:
                output_path = input_path

            success = self.crop_multi_direction(input_path, str(output_path), top_pixels, bottom_pixels, left_pixels,
                                                right_pixels)

            # 更新进度到100%
            self.msg_queue.put(("progress_update", 100))

            if success:
                if save_as_new:
                    output_folder = str(path_obj.parent)
                    self.msg_queue.put(("ask_open_folder", output_folder))
                else:
                    self.msg_queue.put(("success", "图片处理成功！"))
            else:
                self.msg_queue.put(("error", "图片处理失败！"))

        except Exception as e:
            self.msg_queue.put(("log", f"处理过程中出现错误: {e}"))
            self.msg_queue.put(("error", f"处理失败: {e}"))

        finally:
            self.msg_queue.put(("progress_stop", ""))

    def resize_image(self, image_path, output_path, target_width, target_height, resize_method):
        """调整图片分辨率"""
        try:
            with Image.open(image_path) as img:
                original_width, original_height = img.size

                if resize_method == "stretch":
                    # 直接拉伸到目标尺寸
                    resized_img = img.resize((target_width, target_height), Image.LANCZOS)

                elif resize_method == "crop":
                    # 保持比例，裁剪多余部分
                    # 计算缩放比例
                    scale_w = target_width / original_width
                    scale_h = target_height / original_height
                    scale = max(scale_w, scale_h)  # 使用较大的缩放比例确保填满

                    # 计算缩放后的尺寸
                    new_width = int(original_width * scale)
                    new_height = int(original_height * scale)

                    # 先缩放
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)

                    # 计算裁剪位置（居中裁剪）
                    left = (new_width - target_width) // 2
                    top = (new_height - target_height) // 2
                    right = left + target_width
                    bottom = top + target_height

                    resized_img = resized_img.crop((left, top, right, bottom))

                else:  # pad
                    # 保持比例，填充黑边
                    # 计算缩放比例
                    scale_w = target_width / original_width
                    scale_h = target_height / original_height
                    scale = min(scale_w, scale_h)  # 使用较小的缩放比例确保完全包含

                    # 计算缩放后的尺寸
                    new_width = int(original_width * scale)
                    new_height = int(original_height * scale)

                    # 先缩放
                    scaled_img = img.resize((new_width, new_height), Image.LANCZOS)

                    # 创建目标尺寸的黑色背景
                    resized_img = Image.new('RGB', (target_width, target_height), (0, 0, 0))

                    # 计算粘贴位置（居中）
                    paste_x = (target_width - new_width) // 2
                    paste_y = (target_height - new_height) // 2

                    resized_img.paste(scaled_img, (paste_x, paste_y))

                resized_img.save(output_path, quality=95)

                method_text = {"stretch": "拉伸", "crop": "裁剪", "pad": "填充"}[resize_method]
                self.msg_queue.put(("log",
                                    f"✓ 成功: {Path(image_path).name} ({original_width}x{original_height}) -> ({target_width}x{target_height}) [{method_text}]"))
                return True

        except Exception as e:
            self.msg_queue.put(("log", f"✗ 失败: {Path(image_path).name} - {e}"))
            return False

    def crop_multi_direction(self, image_path, output_path, top_pixels, bottom_pixels, left_pixels, right_pixels):
        """多方向裁剪图片"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size

                # 检查是否可以裁剪
                if height <= (top_pixels + bottom_pixels):
                    self.msg_queue.put(("log",
                                        f"警告: 图片 {Path(image_path).name} 高度({height}px)不足以裁剪上下共{top_pixels + bottom_pixels}px"))
                    return False

                if width <= (left_pixels + right_pixels):
                    self.msg_queue.put(("log",
                                        f"警告: 图片 {Path(image_path).name} 宽度({width}px)不足以裁剪左右共{left_pixels + right_pixels}px"))
                    return False

                # 计算裁剪区域 (left, top, right, bottom)
                crop_box = (left_pixels, top_pixels, width - right_pixels, height - bottom_pixels)

                cropped_img = img.crop(crop_box)
                cropped_img.save(output_path, quality=95)

                new_width, new_height = cropped_img.size
                crop_info = f"上{top_pixels}下{bottom_pixels}左{left_pixels}右{right_pixels}"
                self.msg_queue.put(("log",
                                    f"✓ 成功: {Path(image_path).name} ({width}x{height}) -> ({new_width}x{new_height}) [{crop_info}]"))
                return True

        except Exception as e:
            self.msg_queue.put(("log", f"✗ 失败: {Path(image_path).name} - {e}"))
            return False

    def batch_crop_images_multi_direction(self, input_folder, output_folder, top_pixels, bottom_pixels, left_pixels,
                                          right_pixels):
        """批量多方向裁剪"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

        Path(output_folder).mkdir(parents=True, exist_ok=True)

        # 首先统计总文件数
        total_files = []
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                file_extension = Path(file).suffix.lower()
                if file_extension in image_extensions:
                    total_files.append(os.path.join(root, file))

        total_count = len(total_files)
        processed_count = 0
        success_count = 0

        self.msg_queue.put(("log", f"找到 {total_count} 张图片需要处理"))

        for input_path in total_files:
            if self.stop_processing.is_set():
                break

            relative_path = os.path.relpath(input_path, input_folder)
            output_path = os.path.join(output_folder, relative_path)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if self.crop_multi_direction(input_path, output_path, top_pixels, bottom_pixels, left_pixels, right_pixels):
                success_count += 1

            processed_count += 1

            # 更新进度条
            progress_percentage = (processed_count / total_count) * 100
            self.msg_queue.put(("progress_update", progress_percentage))

        return success_count, total_count

    def batch_resize_images(self, input_folder, output_folder, target_width, target_height, resize_method):
        """批量调整分辨率"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

        Path(output_folder).mkdir(parents=True, exist_ok=True)

        # 首先统计总文件数
        total_files = []
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                file_extension = Path(file).suffix.lower()
                if file_extension in image_extensions:
                    total_files.append(os.path.join(root, file))

        total_count = len(total_files)
        processed_count = 0
        success_count = 0

        self.msg_queue.put(("log", f"找到 {total_count} 张图片需要处理"))

        for input_path in total_files:
            if self.stop_processing.is_set():
                break

            relative_path = os.path.relpath(input_path, input_folder)
            output_path = os.path.join(output_folder, relative_path)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if self.resize_image(input_path, output_path, target_width, target_height, resize_method):
                success_count += 1

            processed_count += 1

            # 更新进度条
            progress_percentage = (processed_count / total_count) * 100
            self.msg_queue.put(("progress_update", progress_percentage))

        return success_count, total_count

    def crop_bottom_pixels(self, image_path, output_path, pixels_to_crop=30):
        """裁剪图片底部指定像素"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size

                if height <= pixels_to_crop:
                    self.msg_queue.put(
                        ("log", f"警告: 图片 {Path(image_path).name} 高度({height}px)不足以裁剪{pixels_to_crop}px"))
                    return False

                crop_box = (0, 0, width, height - pixels_to_crop)
                cropped_img = img.crop(crop_box)
                cropped_img.save(output_path, quality=95)

                self.msg_queue.put(("log",
                                    f"✓ 成功: {Path(image_path).name} ({width}x{height}) -> ({width}x{height - pixels_to_crop})"))
                return True

        except Exception as e:
            self.msg_queue.put(("log", f"✗ 失败: {Path(image_path).name} - {e}"))
            return False


def main():
    root = tk.Tk()
    app = ImageCropGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
