from itertools import groupby
import json
import os

class Span:
    def __init__(self, spanID, operationName, tags, startTIme=None, duration=None):
        self.spanID = spanID
        self.operationName = operationName
        self.startTime = startTIme
        self.duration = duration
        self.tags = tags

def get_all_files(directory):
    """
    递归遍历指定目录，并返回所有文件名
    使用：all_files = list(get_all_files(dir))
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            yield os.path.relpath(os.path.join(root, file), directory)

def dfs_traversal(span, visited_spans, level, span_levels):
    span_id = span["spanID"]

    # 读取追踪数据
    with open(file_path, 'r') as file:
        trace_data = json.load(file)

    # 检查是否已访问
    if span_id in visited_spans:
        return None
    
    # 记录除 references 外的信息
    span_info = span.copy()
    span_info.pop("references", None)
    # print(json.dumps(span_info, indent=2))
     
    # 记录 spanID 和层级信息
    span_levels.append({"spanID": span_id, "level": level, "spanInfo": span_info})

    # 标记为已访问
    visited_spans.add(span_id)

    # 检查是否有子 span
    has_children = span.get("hasChildren", False)
    if not has_children:
        return None

    # 遍历 childSpanIds
    child_span_ids = span.get("childSpanIds", [])
    for child_span_id in child_span_ids:
        child_span = find_span_by_id(trace_data, child_span_id)
        if child_span:
            dfs_traversal(child_span, visited_spans, level + 1, span_levels)

def find_span_by_id(trace_data, span_id):
    for item in trace_data["data"]:
        for span in item["spans"]:
            if span["spanID"] == span_id:
                return span
    return None

def get_span_info(span_id, trace_data):
    for item in trace_data["data"]:
        for span in item["spans"]:
            if span["spanID"] == span_id:
                span_info = span.copy()
                span_info.pop("references", None)
                formatted_span_info = json.dumps(span_info, indent=2)
                print(formatted_span_info)
                return formatted_span_info
    return None

def parse_trace_file(file_path):
    """
    解析 trace 文件（json）
    并按 trace 层级打印 trace ID、方法名和详情
    """
    # 读取追踪数据
    with open(file_path, 'r') as file:
        trace_data = json.load(file)

    # 用于记录已访问的 span
    visited_spans = set()

    # 存储 spanID 和层级信息的列表
    span_levels = []

    # 从根 span 开始进行 DFS 遍历
    for item in trace_data["data"]:
        for span in item["spans"]:
            if not span.get("references"):
                dfs_traversal(span, visited_spans, 0, span_levels)

    # 按层级排序
    span_levels.sort(key=lambda x: x["level"])
    # 每个层级单独作为新的列表
    span_levels = [list(g) for _, g in groupby(span_levels, key=lambda x: x["level"])]
    # 按照 span 的开始时间排序
    for span_level in span_levels:
        span_level.sort(key=lambda x: x["spanInfo"]["startTime"])

    for span_level in span_levels:
        for span in span_level:
            indentation = span["level"] * 4 * ' '
            print(f'{indentation}{span["level"]:<5}{span["spanID"]:<16} {span["spanInfo"]["operationName"]:<50} {span["spanInfo"]["startTime"]:<60}')
            for tag in span["spanInfo"]["tags"]:
                print(f'{indentation}{tag["key"]:<20} {tag["value"]:<20}')

# 遍历 trace 文件中所有的 span，并打印每个 span 的 tag 信息
def print_span_tags(file_path):
    # 读取trae数据
    with open(file_path, 'r') as file:
        trace_data = json.load(file)
    for item in trace_data["data"]:
        for span in item["spans"]:
            print("==================================================")
            print(f'spanID:{span["spanID"]:<16} operationName:{span["operationName"]:<50}')
            for tag in span["tags"]:
                print(f'    {tag["key"]:<20} {tag["value"]:<20}')

def get_span_tags(file_path):
    """
    遍历 trace 文件中所有的 span，并保存每个 span 的 tag 信息，写入为 Span 对象
    return : span 对象列表
    """
    with open(file_path, 'r') as file:
        trace_data = json.load(file)
    spans = []
    for item in trace_data["data"]:
        for span in item["spans"]:
            spanID = span["spanID"]
            operationName = span["operationName"]
            tags = span["tags"]
            new_span = Span(spanID, operationName, tags)
            spans.append(new_span)
    return spans

if __name__ == '__main__':
    file_path = 'TrainTicket-F1-trace/ts-cancel-service cancelTicket 963b968.json'
    all_trace_files = list(get_all_files('TrainTicket-F1-trace'))
    for i in range(len(all_trace_files)):
        all_trace_files[i] = os.path.join('TrainTicket-F1-trace', all_trace_files[i])

    spans = []
    for file in all_trace_files:
        # 只处理.json结尾的文件
        if file.endswith('.json'):
            print_span_tags(file)
            spans += get_span_tags(file)
    print(len(spans))
    # parse_trace_file('TrainTicket-F1-trace/ts-cancel-service cancelTicket 963b968.json')
    
        