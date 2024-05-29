import json
from object import Span
from utils.sql_parse import *
import itertools
import copy

flowID = 0
flows = []

class Flow:
    def __init__(self, id, headSpan=None, flow=None):
        self.id = id
        if headSpan is not None:
            self.headSpan = headSpan
            self.tailSpan = headSpan
        elif flow is not None:
            self.headSpan = flow.headSpan
            self.tailSpan = flow.tailSpan
        else:
            raise Exception("Flow init error: headSpan and flow are both None")
        self.child_flow_ids = []

    def __str__(self):
        output = ""
        nowSpan = self.headSpan
        while nowSpan is not None:
            if nowSpan == self.headSpan:
                output += f"{nowSpan.span.endpointName}"
            else:
                output += f" -> {nowSpan.span.endpointName}"
            nowSpan = nowSpan.nextRequestSpan
        return output

class RequestSpan:
    def __init__(self, flowID, span):
        self.flowID = flowID # 所属请求流
        self.span = span
        self.nextRequestSpan = None # 下一个Requestspan

    def __deepcopy__(self, memo):
        # 创建新实例
        new_instance = RequestSpan(self.flowID, self.span)
        return new_instance

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

        new_segments[segmentID] = spanlist

    segments = new_segments

    first_spanlist = None
    segment_tree = {}
    for segmentID, spanlist in segments.items():
        if len(spanlist[0].refs) > 0 :
            parentSegmentID = spanlist[0].refs[0]["parentSegmentId"]
            # 原始数据中 异步Local 没有挂在父segment下
            # 这里手动挂在父segment下，方便请求流构建
            if spanlist[0].type == 'Local' and spanlist[0].component == 'SpringAsync':
                segments[parentSegmentID].append(spanlist[0])
        else: 
            parentSegmentID = None
            first_spanlist = spanlist
        if parentSegmentID not in segment_tree:
            segment_tree[parentSegmentID] = []
        segment_tree[parentSegmentID].append(segmentID)
    
    segments[None] = first_spanlist
    
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

    _print_trace(segments, segment_tree, None, 0)

    return segments, segment_tree

def find_span(spanId, segments):
    segID = spanId.split('-')[0]
    spanID = int(spanId.split('-')[1])
    span = None
    for s in segments[segID]:
        if s.spanID == spanID:
            span = s
            break
    if span is None:
        raise Exception(f"span {spanId} not found")
    return span

def find_entry_span_by_exit_span(exitSpan, segments, segment_tree):
    for child_segment in segment_tree[exitSpan.segmentID]:
        for span in segments[child_segment]:
            if span.type == 'Entry' and span.refs[0]["parentSpanId"] == exitSpan.spanID:
                if span.layer == 'Http':
                    return span
    raise Exception(f"entry span not found for exit span {exitSpan.segmentID}-{exitSpan.spanID}")

def find_entry_span_by_segment_id(segmentID, segments):
    for span in segments[segmentID]:
        if span.type == 'Entry':
            if span.layer != 'Http':
                raise Exception(f"entry span is not Http span")
            else:
                return span
    raise Exception(f"entry span not found for segment {segmentID}")

def construct_flow(segments, segment_tree):
    """
    1. 从根segment开始，找到其所有 exit Span
    2. 若exit Span为 request Span，找到对应的 entry Span
    3. 对于该 entry Span 所在的segment，重复1
    4. 若exit Span 为 data Span, 挂到其 entry Span 的req_data_map上
    """
    def _construct_flow(segments, segment_tree, now_segment_id, req_data_map, now_flow_id):
        global flowID, flows

        entrySpan = None
        entrySpan_unique_id = None
        for span in segments[now_segment_id]:
            # 遍历本segment的所有span
            if span.type == 'Entry':
                if span.layer != 'Http':
                    raise Exception(f"entry span is not Http span")
                entrySpan = span
                entrySpan_unique_id = f"{entrySpan.segmentID}-{entrySpan.spanID}"
                if entrySpan_unique_id not in req_data_map:
                    req_data_map[entrySpan_unique_id] = []
                
                if now_segment_id == None:
                    # 用户请求，创建新的请求流
                    flow = Flow(flowID, headSpan=RequestSpan(flowID, entrySpan))
                    flows.append(flow)
                    now_flow_id = flowID
                    flowID += 1
                
                else:
                    # 非用户请求，继续当前请求流
                    flow = flows[now_flow_id]

                    for child_flow_id in flow.child_flow_ids:
                        flows[child_flow_id].tailSpan.nextRequestSpan = RequestSpan(child_flow_id, entrySpan)
                        flows[child_flow_id].tailSpan = flows[child_flow_id].tailSpan.nextRequestSpan

            if span.type == 'Local' and span.component == 'SpringAsync':
                if now_segment_id == span.segmentID:
                    # 已经位于以该异步Local为起始span的segment中
                    entrySpan = span
                    entrySpan_unique_id = f"{entrySpan.segmentID}-{entrySpan.spanID}"
                    if entrySpan_unique_id not in req_data_map:
                        req_data_map[entrySpan_unique_id] = []
                else:
                    # 产生分叉，分叉时要创建新的请求流(并复制之前的ReqSpan)
                    async_flow = Flow(flowID, flow=flows[now_flow_id])
                    flows.append(async_flow)
                    flows[now_flow_id].child_flow_ids.append(flowID)
                    
                    flowID += 1

                    # 进入以该异步Local为起始span的segment中
                    _construct_flow(segments, segment_tree, span.segmentID, req_data_map, async_flow.id)
                    

            if span.type == 'Exit':
                if span.layer == 'Http':
                    corresponding_entrySpan = find_entry_span_by_exit_span(span, segments, segment_tree)
                    _construct_flow(segments, segment_tree, corresponding_entrySpan.segmentID, req_data_map, now_flow_id)
                elif span.layer == 'Database':
                    if entrySpan_unique_id is None:
                        raise Exception(f"entrySpan_unique_id is None")
                    req_data_map[entrySpan_unique_id].append(span)


    # 一个 trace 文件只会有一条请求流，除非trace中有Async分叉
    root_segment_id = None
    req_data_map = {}
    _construct_flow(segments, segment_tree, root_segment_id, req_data_map, -1)

if __name__ == '__main__':
    file = 'data/f1-response/d6dcf0452c2f44f0b903443fb6470601.120.17169468514030001.json'
    spans = load_spans_from_file(file)
    segments, segment_tree = trace_analyze(spans)
    construct_flow(segments, segment_tree)

    for flow in flows:
        print(flow.id)
        print(flow)