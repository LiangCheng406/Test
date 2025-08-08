import os
import whisper
from moviepy.editor import VideoFileClip
from concurrent.futures import ProcessPoolExecutor, as_completed
from openpyxl import Workbook
from tqdm import tqdm
import torch
import multiprocessing as mp
import tempfile
import shutil
from pathlib import Path
import gc
import warnings

warnings.filterwarnings("ignore")


def get_optimal_device(device):
    """自动选择最优设备"""
    if device != "auto":
        return device
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "mps"
    try:
        if torch.version.hip is not None:
            return "cuda"
    except:
        pass
    return "cpu"


def process_single_video(args):
    """子进程执行的视频转录任务"""
    video_path, model_size, device, temp_dir = args

    try:
        filename = os.path.basename(video_path)

        process_temp_dir = os.path.join(temp_dir, f"process_{os.getpid()}")
        os.makedirs(process_temp_dir, exist_ok=True)

        audio_path = os.path.join(process_temp_dir, f"{filename}.wav")

        model = whisper.load_model(model_size, device=device)

        with VideoFileClip(video_path) as clip:
            if clip.audio is not None:
                clip.audio.write_audiofile(
                    audio_path,
                    logger=None,
                    verbose=False
                )
            else:
                return (filename, "错误：视频无音频轨道")

        result = model.transcribe(
            audio_path,
            language='zh',
            fp16=device != "cpu",
            condition_on_previous_text=False,
            temperature=0.0,
            best_of=1,
            beam_size=1,
            patience=1.0,
            suppress_tokens=[-1],
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
            compression_ratio_threshold=2.4,
            word_timestamps=False
        )

        text = result['text'].strip()

        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(process_temp_dir):
            shutil.rmtree(process_temp_dir, ignore_errors=True)

        del model
        gc.collect()

        return (filename, text)

    except Exception as e:
        return (os.path.basename(video_path), f"错误：{str(e)}")


def batch_transcribe_videos(input_folder, output_excel,
                            model_size="large", device="cpu",
                            max_processes=None, chunk_size=None):

    if not os.path.exists(input_folder):
        print(f"❌ 输入文件夹不存在: {input_folder}")
        return

    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm'}
    video_files = [os.path.join(input_folder, f)
                   for f in os.listdir(input_folder)
                   if Path(f).suffix.lower() in video_extensions]

    if not video_files:
        print(f"❌ 文件夹中没有找到视频文件: {input_folder}")
        return

    print(f"📁 找到 {len(video_files)} 个视频文件")

    if max_processes is None:
        max_processes = min(len(video_files), max(1, mp.cpu_count() - 1))

    temp_dir = tempfile.mkdtemp(prefix="video_transcribe_")

    try:
        wb = Workbook()
        ws = wb.active
        ws.append(['视频名称', '识别结果', '文件大小(MB)', '处理状态'])

        process_args = []
        for video_path in video_files:
            process_args.append((video_path, model_size, device, temp_dir))

        print(f"🔄 开始处理，使用 {max_processes} 个进程...")

        with ProcessPoolExecutor(max_workers=max_processes) as executor:
            futures = {executor.submit(process_single_video, args): args[0]
                       for args in process_args}

            for future in tqdm(as_completed(futures),
                               total=len(futures),
                               desc="转录进度",
                               unit="视频"):
                video_path = futures[future]
                try:
                    filename, text = future.result()
                    file_size = os.path.getsize(video_path) / (1024 * 1024)
                    status = "成功" if not text.startswith("错误") else "失败"

                    ws.append([filename, text, round(file_size, 2), status])

                    if status == "成功":
                        print(f"✅ [完成] {filename}")
                    else:
                        print(f"❌ [失败] {filename}: {text}")

                except Exception as e:
                    filename = os.path.basename(video_path)
                    error_msg = f"错误：{str(e)}"
                    ws.append([filename, error_msg, 0, "失败"])
                    print(f"❌ [异常] {filename}: {e}")

        os.makedirs(os.path.dirname(output_excel), exist_ok=True)
        wb.save(output_excel)
        print(f"\n🎉 处理完成！结果保存至: {output_excel}")

        total_files = len(video_files)
        success_count = sum(1 for row in ws.iter_rows(min_row=2) if row[3].value == "成功")
        print(f"📊 处理统计: {success_count}/{total_files} 成功")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    config = {
        "input_folder": r"D:\桌面\加油站素材\实拍\input",
        "output_excel": r"D:\桌面\加油站素材\实拍\output_optimized.xlsx",
        "model_size": "large",
        "device": "auto",
        "max_processes": None,
    }

    config["device"] = get_optimal_device(config["device"])

    print("🚀 优化版视频语音识别工具启动")
    print("=" * 50)
    for key, value in config.items():
        print(f"📝 {key}: {value}")
    print("=" * 50)

    batch_transcribe_videos(**config)


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    main()
