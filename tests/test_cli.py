import subprocess
import sys


def test_help():
    result = subprocess.run([sys.executable, "-m", "snaplet.cli", "--help"], capture_output=True, text=True)
    assert "Snaplet - 视频关键帧提取与重组工具" in result.stdout
