import os


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


def parse_color(color_str: str):
    """
    解析颜色字符串，支持颜色名或十六进制RGB格式，返回RGB三元组。

    :param color_str: 颜色字符串，如 "black", "#000000", "fff"
    :return: (R, G, B)元组
    """
    from PIL import ImageColor

    try:
        return ImageColor.getrgb(color_str)
    except Exception:
        # 默认黑色
        return (0, 0, 0)
