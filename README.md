# Snaplet

Snaplet 是一个基于 Python 的视频关键帧提取与重组工具，支持从视频中提取关键帧，生成多宫格拼接图片，以及根据关键帧生成固定时长的视频或 GIF。适合快速预览视频内容、制作动图或短视频剪辑。

---

## 主要功能

- **关键帧提取**：基于帧间灰度差异自动提取视频关键帧  
- **多宫格拼接**：将关键帧等间距抽取后拼接成多宫格图片，方便快速浏览  
- **视频/GIF 生成**：根据关键帧生成固定时长的视频或 GIF，支持自动控制文件大小和分辨率  
- **命令行工具**：基于 Typer 实现，简单易用，支持多种参数配置  

---

## 安装

```bash
pip install snaplet
```

或者从源码安装：

```bash
git clone https://github.com/yourusername/snaplet.git
cd snaplet
pip install .
```

---

## 使用示例

### 1. 提取关键帧并生成多宫格图片

```bash
snaplet extract path/to/video.mp4 --rows 5 --cols 5 -o output_grid.jpg --verbose
```

### 2. 根据关键帧生成固定时长 GIF

```bash
snaplet clip path/to/video.mp4 --duration 5 --fps 12 --gif --loop --target-size 3 -o output.gif --verbose
```

### 3. 根据关键帧生成固定时长视频

```bash
snaplet clip path/to/video.mp4 --duration 10 --fps 15 --width 640 --height 360 -o output.mp4 --verbose
```

---

## 命令行参数说明

### extract

| 参数       | 说明               | 默认值 |
|------------|--------------------|--------|
| video      | 输入视频文件路径   | 必填   |
| --rows     | 拼接图片行数       | 5      |
| --cols     | 拼接图片列数       | 5      |
| -o, --output | 输出拼接图片路径 | 自动生成 |
| --verbose  | 是否打印详细信息   | False  |

### clip

| 参数           | 说明                         | 默认值  |
|----------------|------------------------------|---------|
| video          | 输入视频文件路径             | 必填    |
| --duration     | 输出视频/GIF时长（秒）       | 3.0     |
| --fps          | 输出视频/GIF帧率             | 10      |
| --width        | 输出视频宽度                 | 自动计算 |
| --height       | 输出视频高度                 | 自动计算 |
| -t, --threshold| 关键帧差异阈值               | 30.0    |
| --gif          | 是否输出GIF格式              | False   |
| --loop         | GIF是否循环播放              | True    |
| --target-size  | 目标文件大小（MB）           | 5.0     |
| -o, --output   | 输出视频/GIF路径             | 自动生成 |
| --verbose      | 是否打印详细信息             | False   |

---

## 依赖

- Python 3.7+
- [OpenCV](https://opencv.org/) (`cv2`)
- [Pillow](https://python-pillow.org/)
- [moviepy](https://zulko.github.io/moviepy/)
- [typer](https://typer.tiangolo.com/)

---

## 贡献

欢迎提交 issue 和 pull request，帮助改进 Snaplet。

---

## 许可证

MIT License © 2024 Your Name
