import os
from typing import Optional

import typer

from snaplet.snaplet.manager import SnapletManager

app = typer.Typer(help="Snaplet - 视频关键帧提取与重组工具")

manager = SnapletManager()


def default_output_path(input_path: str, suffix: str, ext: str) -> str:
    """
    根据输入文件路径生成默认输出路径。

    例如：input.mp4 + suffix='snaplet' + ext='jpg' -> input_snaplet.jpg

    :param input_path: 输入文件路径
    :param suffix: 输出文件名后缀
    :param ext: 输出文件扩展名（不带点）
    :return: 生成的输出文件路径
    """
    base, _ = os.path.splitext(input_path)
    return f"{base}_{suffix}.{ext}"


@app.command("extract")
def extract(
    video: str = typer.Argument(..., help="输入视频文件路径"),
    rows: int = typer.Option(5, "--rows", help="拼接图片行数，默认5"),
    cols: int = typer.Option(5, "--cols", help="拼接图片列数，默认5"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="输出拼接图片路径，默认自动生成"),
    verbose: bool = typer.Option(False, "--verbose/--no-verbose", help="是否打印详细信息"),
):
    """
    提取视频关键帧，等间距抽取 rows*cols 帧并拼接成多宫格图片。

    主要流程：
    1. 提取关键帧
    2. 等间距抽取指定数量帧
    3. 拼接成多宫格图片
    4. 保存输出文件
    """
    try:
        # 1. 提取关键帧
        all_frames = manager.extract_keyframes(video_path=video, verbose=verbose)
        if not all_frames:
            typer.echo("未提取到任何帧", err=True)
            raise typer.Exit(code=1)

        max_frames = rows * cols

        # 2. 等间距抽取 max_frames 帧
        sampled_frames = manager.sample_frames(all_frames, max_frames)

        # 3. 拼接成多宫格图片
        concat_img = manager.concat_images_grid(
            sampled_frames,
            rows=rows,
            cols=cols,
            max_frames=max_frames,
            padding=5,
        )

        # 4. 生成默认输出路径（如果未指定）
        if output is None:
            output = default_output_path(video, "snaplet", "jpg")

        # 5. 保存拼接图片
        concat_img.save(output)
        typer.echo(f"拼接图片已保存: {os.path.abspath(output)}")

    except Exception as e:
        typer.echo(f"错误: {e}", err=True)
        raise typer.Exit(code=1)


@app.command("clip")
def clip(
    video: str = typer.Argument(..., help="输入视频文件路径"),
    duration: float = typer.Option(3.0, "--duration", help="输出视频/GIF时长，单位秒，默认3秒"),
    fps: int = typer.Option(10, "--fps", help="输出视频/GIF帧率，默认10fps"),
    width: Optional[int] = typer.Option(None, "--width", help="输出视频宽度"),
    height: Optional[int] = typer.Option(None, "--height", help="输出视频高度"),
    threshold: float = typer.Option(30.0, "-t", "--threshold", help="关键帧差异阈值，越大提取帧越少"),
    gif: bool = typer.Option(False, "--gif/--no-gif", help="是否输出GIF格式，默认输出视频"),
    loop: bool = typer.Option(True, "--loop/--no-loop", help="GIF是否循环播放，默认循环"),
    target_size_mb: float = typer.Option(5.0, "--target-size", help="目标文件大小，单位MB，默认5MB"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="输出视频/GIF路径，默认自动生成"),
    verbose: bool = typer.Option(False, "--verbose/--no-verbose", help="是否打印详细信息"),
):
    """
    生成固定时长的视频或GIF，自动抽取关键帧并控制文件大小。

    主要流程：
    1. 获取视频原始信息（时长、帧率）
    2. 提取关键帧
    3. 计算目标帧数并等间距抽取
    4. 计算输出分辨率，动态调整以满足目标文件大小
    5. 调整帧尺寸
    6. 生成视频或GIF文件
    """
    import math

    import cv2
    from PIL import Image

    try:
        # 1. 获取原视频时长（秒）和帧率
        cap = cv2.VideoCapture(video)
        if not cap.isOpened():
            typer.echo(f"无法打开视频文件: {video}", err=True)
            raise typer.Exit(code=1)
        orig_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_duration = frame_count / orig_fps if orig_fps > 0 else 0
        cap.release()

        if verbose:
            typer.echo(f"原视频时长: {orig_duration:.2f} 秒, 帧数: {frame_count}, FPS: {orig_fps:.2f}")

        # 2. 提取关键帧
        keyframes = manager.extract_keyframes(video_path=video, threshold=threshold, verbose=verbose)
        if not keyframes:
            typer.echo("未提取到任何关键帧，无法生成视频/GIF", err=True)
            raise typer.Exit(code=1)

        total_keyframes = len(keyframes)
        if verbose:
            typer.echo(f"提取关键帧数: {total_keyframes}")

        # 3. 计算目标帧数
        target_frame_count = max(1, int(fps * duration))

        # 4. 等间距抽取帧
        if total_keyframes > target_frame_count:
            step = total_keyframes / target_frame_count
            indices = [int(i * step) for i in range(target_frame_count)]
            sampled_frames = [keyframes[i] for i in indices]
        else:
            sampled_frames = keyframes
            target_frame_count = total_keyframes  # 实际帧数

        if verbose:
            typer.echo(f"目标帧数: {target_frame_count}, 实际抽取帧数: {len(sampled_frames)}")

        # 5. 计算目标分辨率
        orig_w, orig_h = sampled_frames[0].size
        if width is None and height is None:
            width = 640
            height = int(orig_h * width / orig_w)
        elif width is not None and height is None:
            height = int(orig_h * width / orig_w)
        elif height is not None and width is None:
            width = int(orig_w * height / orig_h)

        # 6. 估算单帧大小（字节），经验值
        approx_bytes_per_frame = width * height * 0.1

        # 7. 根据目标大小和帧数，动态调整分辨率
        max_total_bytes = target_size_mb * 1024 * 1024
        estimated_size = approx_bytes_per_frame * len(sampled_frames)

        if estimated_size > max_total_bytes:
            scale_factor = math.sqrt(max_total_bytes / estimated_size)
            new_width = max(16, int(width * scale_factor))
            new_height = max(16, int(height * scale_factor))
            if verbose:
                typer.echo(
                    f"预计文件过大({estimated_size / 1024 / 1024:.2f}MB)，缩小分辨率 {width}x{height} -> {new_width}x{new_height}"
                )
            width, height = new_width, new_height

        # 8. 调整尺寸
        resized_frames = [img.resize((width, height), Image.Resampling.LANCZOS) for img in sampled_frames]

        # 9. 生成视频/GIF
        if output is None:
            ext = "gif" if gif else "mp4"
            output = default_output_path(video, "snaplet", ext)

        if gif:
            manager.create_gif_from_images(
                images=resized_frames,
                output_path=output,
                fps=fps,
                loop=loop,
                optimize=True,
                colors=64,
                verbose=verbose,
            )
        else:
            manager.create_video_from_images(
                images=resized_frames,
                output_path=output,
                fps=fps,
                size=(width, height),
                verbose=verbose,
                crf=28,
                preset="fast",
            )

        typer.echo(f"生成完成: {os.path.abspath(output)}")

    except Exception as e:
        typer.echo(f"错误: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
