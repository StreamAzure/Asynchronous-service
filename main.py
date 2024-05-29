from trace_preprocess import pre_process, pre_process_single_trace
from reqflow_construct import construct_flow
from reqflow_analyze import formulate_candidate_pairs_origin, prune_by_database, prune_by_flow, classify_by_ids
from utils.io import print_candidate_pairs, print_flow_by_id, origin_output, save_request_flows, print_blue, print_red

def output_all_sql_statemnts(req_data_map):
    sqls = []
    for dataSpans in req_data_map.values():
        for dataSpan in dataSpans:
            ids = dataSpan._get_ids(dataSpan.span)
            print_blue(dataSpan.span.sqlStmt_with_param + "\n")
            print_red(ids)
    #         sqls.append(dataSpan.span.sqlStmt_with_param)

    # # 去重
    # sqls = list(set(sqls))
    # for sql in sqls:
    #     print(sql)

def main():
    trace_dir = './data/f1-response'
    output_dir = './output'

    segments, segment_tree = pre_process(trace_dir)
    # segments, segment_tree = pre_process_single_trace('data/f1-response/d6dcf0452c2f44f0b903443fb6470601.120.17169468514030001.json')

    # flows: 独立请求流的集合; origin_flows: 含子流的请求流集合（用于 flow_prune）, req_data_map: reqSpan与dataSpan的映射
    flows, origin_flows, req_data_map = construct_flow(segments, segment_tree)
    candidate_pairs = formulate_candidate_pairs_origin(flows, req_data_map)
    print("=====")
    candidate_pairs = prune_by_database(candidate_pairs, req_data_map)
    print("=====")
    candidate_pairs = prune_by_flow(candidate_pairs, flows, origin_flows)
    print("=====")

    res = classify_by_ids(candidate_pairs)

    # # 打印结果
    # print_candidate_pairs(candidate_pairs, origin_flows)

    # # 打印所有独立请求流
    for flow_id, flow in flows.items():
        print_flow_by_id(origin_flows, flow_id)
    # output_all_sql_statemnts(req_data_map)

    origin_output(res, output_dir)

    save_request_flows(origin_flows, output_dir)

if __name__ == "__main__":
    main()
    
    
