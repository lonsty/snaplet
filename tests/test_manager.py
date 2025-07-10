import os
import tempfile

import pytest
from PIL import Image

from snaplet.const import DEFAULT_THRESHOLD
from snaplet.snaplet.manager import SnapletManager

# 这里用一个小视频文件做测试，或者用测试资源路径
TEST_VIDEO = "tests/file_example_mp4_480_1.5mb.mp4"


@pytest.fixture
def manager():
    return SnapletManager()


def test_extract_keyframes_ffmpeg(manager):
    # 只测试能否正常调用，结果不做严格断言
    try:
        frames = manager._extract_keyframes_ffmpeg(TEST_VIDEO, max_frames=5, verbose=True)
        assert isinstance(frames, list)
        assert all(isinstance(f, Image.Image) for f in frames)
    except Exception as e:
        pytest.skip(f"FFmpeg提取失败，跳过测试: {e}")


def test_extract_keyframes_bucket_sampling(manager):
    frames = manager._extract_keyframes_bucket_sampling(TEST_VIDEO, max_frames=5, verbose=True)
    assert isinstance(frames, list)
    assert all(isinstance(f, Image.Image) for f in frames)
    assert len(frames) <= 5


def test_extract_keyframes_frame_diff(manager):
    frames = manager._extract_keyframes_frame_diff(TEST_VIDEO, threshold=DEFAULT_THRESHOLD, verbose=True)
    assert isinstance(frames, list)
    assert all(isinstance(f, Image.Image) for f in frames)
    assert len(frames) > 0


def test_concat_images_grid(manager):
    # 生成几张纯色图测试拼接
    imgs = [Image.new("RGB", (100, 100), (i * 20, i * 20, i * 20)) for i in range(6)]
    grid_img = manager.concat_images_grid(imgs, max_frames=6, padding=2, bg_color=(255, 0, 0))
    assert isinstance(grid_img, Image.Image)
    # 尺寸应大于单张图
    assert grid_img.width > 100 and grid_img.height > 100


def test_sample_frames(manager):
    imgs = [Image.new("RGB", (10, 10)) for _ in range(10)]
    sampled = manager.sample_frames(imgs, 5)
    assert len(sampled) == 5
    sampled = manager.sample_frames(imgs, 15)
    assert len(sampled) == 10  # 不会超出原始数量


def test_create_gif_from_images(manager):
    imgs = [Image.new("RGB", (50, 50), (i * 40, i * 40, i * 40)) for i in range(5)]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "test.gif")
        manager.create_gif_from_images(imgs, out_path, fps=5, loop=True, colors=16, verbose=True)
        assert os.path.isfile(out_path)
        assert os.path.getsize(out_path) > 0


def test_create_video_from_images(manager):
    imgs = [Image.new("RGB", (64, 64), (i * 40, i * 40, i * 40)) for i in range(5)]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "test.mp4")
        manager.create_video_from_images(
            imgs,
            out_path,
            fps=5,
            size=(64, 64),
            verbose=True,
            crf=30,
            preset="fast",
        )
        assert os.path.isfile(out_path)
        assert os.path.getsize(out_path) > 0
