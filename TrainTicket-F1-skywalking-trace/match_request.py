from trace_ana import load_spans_from_file, trace_analyze, get_bundle
import os, json

TIME_RANGE_MIN = -10  # 最小时间范围（毫秒）
TIME_RANGE_MAX = 10  # 最大时间范围（毫秒）

def readHTTPFile(filename) -> list:
    packages = []
    with open(filename, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            log_entry = json.loads(line)
            packages.append(log_entry)
    return packages

def _get_correspond_request_timestamp(span, segments):
    """
    segments: 将span按segment分组构成的字典
    输入一个 span，溯源到它的 request URL
    """
    entrySpan = segments[span.segmentID][0]
    if entrySpan.type != "Entry":
        raise Exception("segment[0] 不是 entrySpan")
    
    return entrySpan.startTime, entrySpan.endTime

def format_or_output(variable):
    """
    打印 body
    """
    try:
        # 尝试将变量解析为JSON
        json.loads(variable)
        # 如果解析成功，使用json.dumps美化输出
        return json.dumps(variable, indent=4)
    except Exception:
        # 如果解析失败，说明它是一个普通的字符串，直接返回
        return variable
    
def match_request_by_data(packages:list, bundles:list, segments):
    """
    根据时间戳、URL等信息将 HTTP 数据和 trace 中的请求相对应
    """
    for bundle in bundles:
        target_url = bundle.req.url
        target_method = bundle.req.http_method
        # 暂时不用 endtime
        target_timestamp, _ = _get_correspond_request_timestamp(bundle.span, segments)
        print(f"searching: [{target_timestamp}][{target_method}][{target_url}]")

        for p in packages:
            if p["method"] == target_method and p["url"] == target_url:
                # print(p["headers"]["X-Timestamp"])
                timestamp = p["headers"]["X-Timestamp"]
                time_diff_ms = int(target_timestamp) - int(timestamp)
                if TIME_RANGE_MIN <= time_diff_ms <= TIME_RANGE_MAX:
                    print(timestamp)
                    # 匹配成功，将HTTP数据中的Body数据填充到bundle.req.body中
                    bundle.req.body = p["body"]
                    # print(format_or_output(bundle.req.body))


def match_request(http_file, trace_file):
    """
    根据时间戳、URL等信息将 HTTP 数据和 trace 中的请求相对应
    """
    # 读取 span
    spans = []
    spans += load_spans_from_file(trace_file)
    # 读取 http package
    packages = readHTTPFile(http_file)
    
    segments, _ = trace_analyze(spans)
    
    bundles = []
    for span in spans:
        if span.sqlStmt is None :
            continue
        bundles.append(get_bundle(span, segments))
    
    match_request_by_data(packages, bundles, segments)

if __name__ == '__main__':
    http_file = 'data-0502/http_data.json'
    trace_file = 'data-0502/trace.json'
    match_request(http_file, trace_file)
