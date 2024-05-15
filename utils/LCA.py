def tarjan_lca(tree, root, queries):
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
        
        for q in queries: 
            # queries化简一下，存queries的时候搞成双向边
            # u : [v1,v2,v3,...]
            # v1 : [u, ...]
            if(q[0] == node):
                v = q[1]
                if visited[v]:
                    lca[(node,v)] = find(v)
                    lca[(v,node)] = lca[(node,v)]

    fa = {}
    visited = {}
    for node in tree.keys():
        fa[node] = node
        visited[node] = False

    lca = {}
    dfs(tree, root)
    for key, value in lca.items():
        print(f"{key} : {value}")

tree = {}
tree[1] = [2,3]
tree[2] = [4,5]
tree[3] = [6]
tree[4] = [] 
tree[5] = [7,8]
tree[6] = []
tree[7] = [9]
tree[8] = []
tree[9] = []

queries = [
    (8,9),
    (9,8),
    (4,6),
    (6,4),
    (7,5),
    (5,7),
    (5,3),
    (3,5)
]
tarjan_lca(tree, 1, queries)