import os
import json
import cv2
import subprocess
from pathlib import Path
import sys
import tempfile
import shutil


class VideoProcessor:
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"  # 如果ffmpeg不在PATH中，请修改为完整路径

    def check_ffmpeg(self):
        """检查ffmpeg是否可用"""
        try:
            result = subprocess.run([self.ffmpeg_path, "-version"],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                print("✓ FFmpeg 检测成功")
                return True
        except FileNotFoundError:
            print("✗ FFmpeg 未找到，请安装FFmpeg并添加到系统PATH")
            print("下载地址: https://ffmpeg.org/download.html")
            return False
        except Exception as e:
            print(f"✗ FFmpeg 检测失败: {e}")
            return False

    def download_default_font(self):
        """下载默认中文字体"""
        try:
            import urllib.request

            # 创建字体目录
            font_dir = Path("fonts")
            font_dir.mkdir(exist_ok=True)

            font_path = font_dir / "NotoSansCJK-Regular.ttc"

            if not font_path.exists():
                print("正在下载中文字体...")
                # 使用Google Noto字体
                font_url = "https://github.com/googlefonts/noto-cjk/releases/download/Sans2.004/NotoSansCJK-Regular.ttc"
                urllib.request.urlretrieve(font_url, font_path)
                print(f"字体下载完成: {font_path}")

            return str(font_path)

        except Exception as e:
            print(f"下载字体失败: {e}")
            return None

    def find_system_font(self):
        """查找系统中的中文字体"""
        possible_fonts = []

        # Windows常见中文字体路径
        if sys.platform.startswith('win'):
            windows_fonts = [
                "C:/Windows/Fonts/simhei.ttf",  # 黑体
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                "C:/Windows/Fonts/simkai.ttf",  # 楷体
                "C:/Windows/Fonts/simfang.ttf",  # 仿宋
            ]
            possible_fonts.extend(windows_fonts)

        # macOS常见中文字体
        elif sys.platform == 'darwin':
            mac_fonts = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Unicode MS.ttf",
            ]
            possible_fonts.extend(mac_fonts)

        # Linux常见中文字体
        else:
            linux_fonts = [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/arphic/uming.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ]
            possible_fonts.extend(linux_fonts)

        # 查找存在的字体
        for font_path in possible_fonts:
            if os.path.exists(font_path):
                print(f"找到系统字体: {font_path}")
                return font_path

        return None

    def prepare_font(self, custom_font_path=None):
        """准备字体文件"""
        if custom_font_path and os.path.exists(custom_font_path):
            print(f"使用指定字体: {custom_font_path}")
            return custom_font_path

        # 查找系统字体
        system_font = self.find_system_font()
        if system_font:
            return system_font

        # 下载默认字体
        print("未找到系统中文字体，尝试下载默认字体...")
        downloaded_font = self.download_default_font()
        if downloaded_font:
            return downloaded_font

        print("警告: 未找到合适的中文字体，可能会出现乱码")
        return None

    def create_subtitle_file(self, text, duration, output_path):
        """
        创建SRT字幕文件

        Args:
            text (str): 字幕文本
            duration (float): 视频时长
            output_path (str): SRT文件输出路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("1\n")
                f.write("00:00:00,000 --> ")

                # 转换时长为时间格式
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                milliseconds = int((duration % 1) * 1000)

                f.write(f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}\n")
                f.write(f"{text}\n")

            return True
        except Exception as e:
            print(f"创建字幕文件失败: {e}")
            return False

    def get_video_duration(self, video_path):
        """获取视频时长"""
        try:
            cmd = [
                self.ffmpeg_path, "-i", video_path,
                "-hide_banner", "-f", "null", "-"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # 从stderr中解析时长
            import re
            duration_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', result.stderr)
            if duration_match:
                hours, minutes, seconds = duration_match.groups()
                total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                return total_seconds

            return 10.0  # 默认10秒

        except Exception as e:
            print(f"获取视频时长失败: {e}")
            return 10.0

    def convert_to_h264_aac(self, input_path, output_path, text_overlay=None):
        """
        将视频转换为1080x1920 H.264+AAC格式，并添加中文文字

        Args:
            input_path (str): 输入视频路径
            output_path (str): 输出视频路径
            text_overlay (dict): 文字叠加配置

        Returns:
            bool: 是否成功
        """
        try:
            print(f"开始转换: {Path(input_path).name}")

            # 基础转换命令
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-r", "30",
                "-y"  # 覆盖输出文件
            ]

            # 如果有文字叠加配置
            if text_overlay:
                # 方法1: 使用字幕文件 (推荐，支持中文最好)
                if text_overlay.get('use_subtitle', True):
                    success = self.add_text_with_subtitle(input_path, output_path, text_overlay)
                    return success

                # 方法2: 使用drawtext filter
                else:
                    video_filter = self.build_text_filter(text_overlay)
                    if video_filter:
                        vf_index = cmd.index("-vf")
                        cmd[vf_index + 1] = video_filter

            cmd.append(output_path)

            print(f"执行命令: {' '.join(cmd)}")

            # 执行转换
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode == 0:
                print(f"✓ 转换成功: {output_path}")
                return True
            else:
                print(f"✗ 转换失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"✗ 转换异常: {e}")
            return False

    def add_text_with_subtitle(self, input_path, output_path, text_config):
        """
        使用字幕文件方式添加文字 (最佳中文支持)

        Args:
            input_path (str): 输入视频路径
            output_path (str): 输出视频路径
            text_config (dict): 文字配置
        """
        temp_dir = None
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            subtitle_file = os.path.join(temp_dir, "subtitle.srt")

            # 获取视频时长
            duration = self.get_video_duration(input_path)

            # 创建字幕文件
            text = text_config.get("text", "固定机位,安全拍摄")
            if not self.create_subtitle_file(text, duration, subtitle_file):
                return False

            # 准备字体
            font_path = self.prepare_font(text_config.get("font_file"))

            # 构建subtitle filter
            subtitle_filter = f"subtitles={subtitle_file}"

            if font_path:
                # 转换Windows路径格式
                font_path_escaped = font_path.replace("\\", "/").replace(":", "\\:")
                subtitle_filter += f":fontsdir='{os.path.dirname(font_path_escaped)}'"
                subtitle_filter += f":force_style='FontName={Path(font_path).stem}'"

            # 添加样式
            font_size = text_config.get("font_size", 40)
            font_color = text_config.get("font_color", "white").replace("#", "&H")

            style_config = [
                f"FontSize={font_size}",
                f"PrimaryColour={font_color}",
                "Bold=1",
                "Outline=2",
                "OutlineColour=&H000000",
                "Shadow=1",
                "BackColour=&H80000000"
            ]

            subtitle_filter += f":force_style='{','.join(style_config)}'"

            # 完整的video filter
            full_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{subtitle_filter}"

            # 执行命令
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-vf", full_filter,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-r", "30",
                "-y",
                output_path
            ]

            print(f"使用字幕方式添加文字: {text}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode == 0:
                print(f"✓ 字幕添加成功")
                return True
            else:
                print(f"✗ 字幕添加失败: {result.stderr}")
                # fallback to drawtext method
                return self.add_text_with_drawtext(input_path, output_path, text_config)

        except Exception as e:
            print(f"字幕方式失败: {e}")
            # fallback to drawtext method
            return self.add_text_with_drawtext(input_path, output_path, text_config)

        finally:
            # 清理临时文件
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def add_text_with_drawtext(self, input_path, output_path, text_config):
        """
        使用drawtext filter添加文字 (备用方案)
        """
        try:
            video_filter = self.build_text_filter(text_config)

            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-vf", video_filter,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-r", "30",
                "-y",
                output_path
            ]

            print("使用drawtext方式添加文字")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode == 0:
                print(f"✓ drawtext添加成功")
                return True
            else:
                print(f"✗ drawtext添加失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"drawtext方式失败: {e}")
            return False

    def build_text_filter(self, text_config):
        """
        构建drawtext filter (改进版，更好的中文支持)
        """
        try:
            text = text_config.get("text", "固定机位,安全拍摄")
            x = text_config.get("x", 0)
            y = text_config.get("y", 0)

            # 计算像素位置
            video_width = 1080
            video_height = 1920

            pixel_x = int(x * video_width) if x <= 1 else int(x)
            pixel_y = int(y * video_height) if y <= 1 else int(y)

            # 准备字体
            font_path = self.prepare_font(text_config.get("font_file"))

            font_size = text_config.get("font_size", 40)
            font_color = text_config.get("font_color", "white")

            # 转义特殊字符
            text_escaped = text.replace("'", "\\'").replace(":", "\\:")

            # 构建drawtext filter
            text_filter_parts = [
                f"text='{text_escaped}'",
                f"x={pixel_x}",
                f"y={pixel_y}",
                f"fontsize={font_size}",
                f"fontcolor={font_color}",
                "borderw=2",
                "bordercolor=black",
                "shadowx=2",
                "shadowy=2",
                "shadowcolor=black@0.5"
            ]

            # 添加字体文件
            if font_path:
                font_path_escaped = font_path.replace("\\", "/").replace(":", "\\:")
                text_filter_parts.append(f"fontfile='{font_path_escaped}'")

            text_filter = "drawtext=" + ":".join(text_filter_parts)

            # 完整filter chain
            full_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{text_filter}"

            return full_filter

        except Exception as e:
            print(f"构建text filter失败: {e}")
            return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    def get_video_info(self, video_path):
        """获取视频信息"""
        try:
            cmd = [
                self.ffmpeg_path, "-i", video_path,
                "-hide_banner"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            info = result.stderr

            import re
            resolution_match = re.search(r'(\d+)x(\d+)', info)
            if resolution_match:
                width, height = resolution_match.groups()
                return {
                    'width': int(width),
                    'height': int(height),
                    'info': info
                }

            return None

        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return None

    def batch_process(self, input_folder, output_folder, text_config=None):
        """批量处理视频"""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v'}

        Path(output_folder).mkdir(parents=True, exist_ok=True)

        processed_count = 0
        success_count = 0

        for root, dirs, files in os.walk(input_folder):
            for file in files:
                file_extension = Path(file).suffix.lower()
                if file_extension in video_extensions:
                    input_path = os.path.join(root, file)

                    base_name = Path(file).stem
                    output_filename = f"{base_name}_1080x1920_h264.mp4"
                    output_path = os.path.join(output_folder, output_filename)

                    print(f"\n--- 处理第 {processed_count + 1} 个视频 ---")
                    print(f"输入: {file}")

                    video_info = self.get_video_info(input_path)
                    if video_info:
                        print(f"原始分辨率: {video_info['width']}x{video_info['height']}")

                    if self.convert_to_h264_aac(input_path, output_path, text_config):
                        success_count += 1

                    processed_count += 1

        print(f"\n批量处理完成!")
        print(f"总共处理: {processed_count} 个视频")
        print(f"成功转换: {success_count} 个视频")
        print(f"转换失败: {processed_count - success_count} 个视频")
        print(f"输出文件夹: {output_folder}")


def main():
    """主函数"""
    print("视频批量转换工具 (H.264+AAC + 中文文字支持)")
    print("=" * 60)

    processor = VideoProcessor()

    if not processor.check_ffmpeg():
        return

    print("\n请选择模式:")
    print("1. 批量转换视频 (只转换格式)")
    print("2. 批量转换视频 + 添加中文文字")
    print("3. 批量转换视频 + 从JSON配置添加文字")

    choice = input("请输入选择 (1/2/3): ").strip()

    input_folder = input("请输入输入视频文件夹路径: ").strip().strip('"')
    output_folder = input("请输入输出视频文件夹路径: ").strip().strip('"')

    if not os.path.exists(input_folder):
        print(f"错误：输入文件夹 '{input_folder}' 不存在！")
        return

    text_config = None

    if choice == "2":
        print("\n配置中文文字叠加:")
        text = input("请输入要添加的文字 (默认: 固定机位,安全拍摄): ").strip()
        if not text:
            text = "固定机位,安全拍摄"

        x = float(input("请输入X坐标 (0-1相对坐标，默认0.1): ") or "0.1")
        y = float(input("请输入Y坐标 (0-1相对坐标，默认0.1): ") or "0.1")
        font_size = int(input("请输入字体大小 (默认40): ") or "40")
        font_color = input("请输入字体颜色 (默认white): ").strip() or "white"

        # 字体文件选择
        custom_font = input("请输入自定义字体文件路径 (可选，按Enter跳过): ").strip().strip('"')

        text_config = {
            'text': text,
            'x': x,
            'y': y,
            'width': 1,
            'height': 1,
            'font_size': font_size,
            'font_color': font_color,
            'font_file': custom_font if custom_font else None,
            'use_subtitle': True  # 优先使用字幕方式
        }

    elif choice == "3":
        json_path = input("请输入JSON配置文件路径: ").strip().strip('"')
        if os.path.exists(json_path):
            text_config = load_text_config_from_json(json_path)
            if text_config:
                text_config['use_subtitle'] = True
                print(f"已加载JSON配置: {text_config}")
            else:
                print("JSON配置加载失败，将只进行格式转换")
        else:
            print(f"JSON文件不存在: {json_path}")

    print(f"\n开始批量处理...")
    print(f"输入文件夹: {input_folder}")
    print(f"输出文件夹: {output_folder}")
    print(f"目标格式: 1080x1920 H.264+AAC")
    if text_config:
        print(f"中文文字叠加: {text_config['text']}")
        print(f"字幕模式: {text_config.get('use_subtitle', True)}")

    processor.batch_process(input_folder, output_folder, text_config)


def load_text_config_from_json(json_path):
    """从JSON模板文件加载文字配置"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            template = json.load(f)

        text_effects = []

        if 'VideoTracks' in template:
            for track in template['VideoTracks']:
                if 'VideoTrackClips' in track:
                    for clip in track['VideoTrackClips']:
                        if 'Effects' in clip:
                            for effect in clip['Effects']:
                                if effect.get('Type') == 'Text':
                                    text_config = {
                                        'text': effect.get('Content', '固定机位,安全拍摄'),
                                        'x': clip.get('X', 0),
                                        'y': clip.get('Y', 0),
                                        'width': clip.get('Width', 1),
                                        'height': clip.get('Height', 1),
                                        'font_size': effect.get('FixedFontSize', 40),
                                        'font_color': effect.get('FontColor', '#ffffff'),
                                        'font_file': effect.get('FontUrl', '')
                                    }
                                    text_effects.append(text_config)

        return text_effects[0] if text_effects else None

    except Exception as e:
        print(f"加载JSON配置失败: {e}")
        return None


if __name__ == "__main__":
    main()