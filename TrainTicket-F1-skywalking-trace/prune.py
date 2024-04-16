
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

# LCA算法
def LCA_prune(origin_queries:list, segment_tree) -> list:
    def pre(origin_queries:list) -> dict:
        queries = {}
        for q in origin_queries:
            segID_1 = q[0].span.segmentID
            segID_2 = q[1].span.segmentID
            if segID_1 not in queries.keys():
                queries[segID_1] = []
            if segID_2 not in queries.keys():
                queries[segID_2] = []
            queries[segID_1].append(segID_2)
            queries[segID_2].append(segID_1)
        return queries
    
    def find(x):
        if(x == fa[x]):
            return x
        else:
            fa[x] = find(fa[x])
            return fa[x]

    def union(x, y):
        a = find(x)
        b = find(y)
        if(a!=b):
            fa[a] = b

    def dfs(tree, node):
        for child in tree[node]:
            if(visited[child] == False):
                dfs(tree, child)
                union(child, node) # 注意这里的顺序不能反

        visited[node] = True

        if node in queries.keys():
            for v in queries[node]:
                if(visited[v]):
                    ans = find(v)
                    lca[(node,v)] = ans
                    lca[(v, node)] = ans
    
    def after(origin_queries) -> list:
        """
        根据 LCA 结果剔除位于同一路径上的 pair
        if: LCA 为 pair 中的某一个
        """
        pruned_pairs = []
        for q in origin_queries:
            a = q[0].span.segmentID
            b = q[1].span.segmentID
            if(lca[(a,b)] == a):
                continue
            if(lca[(a,b)] == b):
                continue
            pruned_pairs.append(q)
        return pruned_pairs
    
    if(origin_queries == None or len(origin_queries) == 0):
        return []
    lca = {}
    queries = pre(origin_queries)
    fa = {}
    visited = {}
    for id_list in segment_tree.values():
        for id in id_list:
            fa[id] = id
            visited[id] = False
    fa[None] = None
    visited[None] = False

    dfs(segment_tree, None)

    pruned_pairs = after(origin_queries)
    
    # for key, value in lca.items():
    #     print(f"{key} : {value}")

    return pruned_pairs


def trace_based_filter(candidate_pairs, segments, segment_tree):
    """
    基于 trace 关系进行剪枝。满足以下情况之一时剔除 request pair
    1. request 具有相同的 segmentID
    2. request 对应的 span 在 segment_tree 中位于同一路径
    """

    pruned_pairs = []
    # 具有相同的 segmentID，存在HB关系，不会并发
    print(f"[Rule 1] Before: {len(candidate_pairs)}")
    pruned_pairs = [pair for pair in candidate_pairs if pair[0].span.segmentID != pair[1].span.segmentID]
    print(f"[Rule 1] After: {len(pruned_pairs)}")
    
    # 两个 request 在 trace 中位于同一路径上
    #（即两个 request 所属的 segment 的最近公共祖先为其中一个segment自己）
    print(f"[Rule 2] Before: {len(pruned_pairs)}")
    pruned_pairs = LCA_prune(pruned_pairs, segment_tree)
    print(f"[Rule 2] After: {len(pruned_pairs)}")

    print()
    
    return pruned_pairs

if __name__ == "__main__":
    pass