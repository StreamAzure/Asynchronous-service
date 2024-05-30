import json
import pickle
import os

def get_all_files(directory):
    """
    递归遍历指定目录，并返回所有json文件名
    使用：all_files = list(get_all_files(dir))
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('json'):
                yield os.path.relpath(os.path.join(root, file), directory)

def print_red(text):
    print(f"\033[91m{text}\033[0m")

def print_blue(text):
    # 取消换行
    print(f"\033[94m{text}\033[0m", end='')

def print_green(text):
    print(f"\033[92m{text}\033[0m")

def print_flow_by_id(origin_flows, flow_id):
    flow = origin_flows[flow_id]
    print_blue(f"[FlowID: {flow_id}] [Lenth: {len(flow.requestSpans)}] ")
    print_green(flow)
    print_red(f"[DB info] {flow.db_infos}")
    print()
    
def print_candidate_pairs(candidate_pairs, flows):
    for reqPair, dataSpanPairs in candidate_pairs.items():
        reqSpan1, reqSpan2 = reqPair
        print_blue(f"[FlowID: {reqSpan1.flowID}] [FlowSpanID: {reqSpan1.flowSpanID}]")
        print(f"[{reqSpan1.span.segmentID}-{reqSpan1.span.spanID}] {reqSpan1.span.tags['http.method']} {reqSpan1.span.tags['url']}")
        print_blue(f"[FlowID: {reqSpan2.flowID}] [FlowSpanID: {reqSpan2.flowSpanID}]")
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

def create_http_req(reqSpan):
    """
    提取 Request span 中的相关信息构成 HTTP 报文
    """
    span = reqSpan.span

    http_method = span.tags["http.method"]
    url = span.tags["url"]
    http_body = ""
    if "http.param" in span.tags.keys():
        http_body = json.loads(span.tags["http.param"]) if span.tags["http.param"] != "" else {}
    if "http.response" in span.tags.keys():
        http_response = json.loads(span.tags["http.response"]) if span.tags["http.response"] != "" else {}
    if "http.status_code" in span.tags.keys():
        http_status_code = span.tags["http.status_code"]

    return {
        "flow_id": reqSpan.flowID,
        "flow_span_id": reqSpan.flowSpanID,
        "sqls": reqSpan.sqls,
        "http_method": http_method,
        "http_url": url,
        "http_body": http_body,
        "http_status_code": http_status_code,
        "http_response": http_response
    }

def origin_output(res:dict, output_dir):
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as error:
        print(f"error when creating output dir: {error}")

    for id, pair_list in res.items():
        output_file = output_dir + "/candidatePairs" + "_" + id + ".json"
        res_json = {}
        for i, reqPair in enumerate(pair_list):
            res_json[i] = [
                create_http_req(reqPair[0]),
                create_http_req(reqPair[1])
            ]
        if len(res_json) == 0:
            continue

        json_data = json.dumps(res_json, indent=4)
        print(f"{output_file}: total {len(res_json)} pairs")
        with open(output_file, 'w') as f:
            f.write(json_data)

def save_request_flows(flows, output_dir):
    """
    保存请求流到二进制文件
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as error:
        print(f"error when creating output dir: {error}")

    file_name = output_dir + "/request_flows.pkl"
    with open(file_name, 'wb') as file:
        pickle.dump(flows, file)

def read_request_flows(file_name):
    # 检查文件是否存在
    if not os.path.exists(file_name):
        print(f"File {file_name} not found.")
        return None
    with open(file_name, 'rb') as file:
        flows = pickle.load(file)
    return flows