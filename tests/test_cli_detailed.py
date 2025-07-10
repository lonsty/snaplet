from typer.testing import CliRunner

from snaplet.cli import app

runner = CliRunner()
TEST_VIDEO = "tests/file_example_mp4_480_1.5mb.mp4"


def test_extract_basic():
    result = runner.invoke(app, ["extract", TEST_VIDEO])
    assert result.exit_code == 0
    assert "[SUCCESS]" in result.output or "[WARN]" in result.output


def test_extract_with_options():
    result = runner.invoke(
        app,
        [
            "extract",
            TEST_VIDEO,
            "--max-frames",
            "2",
            "--threshold",
            "10",
            "--padding",
            "5",
            "--bg-color",
            "white",
            "--verbose",
        ],
    )
    assert result.exit_code == 0
    assert "[INFO]" in result.output


def test_extract_invalid_video():
    result = runner.invoke(app, ["extract", "nonexistent.mp4"])
    assert result.exit_code != 0
    assert "[ERROR]" in result.output


def test_clip_basic_video():
    result = runner.invoke(app, ["clip", TEST_VIDEO, "--duration", "1", "--fps", "5"])
    assert result.exit_code == 0
    assert "[SUCCESS]" in result.output


def test_clip_basic_gif():
    result = runner.invoke(app, ["clip", TEST_VIDEO, "--duration", "1", "--fps", "5", "--gif", "--loop", "--verbose"])
    assert result.exit_code == 0
    assert "[SUCCESS]" in result.output


def test_clip_with_size():
    result = runner.invoke(app, ["clip", TEST_VIDEO, "--width", "320", "--height", "240"])
    assert result.exit_code == 0
    assert "[SUCCESS]" in result.output


def test_clip_invalid_video():
    result = runner.invoke(app, ["clip", "nonexistent.mp4"])
    assert result.exit_code != 0
    assert "[ERROR]" in result.output


def test_clip_target_size_small():
    result = runner.invoke(app, ["clip", TEST_VIDEO, "--target-size", "0.1"])
    assert result.exit_code == 0
    assert "[SUCCESS]" in result.output
