class TreeNode:
    def __init__(self, value):
        self.value = value
        self.children = []
        self.parent = None

def dfs_recursive(node, result, visited_asny:list, depth, visited_node:list):
    # 记录当前节点的值
    if "SpringAsync" in node.value and depth in visited_asny:
        return
    if node not in visited_node:
        result.append(node.value)
        visited_node.append(node)
    else:
        return
    
    if node.children:
        # 优先遍历子节点
        for child in node.children:
            dfs_recursive(child,  result, visited_asny, depth+1, visited_node)
    elif node.parent:
        # 如果没有子节点，则下一个节点是父节点的兄弟节点
        siblings = node.parent.children
        sibling_index = siblings.index(node)
        for sibling in siblings[sibling_index+1:]:
            if "SpringAsync" in sibling.value:
                if depth not in visited_asny:
                    visited_asny.append(depth)
                    dfs_recursive(sibling,  result, visited_asny, depth-1, visited_node)
                else:
                    continue
            else:
                dfs_recursive(sibling,  result, visited_asny, depth-1, visited_node)
    

# 示例用法
if __name__ == "__main__":
    # 创建树节点
    root = TreeNode("Get cancelservice")
    child1 = TreeNode("Get orderOtherservice")
    child2 = TreeNode("SpringAsync1")
    child3 = TreeNode("SpringAsync2")
    child4 = TreeNode("Get orderOtherservice")
    child5 = TreeNode("Put orderOtherservice 7")
    child6 = TreeNode("Get insidePaymentservice")
    child7 = TreeNode("Put orderOtherservice 4")
    
    # 构建树结构
    root.children = [child1, child2, child3]
    child2.children = [child7]
    child3.children = [child4, child5, child6]

    nodes = [root, child1, child2, child3, child4, child5, child6, child7]
    
    for node in nodes:
        for child in node.children:
            child.parent = node


    all_results = []
    results = []
    dfs_recursive(root, results, [], 0, [])
    str = ""
    for i, result in enumerate(results):
        if i != 0:
            str += '-> ' + result
        else:
            str = result
    print(str)

    all_results.append(result)

    # print(all_results)    

