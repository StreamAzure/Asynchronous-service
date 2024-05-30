from utils.sql_parse import *
import copy
from trace_preprocess import pre_process
from object import Flow, RequestSpan, DataSpan
from utils.io import print_red
import os

flowID = 0
flows = {}
req_data_map = {}

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
    global flowID, flows, req_data_map
    def _construct_flow(segments, segment_tree, now_segment_id, now_flow_id):
        global flowID, flows, req_data_map

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
                
                if len(segments[now_segment_id][0].refs) == 0:
                    # 用户请求，以EntrySpan开始创建新的请求流
                    flow = Flow(flowID)
                    flowSpanId = len(flow.requestSpans)
                    flow.requestSpans.append(RequestSpan(flowID, flowSpanId, entrySpan))
                    
                    flows[flowID] = flow
                    now_flow_id = flowID
                    flowID += 1

            if span.type == 'Local' and span.component == 'SpringAsync':
                if now_segment_id == span.segmentID:
                    # 已经位于以该异步Local为起始span的segment中
                    entrySpan = span
                    entrySpan_unique_id = f"{entrySpan.segmentID}-{entrySpan.spanID}"
                    if entrySpan_unique_id not in req_data_map:
                        req_data_map[entrySpan_unique_id] = []
                else:
                    # 产生分叉，分叉时要创建新的请求流(并复制之前的ReqSpan)

                    async_flow = Flow(flowID)
                    async_flow.requestSpans = copy.deepcopy(flows[now_flow_id].requestSpans)

                    flows[flowID] = async_flow
                    flows[now_flow_id].child_flow_ids.append(flowID)
                    
                    flowID += 1

                    # 进入以该异步Local为起始span的segment中
                    _construct_flow(segments, segment_tree, span.segmentID, async_flow.id)
                    

            if span.type == 'Exit':
                if span.layer == 'Http':
                    corresponding_entrySpan = find_entry_span_by_exit_span(span, segments, segment_tree)

                    for key, value in corresponding_entrySpan.tags.items():
                        if key not in span.tags:
                            span.tags[key] = value

                    # 非用户请求，继续当前请求流
                    flow = flows[now_flow_id]
                    flowSpanId = len(flow.requestSpans)
                    requestSpan = RequestSpan(now_flow_id, flowSpanId, span)
                    flow.requestSpans.append(requestSpan)
                    requestSpan.corresponding_entrySpan_unique_id = corresponding_entrySpan.segmentID + '-' + str(corresponding_entrySpan.spanID)
                    
                    for child_flow_id in flow.child_flow_ids:
                        flowSpanId = len(flows[child_flow_id].requestSpans)
                        flows[child_flow_id].requestSpans.append(RequestSpan(now_flow_id, flowSpanId, span))
                        # 是子流共有的RequestSpan，该Span的flowID应该是parent flow的ID，避免baseline算法重复配对

                    _construct_flow(segments, segment_tree, corresponding_entrySpan.segmentID, now_flow_id)

                elif span.layer == 'Database':
                    if entrySpan_unique_id is None:
                        raise Exception(f"entrySpan_unique_id is None")
                    req_data_map[entrySpan_unique_id].append(DataSpan(span))

    def _get_req_data_map(flow, req_data_map):
        """
        将对应 EntrySpan 的 DataSpan 全部挂到 RequestSpan 上
        并把对应 dataSpan 的 SQL 语句挂到 requestSpan 对象上
        """
        new_req_data_map = {}
        for flow_id, flow in flows.items():
            for reqSpan in flow.requestSpans:
                unique_id = reqSpan.span.segmentID + '-' + str(reqSpan.span.spanID)
                dataSpans = []
                if unique_id in req_data_map:
                    for dataSpan in req_data_map[unique_id]:
                        dataSpans.append(dataSpan)
                if reqSpan.corresponding_entrySpan_unique_id in req_data_map:
                    for dataSpan in req_data_map[reqSpan.corresponding_entrySpan_unique_id]:
                        dataSpans.append(dataSpan)
                
                new_req_data_map[unique_id] = dataSpans

                for dataSpan in dataSpans:
                    reqSpan.sqls.append(dataSpan.span.sqlStmt_with_param)

        return new_req_data_map
    
    def _get_dbinfo_in_flow(flow, req_data_map):
        """
        获取请求流上的数据库信息
        """
        db_infos = []
        for reqSpan in flow.requestSpans:
            unique_id = reqSpan.span.segmentID + '-' + str(reqSpan.span.spanID)
            if unique_id in req_data_map:
                for dataSpan in req_data_map[unique_id]:
                    db_info = dataSpan.span.peer + ":" + dataSpan.span.tags["db.instance"]
                    db_infos.append(db_info)
        # 去重
        db_infos = list(set(db_infos))
        return db_infos

    # 一个 trace 文件只会有一条请求流，除非trace中有Async分叉
    root_segment_id = None
    for segment_id in segment_tree[root_segment_id]:
        _construct_flow(segments, segment_tree, segment_id, -1)

    # 没有子流的请求流
    new_flows = {}
    for flow_id, flow in flows.items():
        if len(flow.child_flow_ids) == 0:
            new_flows[flow_id] = flow
    
    if os.environ.get('DEBUG') == '1':
        for flow_id, flow in flows.items():
            print(f"{flow_id}: {flow}\n")

    # 整理 req_data_map
    req_data_map = _get_req_data_map(flows, req_data_map)

    for flow_id, flow in flows.items():
        flow.db_infos = _get_dbinfo_in_flow(flow, req_data_map)

    return new_flows, flows, req_data_map

if __name__ == '__main__':
    
    trace_dir = './data/f1-response'

    segments, segment_tree = pre_process(trace_dir)
    construct_flow(segments, segment_tree)

    for flow_id, flow in flows.items():
        if len(flow.child_flow_ids) == 0:
            print_red(flow_id)
            print(flow)
            print()

    # print("============\n")
    # # 关联DataSpan
    # for flow_id, flow in flows.items():
    #     for reqSpan in flow.requestSpans:
    #         http_str = f"[{reqSpan.span.tags['http.method']}] {reqSpan.span.tags['url']}"
    #         print(http_str)
    #         unique_id = reqSpan.span.segmentID + '-' + str(reqSpan.span.spanID)
    #         if unique_id in req_data_map:
    #             for dataSpan in req_data_map[unique_id]:
    #                 # print(f"\t[{dataSpan.operation}] [{dataSpan.peer}] [{dataSpan.db}] {dataSpan.span.endpointName} {dataSpan.ids}")
    #                 print(f"\t[{dataSpan.operation}] [{dataSpan.span.endpointName}] {dataSpan.ids} {dataSpan.span.sqlStmt_with_param}")

    # print(len(req_data_map))