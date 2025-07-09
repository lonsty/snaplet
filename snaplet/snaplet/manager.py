import math
import os
import shutil
import tempfile
from typing import List, Optional

import cv2
from moviepy.editor import ImageSequenceClip
from PIL import Image


class SnapletManager:
    def __init__(self):
        """
        SnapletManager 初始化类，暂时无状态变量。
        """
        pass

    def extract_keyframes(
        self,
        video_path: str,
        threshold: float = 30.0,
        verbose: bool = False,
    ) -> List[Image.Image]:
        """
        从视频中提取关键帧，返回PIL图片列表。

        通过计算相邻帧灰度图的差异，判断是否为关键帧。
        差异超过阈值则认为是关键帧。

        :param video_path: 输入视频路径
        :param threshold: 关键帧差异阈值，百分比，越大提取帧越少
        :param verbose: 是否打印详细信息
        :return: 关键帧PIL图片列表
        :raises FileNotFoundError: 视频文件不存在时抛出
        :raises IOError: 视频文件无法打开时抛出
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"无法打开视频文件: {video_path}")

        keyframes = []
        prev_frame_gray = None
        frame_idx = 0
        saved_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 转为灰度图，便于计算差异
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if prev_frame_gray is None:
                # 第一帧直接保存
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                keyframes.append(img)
                prev_frame_gray = gray
                saved_idx += 1
                if verbose:
                    print(f"保存关键帧 #{saved_idx} (帧号 {frame_idx})")
            else:
                # 计算当前帧与上一关键帧的差异
                diff = cv2.absdiff(gray, prev_frame_gray)
                non_zero_count = cv2.countNonZero(diff)
                mean_diff = non_zero_count / diff.size * 100  # 百分比差异

                if mean_diff > threshold:
                    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    keyframes.append(img)
                    prev_frame_gray = gray
                    saved_idx += 1
                    if verbose:
                        print(f"保存关键帧 #{saved_idx} (帧号 {frame_idx}) 差异: {mean_diff:.2f}%")

            frame_idx += 1

        cap.release()
        if verbose:
            print(f"共提取关键帧: {len(keyframes)} 张")
        return keyframes

    def sample_frames(self, frames: List[Image.Image], sample_count: int) -> List[Image.Image]:
        """
        从完整帧列表中等间距抽取指定数量的帧。

        如果请求的帧数大于等于总帧数，则返回全部帧的副本。

        :param frames: 完整帧列表
        :param sample_count: 需要抽取的帧数
        :return: 抽取后的帧列表
        """
        total = len(frames)
        if sample_count >= total:
            return frames.copy()

        interval = total / sample_count
        sampled = []
        for i in range(sample_count):
            idx = int(i * interval)
            sampled.append(frames[idx])
        return sampled

    def concat_images_horizontally(self, images: List[Image.Image]) -> Image.Image:
        """
        将多张PIL图片水平拼接成一张大图。

        会将所有图片等比例缩放到最大高度一致。

        :param images: PIL图片列表
        :return: 拼接后的PIL图片
        :raises ValueError: 图片列表为空时抛出
        """
        if not images:
            raise ValueError("图片列表不能为空")

        max_height = max(img.height for img in images)
        resized_images = []
        for img in images:
            if img.height != max_height:
                ratio = max_height / img.height
                new_width = int(img.width * ratio)
                resized = img.resize((new_width, max_height), Image.LANCZOS)
                resized_images.append(resized)
            else:
                resized_images.append(img)

        total_width = sum(img.width for img in resized_images)
        new_img = Image.new("RGB", (total_width, max_height))

        x_offset = 0
        for img in resized_images:
            new_img.paste(img, (x_offset, 0))
            x_offset += img.width

        return new_img

    def concat_images_grid(
        self,
        images: List[Image.Image],
        rows: Optional[int] = 5,
        cols: Optional[int] = 5,
        max_frames: Optional[int] = None,
        padding: int = 5,
        bg_color=(255, 255, 255),
    ) -> Image.Image:
        """
        将多张图片拼接成多宫格。

        支持指定行数或列数，自动计算另一维度。
        支持最大帧数限制，超出部分截断。
        图片会缩放到最小宽高一致，保证整齐排列。

        :param images: PIL图片列表
        :param rows: 指定行数（优先）
        :param cols: 指定列数（次之）
        :param max_frames: 最大提取帧数，超过截断
        :param padding: 图片间距，默认5像素
        :param bg_color: 背景颜色，默认白色
        :return: 拼接后的PIL图片
        :raises ValueError: 图片列表为空时抛出
        """
        if not images:
            raise ValueError("图片列表不能为空")

        if max_frames is not None and max_frames > 0:
            images = images[:max_frames]

        total = len(images)

        # 自动计算行列数
        if rows is None and cols is None:
            cols = int(math.ceil(math.sqrt(total)))
            rows = int(math.ceil(total / cols))
        elif rows is not None and cols is None:
            cols = int(math.ceil(total / rows))
        elif cols is not None and rows is None:
            rows = int(math.ceil(total / cols))

        max_cells = rows * cols
        if total > max_cells:
            images = images[:max_cells]
            total = max_cells

        # 统一缩放到最小宽高，保证整齐
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
        fps: int = 10,
        loop: bool = True,
        optimize: bool = True,  # 保留参数，方便未来扩展
        colors: int = 64,
        verbose: bool = False,
    ) -> None:
        """
        根据PIL图片序列生成GIF。

        通过将图片转换为调色板模式减少颜色数，减小GIF体积。
        使用moviepy调用ffmpeg生成GIF，稳定且支持循环。

        :param images: PIL图片列表
        :param output_path: 输出GIF路径
        :param fps: 帧率，默认10
        :param loop: 是否循环播放，True表示无限循环
        :param optimize: 是否启用优化（当前未实现，仅保留参数）
        :param colors: 调色板颜色数，默认64色
        :param verbose: 是否打印详细信息
        :raises ValueError: 图片列表为空时抛出
        """
        if not images:
            raise ValueError("图片列表不能为空")

        temp_dir = tempfile.mkdtemp(prefix="snaplet_gif_")
        try:
            temp_files = []
            for i, img in enumerate(images):
                # 转为P模式减少颜色数，减小GIF体积
                p_img = img.convert("P", palette=Image.ADAPTIVE, colors=colors)
                temp_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                p_img.save(temp_path)
                temp_files.append(temp_path)

            clip = ImageSequenceClip(temp_files, fps=fps)

            loop_count = 0 if loop else 1  # 0表示无限循环，1表示播放一次
            clip.write_gif(
                output_path,
                loop=loop_count,
                verbose=verbose,
                program="ffmpeg",  # moviepy默认用imageio，ffmpeg更稳定
            )
            if verbose:
                print(f"[GIF] 生成完成: {output_path}")
        finally:
            shutil.rmtree(temp_dir)

    def create_video_from_images(
        self,
        images: List[Image.Image],
        output_path: str,
        fps: int = 10,
        size: Optional[tuple] = None,
        codec: str = "libx264",
        preset: str = "medium",
        crf: int = 28,
        bitrate: Optional[str] = None,
        audio: bool = False,
        verbose: bool = False,
        threads: int = 4,
    ) -> None:
        """
        根据PIL图片序列生成视频。

        使用moviepy调用ffmpeg编码，支持调整分辨率、编码参数。

        :param images: PIL图片列表
        :param output_path: 输出视频路径
        :param fps: 帧率，默认10
        :param size: (width, height)，默认使用图片尺寸
        :param codec: 视频编码器，默认libx264
        :param preset: 编码预设，默认medium，影响编码速度和压缩率
        :param crf: 视频质量参数，0-51，越小质量越好，默认28
        :param bitrate: 比特率，如 "5000k"，优先级高于crf
        :param audio: 是否包含音频，默认False
        :param verbose: 是否打印详细信息
        :param threads: 编码线程数，默认4
        :raises ValueError: 图片列表为空时抛出
        """
        if not images:
            raise ValueError("图片列表不能为空")

        temp_dir = tempfile.mkdtemp(prefix="snaplet_video_")
        try:
            temp_files = []
            for i, img in enumerate(images):
                # 调整尺寸
                if size is not None:
                    img = img.resize(size, Image.Resampling.LANCZOS)
                temp_path = os.path.join(temp_dir, f"frame_{i:05d}.png")
                img.save(temp_path)
                temp_files.append(temp_path)

            clip = ImageSequenceClip(temp_files, fps=fps)

            # clip.resize 也可以调整尺寸，冗余但安全
            if size is not None:
                clip = clip.resize(newsize=size)

            # ffmpeg参数，传递给ffmpeg编码器
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
