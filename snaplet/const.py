# GIF 生成时默认调色板颜色数，颜色越多文件越大，颜色越少质量越差
DEFAULT_GIF_COLORS = 64

# 默认视频编码器，使用 libx264 进行 H.264 编码
DEFAULT_VIDEO_CODEC = "libx264"

# 默认视频编码预设，影响编码速度和压缩率，medium 为平衡选项
DEFAULT_VIDEO_PRESET = "medium"

# 默认视频编码质量参数，CRF 值越小质量越好，文件越大，28 为较高压缩率
DEFAULT_VIDEO_CRF = 28

# 默认视频编码线程数，影响编码速度，通常设置为 CPU 核心数或其倍数
DEFAULT_VIDEO_THREADS = 4

# 默认阈值，可能用于图像处理中的相似度、差异度判断，单位百分比
DEFAULT_THRESHOLD = 80.0

# 默认最大帧数限制，避免处理过多帧导致性能问题
DEFAULT_MAX_FRAMES = 30

# 默认填充大小，可能用于图像边缘扩展，单位像素
DEFAULT_PADDING = 0

# 默认颜色名称，常用于图像填充或背景色，字符串格式
DEFAULT_COLOR = "black"

# 默认背景颜色，RGB 三元组格式，黑色
DEFAULT_BG_COLOR = (0, 0, 0)  # 黑色

# 默认持续时间，单位秒，可能用于 GIF 或视频片段长度
DEFAULT_DURATION = 3.0

# 默认帧率，单位帧每秒，影响视频或 GIF 的流畅度
DEFAULT_FPS = 10

# 默认目标文件大小，单位 MB，可能用于视频压缩目标
DEFAULT_TARGET_SIZE_MB = 5.0
