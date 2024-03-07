from itertools import groupby
import json
from file_helper import *

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


class Span:
    def __init__(self, span, service_name):
        self.traceID = span["traceID"]
        self.spanID = span["spanID"]
        self.operationName = span["operationName"]
        self.tags = span["tags"]
        self.logs = span["logs"]
        self.service = service_name
    
    def get_tag_keys(self) -> list:
        """
        获取 tag 字段中所有 key 的列表
        """ 
        return [tag["key"] for tag in self.tags]
    
    def get_log_keys(self) -> list:
        """
        获取 log 字段中所有 key 的列表
        """
        keys = []
        for log in self.logs:
            for field in log['fields']:
                keys.append(field['key'])
        return keys

    def get_http_info(self):
        """
        获取 http 请求url、状态码、method
        """
        
        

def load_spans_from_file(file_path):
    """
    从 trace 文件中加载所有span
    return : span 对象列表
    """
    with open(file_path, 'r') as file:
        trace_data = json.load(file)
    data = trace_data["data"]
    spans = []
    for span in data[0]["spans"]:
        spans.append(Span(span))
    return spans

def load_service_info_from_file(file_path):
    """
    从 trace 文件中加载 service 信息
    每个 service 都由唯一的 process ID 对应
    返回列表：[{processID: {serviceName, ip}}{}{}]
    """
    with open(file_path, 'r') as file:
        trace_data = json.load(file)
    processes = trace_data["data"][0]["processes"]
    p_names = processes.keys()

    service_infos = []
    for p in p_names:
        service_info = {}
        service_info['serviceName'] = processes[p]["serviceName"]
        for tag in processes[p]["tags"]:
            if tag['key'] == 'ip':
                service_info['ip'] = tag['value']
                break
        service_infos.append({p: service_info})

    return service_infos

if __name__ == '__main__':
    file_path = 'TrainTicket-F1-trace/ts-cancel-service cancelTicket 963b968.json'
    all_trace_files = list(get_all_files('TrainTicket-F1-trace'))
    for i in range(len(all_trace_files)):
        all_trace_files[i] = os.path.join('TrainTicket-F1-trace', all_trace_files[i])

    # spans = []
    # for file in all_trace_files:
    #     # 只处理.json结尾的文件
    #     if file.endswith('.json'):
    #         spans += load_spans_from_file(file)

    # ---------------------------------------------
    

    # for span in spans:
    #     print(span.get_tag_keys())
    #     print(span.get_log_keys())
    #     print()

    # parse_trace_file('TrainTicket-F1-trace/ts-cancel-service cancelTicket 963b968.json')
    
        