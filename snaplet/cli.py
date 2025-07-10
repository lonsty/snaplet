import os
from typing import Optional

import typer

from snaplet.const import (
    DEFAULT_COLOR,
    DEFAULT_DURATION,
    DEFAULT_FPS,
    DEFAULT_MAX_FRAMES,
    DEFAULT_PADDING,
    DEFAULT_TARGET_SIZE_MB,
    DEFAULT_THRESHOLD,
)
from snaplet.snaplet import SnapletManager
from snaplet.utils import default_output_path, parse_color

app = typer.Typer(help="Snaplet - 视频关键帧提取与重组工具")

manager = SnapletManager()


@app.command("extract")
def extract(
    video_path: str = typer.Argument(..., help="输入视频文件路径"),
    max_frames: int = typer.Option(DEFAULT_MAX_FRAMES, "--max-frames", "-m", min=1, help="最大提取关键帧数，默认30"),
    ffmpeg: bool = typer.Option(True, "--ffmpeg/--no-ffmpeg", help="是否使用FFmpeg模式提取关键帧"),
    threshold: float = typer.Option(
        DEFAULT_THRESHOLD, "--threshold", "-t", min=0.0, help="关键帧差异阈值，仅非FFmpeg模式生效，默认80"
    ),
    output_path: Optional[str] = typer.Option(None, "--output", "-o", help="输出拼接图片路径，默认自动生成"),
    padding: int = typer.Option(DEFAULT_PADDING, "--padding", help="拼接图片间距，默认1像素"),
    bg_color: str = typer.Option(DEFAULT_COLOR, "--bg-color", help="拼接图片背景色，支持颜色名或十六进制，默认黑色"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="打印详细日志"),
) -> None:
    """
    提取视频关键帧，等间距抽取指定数量帧并拼接成多宫格图片。
    """
    try:
        if verbose:
            typer.echo(f"[INFO] 开始提取关键帧，视频: {video_path}, 最大帧数: {max_frames}, 阈值: {threshold}")

        keyframes = manager.extract_keyframes(
            video_path=video_path,
            use_ffmpeg=ffmpeg,
            threshold=threshold,
            max_frames=max_frames,
            verbose=verbose,
        )
        if not keyframes:
            typer.echo("[WARN] 未提取到任何关键帧", err=True)
            raise typer.Exit(code=1)

        if verbose:
            typer.echo(f"[INFO] 实际提取关键帧数: {len(keyframes)}")

        sampled_frames = manager.sample_frames(keyframes, max_frames)

        bg = parse_color(bg_color)

        concat_img = manager.concat_images_grid(
            sampled_frames,
            max_frames=max_frames,
            padding=padding,
            bg_color=bg,
        )

        if output_path is None:
            output_path = default_output_path(video_path, "snaplet", "jpg")

        concat_img.save(output_path)
        typer.echo(f"[SUCCESS] 拼接图片已保存: {os.path.abspath(output_path)}")

    except Exception as e:
        typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(code=1)


@app.command("clip")
def clip(
    video_path: str = typer.Argument(..., help="输入视频文件路径"),
    duration: float = typer.Option(
        DEFAULT_DURATION, "--duration", "-d", min=0.1, help="输出视频/GIF时长（秒），默认3秒"
    ),
    fps: int = typer.Option(DEFAULT_FPS, "--fps", "-f", min=1, help="输出帧率，默认10fps"),
    width: Optional[int] = typer.Option(None, "--width", "-w", min=16, help="输出视频宽度"),
    height: Optional[int] = typer.Option(None, "--height", "-h", min=16, help="输出视频高度"),
    ffmpeg: bool = typer.Option(True, "--ffmpeg/--no-ffmpeg", help="是否使用FFmpeg模式提取关键帧"),
    threshold: float = typer.Option(DEFAULT_THRESHOLD, "--threshold", "-t", min=0.0, help="关键帧差异阈值，默认80"),
    gif: bool = typer.Option(False, "--gif/--no-gif", help="是否输出GIF格式，默认输出视频"),
    loop: bool = typer.Option(True, "--loop/--no-loop", help="GIF是否循环播放，默认循环"),
    target_size_mb: float = typer.Option(
        DEFAULT_TARGET_SIZE_MB, "--target-size", "-s", min=0.1, help="目标文件大小（MB），默认5MB"
    ),
    output_path: Optional[str] = typer.Option(None, "--output", "-o", help="输出视频/GIF路径，默认自动生成"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="打印详细日志"),
) -> None:
    """
    生成固定时长的视频或GIF，自动抽取关键帧并控制文件大小。
    """
    import math

    import cv2
    from PIL import Image

    try:
        if verbose:
            typer.echo(f"[INFO] 开始生成剪辑，视频: {video_path}, 时长: {duration}s, FPS: {fps}")

        target_frame_count = max(1, int(fps * duration))

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            typer.echo(f"[ERROR] 无法打开视频文件: {video_path}", err=True)
            raise typer.Exit(code=1)

        orig_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_duration = frame_count / orig_fps if orig_fps > 0 else 0
        cap.release()

        if verbose:
            typer.echo(f"[INFO] 原视频时长: {orig_duration:.2f}s, 总帧数: {frame_count}, FPS: {orig_fps:.2f}")

        keyframes = manager.extract_keyframes(
            video_path=video_path,
            use_ffmpeg=ffmpeg,
            threshold=threshold,
            max_frames=target_frame_count,
            verbose=verbose,
        )
        if not keyframes:
            typer.echo("[WARN] 未提取到任何关键帧，无法生成视频/GIF", err=True)
            raise typer.Exit(code=1)

        total_keyframes = len(keyframes)
        if verbose:
            typer.echo(f"[INFO] 提取关键帧数: {total_keyframes}")

        if total_keyframes > target_frame_count:
            step = total_keyframes / target_frame_count
            indices = [int(i * step) for i in range(target_frame_count)]
            sampled_frames = [keyframes[i] for i in indices]
        else:
            sampled_frames = keyframes
            target_frame_count = total_keyframes

        if verbose:
            typer.echo(f"[INFO] 目标帧数: {target_frame_count}, 实际抽取帧数: {len(sampled_frames)}")

        orig_w, orig_h = sampled_frames[0].size

        if width is None and height is None:
            width = 640
            height = int(orig_h * width / orig_w)
        elif width is not None and height is None:
            height = int(orig_h * width / orig_w)
        elif height is not None and width is None:
            width = int(orig_w * height / orig_h)

        approx_bytes_per_frame = width * height * 0.1
        max_total_bytes = target_size_mb * 1024 * 1024
        estimated_size = approx_bytes_per_frame * len(sampled_frames)

        if estimated_size > max_total_bytes:
            scale_factor = math.sqrt(max_total_bytes / estimated_size)
            new_width = max(16, int(width * scale_factor))
            new_height = max(16, int(height * scale_factor))
            if verbose:
                typer.echo(
                    f"[INFO] 预计文件过大({estimated_size / 1024 / 1024:.2f}MB)，缩小分辨率 {width}x{height} -> {new_width}x{new_height}"
                )
            width, height = new_width, new_height

        resized_frames = [img.resize((width, height), Image.Resampling.LANCZOS) for img in sampled_frames]

        if output_path is None:
            ext = "gif" if gif else "mp4"
            output_path = default_output_path(video_path, "snaplet", ext)

        if gif:
            manager.create_gif_from_images(
                images=resized_frames,
                output_path=output_path,
                fps=fps,
                loop=loop,
                colors=64,
                verbose=verbose,
            )
        else:
            manager.create_video_from_images(
                images=resized_frames,
                output_path=output_path,
                fps=fps,
                size=(width, height),
                verbose=verbose,
                crf=28,
                preset="fast",
            )

        typer.echo(f"[SUCCESS] 生成完成: {os.path.abspath(output_path)}")

    except Exception as e:
        typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
