import os

def get_all_files(directory):
    """
    递归遍历指定目录，并返回所有文件名
    使用：all_files = list(get_all_files(dir))
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            yield os.path.relpath(os.path.join(root, file), directory)