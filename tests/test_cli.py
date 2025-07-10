import pytest
from typer.testing import CliRunner

from snaplet.cli import app

runner = CliRunner()
TEST_VIDEO = "tests/file_example_mp4_480_1.5mb.mp4"


def test_extract_command():
    result = runner.invoke(app, ["extract", TEST_VIDEO, "--max-frames", "3", "--verbose"])
    assert result.exit_code == 0
    assert "[SUCCESS]" in result.output or "[WARN]" in result.output


def test_clip_command_gif():
    result = runner.invoke(app, ["clip", TEST_VIDEO, "--duration", "1", "--fps", "5", "--gif", "--verbose"])
    assert result.exit_code == 0
    assert "[SUCCESS]" in result.output


def test_clip_command_video():
    result = runner.invoke(app, ["clip", TEST_VIDEO, "--duration", "1", "--fps", "5", "--verbose"])
    assert result.exit_code == 0
    assert "[SUCCESS]" in result.output
