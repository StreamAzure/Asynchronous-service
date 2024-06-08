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
    1. Start from the root segment, find all exit Spans
    2. If the exit Span is a request Span, find the corresponding entry Span
    3. Repeat step 1 for the segment where the entry Span is located
    4. If the exit Span is a data Span, attach it to the req_data_map of its entry Span
    """
    global flowID, flows, req_data_map
    def _construct_flow(segments, segment_tree, now_segment_id, now_flow_id):
        global flowID, flows, req_data_map

        entrySpan = None
        entrySpan_unique_id = None
        for span in segments[now_segment_id]:
            # Traverse all spans in this segment
            if span.type == 'Entry':
                if span.layer != 'Http':
                    raise Exception(f"entry span is not Http span")
                entrySpan = span
                entrySpan_unique_id = f"{entrySpan.segmentID}-{entrySpan.spanID}"
                if entrySpan_unique_id not in req_data_map:
                    req_data_map[entrySpan_unique_id] = []
                
                if len(segments[now_segment_id][0].refs) == 0:
                    # User request, start a new request flow with EntrySpan
                    flow = Flow(flowID)
                    flowSpanId = len(flow.requestSpans)
                    flow.requestSpans.append(RequestSpan(flowID, flowSpanId, entrySpan))
                    
                    flows[flowID] = flow
                    now_flow_id = flowID
                    flowID += 1

            if span.type == 'Local' and span.component == 'SpringAsync':
                if now_segment_id == span.segmentID:
                    # Already in the segment starting with this asynchronous Local span
                    entrySpan = span
                    entrySpan_unique_id = f"{entrySpan.segmentID}-{entrySpan.spanID}"
                    if entrySpan_unique_id not in req_data_map:
                        req_data_map[entrySpan_unique_id] = []
                else:
                    # Forking, when forking, create a new request flow (and copy the previous ReqSpan)

                    async_flow = Flow(flowID)
                    async_flow.requestSpans = copy.deepcopy(flows[now_flow_id].requestSpans)

                    flows[flowID] = async_flow
                    flows[now_flow_id].child_flow_ids.append(flowID)
                    
                    flowID += 1

                    # Enter the segment starting with this asynchronous Local span
                    _construct_flow(segments, segment_tree, span.segmentID, async_flow.id)
                    
            if span.type == 'Exit':
                if span.layer == 'Http':
                    corresponding_entrySpan = find_entry_span_by_exit_span(span, segments, segment_tree)

                    for key, value in corresponding_entrySpan.tags.items():
                        if key not in span.tags:
                            span.tags[key] = value

                    # Not a user request, continue the current request flow
                    flow = flows[now_flow_id]
                    flowSpanId = len(flow.requestSpans)
                    requestSpan = RequestSpan(now_flow_id, flowSpanId, span)
                    flow.requestSpans.append(requestSpan)
                    requestSpan.corresponding_entrySpan_unique_id = corresponding_entrySpan.segmentID + '-' + str(corresponding_entrySpan.spanID)
                    
                    for child_flow_id in flow.child_flow_ids:
                        flowSpanId = len(flows[child_flow_id].requestSpans)
                        flows[child_flow_id].requestSpans.append(RequestSpan(now_flow_id, flowSpanId, span))
                        # It is a shared RequestSpan of the child flow, the flowID of this Span should be the ID of the parent flow to avoid duplicate pairing in the baseline algorithm

                    _construct_flow(segments, segment_tree, corresponding_entrySpan.segmentID, now_flow_id)

                elif span.layer == 'Database':
                    if entrySpan_unique_id is None:
                        raise Exception(f"entrySpan_unique_id is None")
                    if "PreparedStatement" in span.endpointName:
                        req_data_map[entrySpan_unique_id].append(DataSpan(span))
                    else:
                        print(f"skip data span {span.endpointName}")

    def _get_req_data_map(flow, req_data_map):
        """
        Attach all DataSpans corresponding to the EntrySpan to the RequestSpan
        And attach the SQL statements of the corresponding dataSpan to the requestSpan object
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
        Obtain the database information on the request flow
        """
        db_infos = []
        for reqSpan in flow.requestSpans:
            unique_id = reqSpan.span.segmentID + '-' + str(reqSpan.span.spanID)
            if unique_id in req_data_map:
                for dataSpan in req_data_map[unique_id]:
                    db_info = dataSpan.span.peer + ":" + dataSpan.span.tags["db.instance"]
                    db_infos.append(db_info)
        # Remove duplicates
        db_infos = list(set(db_infos))
        return db_infos

    # A trace file will only have one request flow, unless there is an Async fork in the trace
    root_segment_id = None
    for segment_id in segment_tree[root_segment_id]:
        _construct_flow(segments, segment_tree, segment_id, -1)

    # Request flows without child flows
    new_flows = {}
    for flow_id, flow in flows.items():
        if len(flow.child_flow_ids) == 0:
            new_flows[flow_id] = flow
    
    if os.environ.get('DEBUG') == '1':
        for flow_id, flow in flows.items():
            print(f"{flow_id}: {flow}\n")

    # Organize req_data_map
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
    # # Associate DataSpan
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