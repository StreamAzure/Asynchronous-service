def print_red(text):
    print(f"\033[91m{text}\033[0m")

def print_blue(text):
    # 取消换行
    print(f"\033[94m{text}\033[0m", end='')

def print_green(text):
    print(f"\033[92m{text}\033[0m")

def print_flow_by_id(origin_flows, flow_id):
    flow = origin_flows[flow_id]
    print_blue(f"[FlowID: {flow_id}] ")
    print_green(flow)
    print()
    
def print_candidate_pairs(candidate_pairs, flows):
    for reqPair, dataSpanPairs in candidate_pairs.items():
        reqSpan1, reqSpan2 = reqPair
        print_blue(f"[FlowID: {reqSpan1.flowID}] ")
        print(f"[{reqSpan1.span.segmentID}-{reqSpan1.span.spanID}] {reqSpan1.span.tags['http.method']} {reqSpan1.span.tags['url']}")
        print_blue(f"[FlowID: {reqSpan2.flowID}] ")
        print(f"[{reqSpan2.span.segmentID}-{reqSpan2.span.spanID}] {reqSpan2.span.tags['http.method']} {reqSpan2.span.tags['url']}")

        print_green(f"[origin user request] {flows[reqSpan1.flowID].requestSpans[0].span.tags['http.method']} {flows[reqSpan1.flowID].requestSpans[0].span.tags['url']}")
        print_green(f"[origin user request] {flows[reqSpan2.flowID].requestSpans[0].span.tags['http.method']} {flows[reqSpan2.flowID].requestSpans[0].span.tags['url']}")

        for dataSpanPair in dataSpanPairs:
            dataSpan1, dataSpan2 = dataSpanPair
            print_red(f"\t{dataSpan1.peer} {dataSpan1.db} {dataSpan1.ids}")
            print_red(f"\t{dataSpan2.peer} {dataSpan2.db} {dataSpan2.ids}")
            print()

def print_res(res):
    for id, pairs in res.items():
        print_red(f"[ID: {id}] pair 数: {len(pairs)}")
        for pair in pairs:
            reqSpan1, reqSpan2 = pair
            print_blue(f"[FlowID: {reqSpan1.flowID}] ")
            print(f"[{reqSpan1.span.segmentID}-{reqSpan1.span.spanID}] {reqSpan1.span.tags['http.method']} {reqSpan1.span.tags['url']}")
            print_blue(f"[FlowID: {reqSpan2.flowID}] ")
            print(f"[{reqSpan2.span.segmentID}-{reqSpan2.span.spanID}] {reqSpan2.span.tags['http.method']} {reqSpan2.span.tags['url']}")
            print()

def save_segments(segments:dict, output_file):
    with open(output_file, 'w') as f:
        for segmentID, spans in segments.items():
            f.write(f"[Segment] {segmentID}\n")
            for span in spans:
                f.write(span.endpointName + "\n")
            f.write("\n")