from object import Span
from utils.sql_parse import *
from utils.io import get_all_files
import json
import os

def load_spans_from_file(file_path):
    """
    从 trace 文件中加载所有span
    return : span 对象列表
    """
    with open(file_path, 'r') as file:
        trace_data = json.load(file)

    data = trace_data["data"]["trace"]["spans"]
    spans = []
    for span in data:
        spans.append(Span(span))
    return spans

def trace_analyze(spans):
    def _print_trace(segments, segment_tree, parent_segment_id, level=0):
        if(level == 0):
            print('Root')
        for child_segment_id in segment_tree[parent_segment_id]:
            format = "   " * (level+1)
            print(f"{format} -------------------------------------")
            print(f"{format} {child_segment_id}")
            # 该 child_segment 的 span
            for span in segments[child_segment_id]:
                if span.layer == 'Http':
                    print(f"{format} [{span.spanID}] [{str(span.startTime)[8:]}] [{span.type:<5}] {span.tags['http.method']} {span.tags['url']}")
                else:
                    print(f"{format} [{span.spanID}] [{str(span.startTime)[8:]}] [{span.type:<5}] {span.endpointName}")
            _print_trace(segments, segment_tree, child_segment_id, level + 1)

    segments = {}
    for span in spans:
        if span.segmentID not in segments:
            segments[span.segmentID] = []
        segments[span.segmentID].append(span)

    new_segments = {}
    for segmentID, spanlist in segments.items():
        # 去除无用 span 和 segment
        if len(spanlist) == 1 and spanlist[0].endpointName == 'Mysql/JDBC/Connection/close':
            continue
        spanlist = sorted(spanlist, key = lambda span: span.spanID)
        spanlist = [span for span in spanlist if "HikariCP" not in span.endpointName and "Mysql/JDBC/Connection/commit" not in span.endpointName]
        # 不要 gateway 的 span
        spanlist = [span for span in spanlist if "gateway" not in span.service]

        new_segments[segmentID] = spanlist

    segments = new_segments

    segment_tree = {}
    for segmentID, spanlist in segments.items():
        if len(spanlist) == 0:
            continue
        if len(spanlist[0].refs) > 0 :
            parentSegmentID = spanlist[0].refs[0]["parentSegmentId"]
            # 原始数据中 异步Local 没有挂在父segment下
            # 这里手动挂在父segment下，方便请求流构建
            if spanlist[0].type == 'Local' and spanlist[0].component == 'SpringAsync':
                segments[parentSegmentID].append(spanlist[0])
        else: 
            parentSegmentID = None
        if parentSegmentID not in segment_tree:
            segment_tree[parentSegmentID] = []
        segment_tree[parentSegmentID].append(segmentID)
    
    for span in spans:
        segID = span.segmentID
        if segID not in segment_tree.keys():
            segment_tree[segID] = []
    
    # 对于每个 segment，其子 segment 按 startTime 从小到大排序
    for segmentID, child_segment_list in segment_tree.items():
        child_segment_list = sorted(child_segment_list, key = lambda segmentID: segments[segmentID][0].startTime)
        segment_tree[segmentID] = child_segment_list
    
    # 对于每个 segmetn，其 spanlist 按 startTime 从小到大排序
    for segmentID, spanlist in segments.items():
        segments[segmentID] = sorted(spanlist, key = lambda span: span.startTime)

    if os.environ.get('DEBUG') == '1':
        _print_trace(segments, segment_tree, None, 0)

    return segments, segment_tree

def pre_process_single_trace(trace_file):
    """
    只分析一条trace
    """
    spans = load_spans_from_file(trace_file)
        
    segments, segment_tree = trace_analyze(spans)

    return segments, segment_tree

def pre_process(trace_dir):
    """
    trace_dir: trace 文件目录
    return: segments, segment_tree
    """
    spans = []
    all_files = list(get_all_files(trace_dir))
    for file in all_files:
        span_file = os.path.join(trace_dir, file)
        try:
            if os.environ.get('DEBUG') == 1:
                print(f"reading {span_file}")
            spans += load_spans_from_file(span_file)
            
        except:
            raise Exception(f"failed in reading trace files: reading {span_file}")
        
    segments, segment_tree = trace_analyze(spans)

    return segments, segment_tree

