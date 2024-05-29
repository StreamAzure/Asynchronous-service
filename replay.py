from object import *
from utils.io import *

def read_replay_pairs(file):
    with open(file, 'r') as f:
        data = f.read()
        replay_pairs = json.loads(data)
    
    return replay_pairs

def print_replay_pairs(replay_pairs, flows):
    for index, pair in replay_pairs.items():
        req1, req2 = pair[0], pair[1]
        flow_id1, flow_id2 = req1['flow_id'], req2['flow_id']

        origin1 = flows[flow_id1].get_original_requestSpan()
        origin2 = flows[flow_id2].get_original_requestSpan()

        print_blue(f"[FlowID: {flow_id1}] [FlowSpanID: {req1['flow_span_id']}] ")
        print(f"[{req1['http_method']} {req1['http_url']}")
        print_green(f"[origin user request] {origin1.span.tags['http.method']} {origin1.span.tags['url']}")
        print_red(f"[DB Info] {flows[flow_id1].db_infos}")

        print_blue(f"[FlowID: {flow_id2}] [FlowSpanID: {req2['flow_span_id']}] ")
        print(f"[{req2['http_method']} {req2['http_url']}")
        print_green(f"[origin user request] {origin2.span.tags['http.method']} {origin2.span.tags['url']}")
        print_red(f"[DB Info] {flows[flow_id2].db_infos}")
        
        print()

def sort_replay_pairs(replay_pairs, flows):
    """
    按 flow ID 及 reqSpan 在 flow 中的顺序排序
    根据每个 pair 的 flow id 分类，将有相同 flow id 的 pair 放在一起
    对于存在子流的flow id, 将 flow id 换成子流的 flow id
    """
    for index, pair in replay_pairs.items():
        req1, req2 = pair[0], pair[1]
        flow1 = flows[req1['flow_id']]
        flow2 = flows[req2['flow_id']]
        if flow1.have_child_flow():
            # 视为第一个子流的请求
            req1['flow_id'] = flow1.child_flow_ids[0]
        if flow2.have_child_flow():
            # 视为第一个子流的请求
            req2['flow_id'] = flow2.child_flow_ids[0]

        # pair 内部, flowID 小的在前
        if req1['flow_id'] < req2['flow_id']:
            replay_pairs[index] = (req1, req2)
        else:
            replay_pairs[index] = (req2, req1)
    
    # 以 pairs[0]['flow_id'] 为准，字典内从小到大排序
    sorted_pairs = sorted(replay_pairs.items(), key=lambda x: x[1][0]['flow_id'])
    replay_pairs = {index: pair for index, pair in sorted_pairs}

    print_replay_pairs(replay_pairs, flows)

def replay(replay_pairs, flows):
    """
    重放请求对
    """
    
    

if __name__ == '__main__':
    data_dir = './output'
    request_flow_file = os.path.join(data_dir, 'request_flows.pkl')

    # 读取请求流数据
    flows = read_request_flows(request_flow_file)
    
    # 读取目录下的所有 json 文件
    replay_pairs_files = list(get_all_files(data_dir))
    for file in replay_pairs_files:
        file = os.path.join(data_dir, file)
        # 每次处理一个ID文件
        if 'candidatePairs' in file:
            print_red(f"Replaying: {file}\n")
            replay_pairs = read_replay_pairs(file)

            sort_replay_pairs(replay_pairs, flows)
            # parse_replay_pairs(replay_pairs, flows)

    