import os
import subprocess
from pathlib import Path
import argparse

def validate_video_quality(video_quality):
    if not (0 <= video_quality <= 51):
        raise ValueError("视频质量参数无效，必须在 0 到 51 之间")

def validate_video_codec(video_codec):
    if video_codec not in ["hevc_qsv", "h264_qsv"]:
        raise ValueError("视频编码参数无效，仅支持 hevc_qsv 和 h264_qsv")

def ensure_font_file_exists(font_file):
    if not font_file.exists():
        raise FileNotFoundError(f"字体文件不存在：{font_file}")

def ensure_output_directory_exists(output_directory):
    output_directory.mkdir(parents=True, exist_ok=True)

def build_ffmpeg_command(file, output_file_name, escaped_font_file, font_color, font_size, video_codec, video_quality, bitrate):
    ffmpeg_command = [
        "ffmpeg",
        "-hwaccel_output_format", "qsv",
        "-i", str(file),
        "-vf", f"drawtext=fontcolor={font_color}:fontsize={font_size}:fontfile='{escaped_font_file}':text='PINSE.CLUB':"
               f"x='if(eq(mod(n\\,2000)\\,0)\\,rand(0\\,(w-text_w))\\,x)':"
               f"y='if(eq(mod(n\\,2000)\\,0)\\,rand(0\\,(h-text_h))\\,y)':"
               f"enable='lt(mod(n\\,2000)\\,1200)'",
        "-c:v", video_codec,
        "-global_quality", str(video_quality),
        "-c:a", "copy",
        "-y", str(output_file_name)
    ]

    if bitrate:
        crf_index = ffmpeg_command.index("-global_quality")
        if crf_index >= 0:
            ffmpeg_command[crf_index] = "-b:v"
            ffmpeg_command[crf_index + 1] = bitrate

    return ffmpeg_command

def check_video_files(input_directory, video_extensions):
    video_files = []
    for ext in video_extensions:
        video_files.extend(input_directory.rglob(ext))
    return video_files

def main(args):
    # 参数定义
    input_directory = Path(args.input_directory)
    output_directory = Path(args.output_directory)
    output_suffix = args.output_suffix
    video_quality = args.video_quality
    video_codec = args.video_codec
    font_size = args.font_size
    font_color = args.font_color
    font_file = Path(args.font_file)
    bitrate = args.bitrate

    # 验证参数是否合法
    try:
        validate_video_quality(video_quality)
        validate_video_codec(video_codec)
        ensure_font_file_exists(font_file)
        ensure_output_directory_exists(output_directory)
    except (ValueError, FileNotFoundError) as e:
        print(e)
        exit(1)

    # 定义需要处理的视频文件扩展名
    video_extensions = ["*.mp4", "*.avi", "*.mkv", "*.mov", "*.wmv", "*.flv", "*.ts", "*.vob", "*.webm", "*.3gp", "*.m4v", "*.rmvb"]

    # 检查输入目录是否包含视频文件
    video_files = check_video_files(input_directory, video_extensions)
    if not video_files:
        print(f"输入目录 '{input_directory}' 中没有找到任何视频文件")
        exit(1)

    print(f"在输入目录 '{input_directory}' 中找到 {len(video_files)} 个视频文件")

    # 转义字体文件路径中的斜杠
    escaped_font_file = str(font_file).replace('\\', '/')

    # 遍历输入目录中的所有视频文件
    for idx, file in enumerate(video_files, start=1):
        # 获取文件相对于输入目录的相对路径
        relative_path = file.relative_to(input_directory)

        # 构建输出文件名和输出文件的完整路径
        output_file_name = output_directory / relative_path.with_name(f"{relative_path.stem}_{output_suffix}{relative_path.suffix}")

        # 确保输出子目录存在
        output_file_name.parent.mkdir(parents=True, exist_ok=True)

        # 构建 ffmpeg 命令
        ffmpeg_command = build_ffmpeg_command(file, output_file_name, escaped_font_file, font_color, font_size, video_codec, video_quality, bitrate)

        # 输出当前处理文件的信息
        print(f"[{idx}/{len(video_files)}] 正在处理文件: {file} -> {output_file_name}")

        # 执行 ffmpeg 命令
        subprocess.run(ffmpeg_command)
    
    print("所有视频文件处理完成")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量处理视频文件并添加水印")
    parser.add_argument('--input_directory', type=str, default='Input', help='输入目录路径')
    parser.add_argument('--output_directory', type=str, default='Output', help='输出目录路径')
    parser.add_argument('--output_suffix', type=str, default='pinseclub', help='输出文件名后缀')
    parser.add_argument('--video_quality', type=int, default=18, help='视频质量 (0-51)')
    parser.add_argument('--video_codec', type=str, default='hevc_qsv', help='视频编码器 (hevc_qsv, h264_qsv)')
    parser.add_argument('--font_size', type=int, default=30, help='字体大小')
    parser.add_argument('--font_color', type=str, default='white', help='字体颜色')
    parser.add_argument('--font_file', type=str, default='./fonts/SimSun.ttf', help='字体文件路径')
    parser.add_argument('--bitrate', type=str, help='视频比特率')

    args = parser.parse_args()
    main(args)
