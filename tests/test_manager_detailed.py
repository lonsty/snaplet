import os
import tempfile
from unittest import mock

import pytest
from PIL import Image

from snaplet.const import DEFAULT_THRESHOLD
from snaplet.snaplet.manager import SnapletManager

TEST_VIDEO = "tests/file_example_mp4_480_1.5mb.mp4"


@pytest.fixture
def manager():
    return SnapletManager()


def test_extract_keyframes_ffmpeg_normal(manager):
    frames = manager._extract_keyframes_ffmpeg(TEST_VIDEO, max_frames=3, verbose=False)
    assert isinstance(frames, list)
    assert all(isinstance(f, Image.Image) for f in frames)
    assert len(frames) <= 3


def test_extract_keyframes_ffmpeg_fail_fallback(manager):
    # 模拟ffprobe失败，触发异常
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        with pytest.raises(RuntimeError):
            manager._get_keyframe_timestamps("nonexistent.mp4")


def test_extract_keyframes_bucket_sampling_empty_video(manager):
    # 模拟空视频，cv2.VideoCapture.read返回False
    with mock.patch("cv2.VideoCapture") as mock_cap:
        instance = mock_cap.return_value
        instance.get.return_value = 0
        instance.read.return_value = (False, None)
        frames = manager._extract_keyframes_bucket_sampling("fake.mp4", max_frames=5, verbose=True)
        assert frames == []


def test_extract_keyframes_frame_diff_threshold(manager):
    frames = manager._extract_keyframes_frame_diff(TEST_VIDEO, threshold=0, verbose=False)
    # threshold=0 应该提取所有帧
    assert len(frames) > 0


def test_extract_keyframes_frame_diff_file_not_exist(manager):
    with pytest.raises(FileNotFoundError):
        manager._extract_keyframes_frame_diff("nonexistent.mp4", threshold=DEFAULT_THRESHOLD)


def test_extract_keyframes_frame_diff_cannot_open(manager):
    with mock.patch("cv2.VideoCapture") as mock_cap:
        instance = mock_cap.return_value
        instance.isOpened.return_value = False
        with pytest.raises(IOError):
            manager._extract_keyframes_frame_diff(TEST_VIDEO, threshold=DEFAULT_THRESHOLD)


def test_sample_frames_exact_and_less(manager):
    frames = [Image.new("RGB", (10, 10)) for _ in range(10)]
    sampled = manager.sample_frames(frames, 10)
    assert sampled == frames
    sampled_less = manager.sample_frames(frames, 5)
    assert len(sampled_less) == 5


def test_sample_frames_zero_and_one(manager):
    frames = [Image.new("RGB", (10, 10)) for _ in range(3)]
    sampled_zero = manager.sample_frames(frames, 0)
    assert sampled_zero == frames  # sample_count=0 视为不抽样
    sampled_one = manager.sample_frames(frames, 1)
    assert len(sampled_one) == 1


def test_concat_images_grid_empty_list(manager):
    with pytest.raises(ValueError):
        manager.concat_images_grid([])


def test_concat_images_grid_padding_and_bgcolor(manager):
    imgs = [Image.new("RGB", (20, 20), (i * 10, i * 10, i * 10)) for i in range(4)]
    img = manager.concat_images_grid(imgs, padding=5, bg_color=(255, 255, 255))
    assert img.width > 20
    assert img.height > 20


def test_create_gif_from_images_empty(manager):
    with pytest.raises(ValueError):
        manager.create_gif_from_images([], "out.gif")


def test_create_gif_from_images_file_created(manager):
    imgs = [Image.new("RGB", (30, 30), (i * 20, i * 20, i * 20)) for i in range(3)]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "out.gif")
        manager.create_gif_from_images(imgs, out_path, fps=5, loop=False, colors=16, verbose=True)
        assert os.path.isfile(out_path)
        assert os.path.getsize(out_path) > 0


def test_create_video_from_images_empty(manager):
    with pytest.raises(ValueError):
        manager.create_video_from_images([], "out.mp4")


def test_create_video_from_images_file_created(manager):
    imgs = [Image.new("RGB", (64, 64), (i * 20, i * 20, i * 20)) for i in range(3)]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "out.mp4")
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


def test_create_video_from_images_with_bitrate(manager):
    imgs = [Image.new("RGB", (64, 64)) for _ in range(2)]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "out_bitrate.mp4")
        manager.create_video_from_images(
            imgs,
            out_path,
            fps=5,
            size=(64, 64),
            bitrate="500k",
            verbose=False,
        )
        assert os.path.isfile(out_path)
