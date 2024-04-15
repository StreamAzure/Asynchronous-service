
# TODO：观察到有一些请求会同时出现在多个 id_span group中
# 也许可以做剪枝，将同时出现在多个group的一组请求优先测试
# 想不到好的算法，先两两求交，得出那些在两个集合里都出现过的group
# all_sets = [set(value) for value in value_to_pairs.values()]
# intersections = []
# for pair in combinations(all_sets, 2):
#     intersection = pair[0].intersection(pair[1])
#     if intersection:
#         intersections.append(intersection)
# # 输出所有非空的交集结果
# for intersect in intersections:
#     print("----")
#     for i in intersect:
#         timestamp_in_seconds = i.span.startTime / 1000
#         dt_object = datetime.fromtimestamp(timestamp_in_seconds, UTC)
#         print(f"[{dt_object}]", get_segment_by_span(i.span, spans))

def _find_parent

def trace_based_filter(candidate_pairs, segments, segment_tree):
    """
    基于 trace 关系进行剪枝。满足以下情况之一时剔除 request pair
    1. request 对应的 span 在 segment_tree 中位于同一路径
    2. request 具有相同的 segmentID
    """
    print(f"开始剪枝，该ID下有 {len(candidate_pairs)} 对可疑 request pairs")
    pruned_pairs = []

    for pair in candidate_pairs:
        bundle_a = pair[0]
        bundle_b = pair[1]
        # 具有相同的 segmentID，存在HB关系，不会并发
        if bundle_a.span.segmentID == bundle_b.span.segmentID:
            continue
        # span 存在父子关系
        elif True:
            pass
        else:
            pruned_pairs.append(pair)

    print(f"剪枝完成，该ID下有 {len(pruned_pairs)} 对可疑 request pairs\n")
    
    return pruned_pairs
