import math
import os
import shutil
import subprocess
import tempfile
from typing import List, Optional

import cv2
from moviepy.editor import ImageSequenceClip
from PIL import Image

from snaplet.const import (
    DEFAULT_BG_COLOR,
    DEFAULT_FPS,
    DEFAULT_GIF_COLORS,
    DEFAULT_PADDING,
    DEFAULT_THRESHOLD,
    DEFAULT_VIDEO_CODEC,
    DEFAULT_VIDEO_CRF,
    DEFAULT_VIDEO_PRESET,
    DEFAULT_VIDEO_THREADS,
    FFMPEG_CMD,
    PNG_HEADER,
    PNG_IEND,
)


class SnapletManager:
    def __init__(self):
        """
        SnapletManager 初始化类，无状态。
        """
        pass

    def extract_keyframes(
        self,
        video_path: str,
        threshold: float = DEFAULT_THRESHOLD,
        max_frames: Optional[int] = None,
        use_ffmpeg: bool = True,
        verbose: bool = False,
    ) -> List[Image.Image]:
        """
        提取视频关键帧。

        - FFmpeg模式（默认）：提取编码I帧，效率高，阈值参数无效。
        - 分桶采样模式：均匀分布采样，阈值参数无效。
        - 基于帧差异的传统算法：阈值参数生效。

        :param video_path: 视频文件路径。
        :param threshold: 帧间差异阈值，仅基于帧差异算法生效。
        :param max_frames: 最大提取帧数。
        :param use_ffmpeg: 是否使用FFmpeg模式。
        :param verbose: 是否打印日志。
        :return: 关键帧PIL图片列表。
        """
        if use_ffmpeg:
            try:
                return self._extract_keyframes_ffmpeg(video_path, max_frames, verbose)
            except Exception as e:
                if verbose:
                    print(f"[WARN] FFmpeg提取失败，切换分桶采样模式: {e}")

        if max_frames is not None:
            return self._extract_keyframes_bucket_sampling(video_path, max_frames, verbose=verbose)

        return self._extract_keyframes_frame_diff(video_path, threshold, verbose)

    def _extract_keyframes_ffmpeg(self, video_path: str, max_frames: Optional[int], verbose: bool) -> List[Image.Image]:
        """
        使用FFmpeg提取视频编码中的I帧（关键帧）。

        注意：
            I帧分布由编码器决定，可能不均匀，通常集中在场景切换处。
            本方法提取所有I帧后，调用方应自行均匀采样以避免帧集中。

        :param video_path: 视频路径。
        :param max_frames: 最大帧数限制。
        :param verbose: 是否打印日志。
        :return: 关键帧列表。
        :raises RuntimeError: FFmpeg未安装或不可用。
        """
        import io
        import shutil

        if not shutil.which(FFMPEG_CMD):
            raise RuntimeError("FFmpeg 未安装或未加入系统PATH")

        if verbose:
            print(f"[FFmpeg] 提取关键帧，最大帧数: {max_frames or '无限制'}")

        cmd = [
            FFMPEG_CMD,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            video_path,
            "-vf",
            "select=eq(pict_type\\,I)",
            "-vsync",
            "0",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if verbose else subprocess.DEVNULL,
            bufsize=10**8,
        )

        keyframes = []
        frame_count = 0

        buffer = b""

        try:
            while True:
                if max_frames is not None and frame_count >= max_frames:
                    break

                data = process.stdout.read(4096)
                if not data:
                    break
                buffer += data

                while True:
                    start_idx = buffer.find(PNG_HEADER)
                    if start_idx == -1:
                        break
                    iend_idx = buffer.find(PNG_IEND, start_idx)
                    if iend_idx == -1 or iend_idx + 8 > len(buffer):
                        break
                    end_idx = iend_idx + 8
                    png_data = buffer[start_idx:end_idx]
                    buffer = buffer[end_idx:]

                    try:
                        img = Image.open(io.BytesIO(png_data))
                        img.load()
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        keyframes.append(img)
                        frame_count += 1
                        if verbose:
                            print(f"[FFmpeg] 解析关键帧 #{frame_count}")
                    except Exception as e:
                        if verbose:
                            print(f"[FFmpeg] 解析关键帧失败: {e}")
                        continue
        finally:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
            process.wait()

        if verbose:
            print(f"[FFmpeg] 实际提取关键帧数: {len(keyframes)}")
        return keyframes

    def _extract_keyframes_bucket_sampling(self, video_path: str, max_frames: int, verbose: bool) -> List[Image.Image]:
        """
        分桶采样算法：

        将视频均分为max_frames个桶，每桶保留差异最大的帧。

        :param video_path: 视频路径。
        :param max_frames: 最大帧数。
        :param verbose: 是否打印日志。
        :return: 关键帧列表。
        """
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        buckets = [{"max_diff": -1, "frame": None} for _ in range(max_frames)]
        prev_gray = None

        for frame_idx in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is None:
                diff_value = float("inf")
            else:
                diff = cv2.absdiff(gray, prev_gray)
                diff_value = cv2.countNonZero(diff) / diff.size * 100

            bucket_idx = min(frame_idx * max_frames // total_frames, max_frames - 1)

            if diff_value > buckets[bucket_idx]["max_diff"]:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                buckets[bucket_idx] = {"max_diff": diff_value, "frame": img}
                if verbose:
                    print(f"[Bucket] 桶{bucket_idx}更新帧{frame_idx} (差异: {diff_value:.1f}%)")

            prev_gray = gray

        cap.release()
        return [b["frame"] for b in buckets if b["frame"] is not None]

    def _extract_keyframes_frame_diff(
        self,
        video_path: str,
        threshold: float = DEFAULT_THRESHOLD,
        verbose: bool = False,
    ) -> List[Image.Image]:
        """
        基于帧间灰度差异提取关键帧。

        :param video_path: 视频路径。
        :param threshold: 差异阈值百分比。
        :param verbose: 是否打印日志。
        :return: 关键帧列表。
        :raises FileNotFoundError: 视频文件不存在。
        :raises IOError: 视频文件无法打开。
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"无法打开视频文件: {video_path}")

        keyframes = []
        prev_gray = None
        frame_idx = 0
        saved_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if prev_gray is None:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                keyframes.append(img)
                prev_gray = gray
                saved_count += 1
                if verbose:
                    print(f"[FrameDiff] 保存关键帧 #{saved_count} (帧号 {frame_idx})")
            else:
                diff = cv2.absdiff(gray, prev_gray)
                non_zero = cv2.countNonZero(diff)
                mean_diff = non_zero / diff.size * 100

                if mean_diff > threshold:
                    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    keyframes.append(img)
                    prev_gray = gray
                    saved_count += 1
                    if verbose:
                        print(f"[FrameDiff] 保存关键帧 #{saved_count} (帧号 {frame_idx}) 差异: {mean_diff:.2f}%")

            frame_idx += 1

        cap.release()
        if verbose:
            print(f"[FrameDiff] 共提取关键帧: {len(keyframes)} 张")
        return keyframes

    def sample_frames(self, frames: List[Image.Image], sample_count: int) -> List[Image.Image]:
        """
        等间距抽取指定数量帧。

        :param frames: 原始帧列表。
        :param sample_count: 目标帧数。
        :return: 抽样帧列表。
        """
        total = len(frames)
        if sample_count >= total:
            return frames.copy()

        interval = total / sample_count
        sampled = [frames[int(i * interval)] for i in range(sample_count)]
        return sampled

    def concat_images_grid(
        self,
        images: List[Image.Image],
        max_frames: Optional[int] = None,
        padding: int = DEFAULT_PADDING,
        bg_color=DEFAULT_BG_COLOR,
    ) -> Image.Image:
        """
        拼接多张图片成多宫格。

        自动计算行列数，满足 rows * cols >= 图片数量，且 rows <= cols，行列尽量接近。

        :param images: 图片列表。
        :param max_frames: 最大帧数，超出截断。
        :param padding: 图片间距，默认1像素。
        :param bg_color: 背景颜色，RGB三元组。
        :return: 拼接后的图片。
        :raises ValueError: 图片列表为空。
        """
        if not images:
            raise ValueError("图片列表不能为空")

        if max_frames is not None and max_frames > 0:
            images = images[:max_frames]

        total = len(images)

        best_rows, best_cols = None, None
        min_diff = None

        for rows in range(1, total + 1):
            cols = math.ceil(total / rows)
            if rows <= cols:
                diff = cols - rows
                if min_diff is None or diff < min_diff:
                    min_diff = diff
                    best_rows, best_cols = rows, cols
                if diff == 0:
                    break

        rows, cols = best_rows, best_cols

        min_width = min(img.width for img in images)
        min_height = min(img.height for img in images)
        resized_images = [img.resize((min_width, min_height), Image.LANCZOS) for img in images]

        total_width = cols * min_width + padding * (cols - 1)
        total_height = rows * min_height + padding * (rows - 1)

        new_img = Image.new("RGB", (total_width, total_height), bg_color)

        for idx, img in enumerate(resized_images):
            r = idx // cols
            c = idx % cols
            x = c * (min_width + padding)
            y = r * (min_height + padding)
            new_img.paste(img, (x, y))

        return new_img

    def create_gif_from_images(
        self,
        images: List[Image.Image],
        output_path: str,
        fps: int = DEFAULT_FPS,
        loop: bool = True,
        colors: int = DEFAULT_GIF_COLORS,
        verbose: bool = False,
    ) -> None:
        """
        根据图片序列生成GIF。

        :param images: 图片列表。
        :param output_path: 输出路径。
        :param fps: 帧率。
        :param loop: 是否循环播放。
        :param colors: 调色板颜色数。
        :param verbose: 是否打印日志。
        :raises ValueError: 图片列表为空。
        """
        if not images:
            raise ValueError("图片列表不能为空")

        temp_dir = tempfile.mkdtemp(prefix="snaplet_gif_")
        try:
            temp_files = []
            for i, img in enumerate(images):
                p_img = img.convert("P", palette=Image.ADAPTIVE, colors=colors)
                temp_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                p_img.save(temp_path)
                temp_files.append(temp_path)

            clip = ImageSequenceClip(temp_files, fps=fps)
            loop_count = 0 if loop else 1
            clip.write_gif(
                output_path,
                loop=loop_count,
                verbose=verbose,
                program=FFMPEG_CMD,
            )
            if verbose:
                print(f"[GIF] 生成完成: {output_path}")
        finally:
            shutil.rmtree(temp_dir)

    def create_video_from_images(
        self,
        images: List[Image.Image],
        output_path: str,
        fps: int = DEFAULT_FPS,
        size: Optional[tuple] = None,
        codec: str = DEFAULT_VIDEO_CODEC,
        preset: str = DEFAULT_VIDEO_PRESET,
        crf: int = DEFAULT_VIDEO_CRF,
        bitrate: Optional[str] = None,
        audio: bool = False,
        verbose: bool = False,
        threads: int = DEFAULT_VIDEO_THREADS,
    ) -> None:
        """
        根据图片序列生成视频。

        :param images: 图片列表。
        :param output_path: 输出路径。
        :param fps: 帧率。
        :param size: (宽, 高)。
        :param codec: 编码器。
        :param preset: 编码预设。
        :param crf: 质量参数。
        :param bitrate: 比特率，优先级高于crf。
        :param audio: 是否包含音频。
        :param verbose: 是否打印日志。
        :param threads: 编码线程数。
        :raises ValueError: 图片列表为空。
        """
        if not images:
            raise ValueError("图片列表不能为空")

        temp_dir = tempfile.mkdtemp(prefix="snaplet_video_")
        try:
            temp_files = []
            for i, img in enumerate(images):
                if size is not None:
                    img = img.resize(size, Image.Resampling.LANCZOS)
                temp_path = os.path.join(temp_dir, f"frame_{i:05d}.png")
                img.save(temp_path)
                temp_files.append(temp_path)

            clip = ImageSequenceClip(temp_files, fps=fps)

            if size is not None:
                clip = clip.resize(newsize=size)

            ffmpeg_params = [
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-threads",
                str(threads),
            ]

            write_params = dict(
                codec=codec,
                audio=audio,
                verbose=verbose,
                ffmpeg_params=ffmpeg_params,
            )
            if bitrate:
                write_params["bitrate"] = bitrate

            clip.write_videofile(output_path, **write_params)

            if verbose:
                print(f"[视频] 生成完成: {output_path}")
        finally:
            shutil.rmtree(temp_dir)
