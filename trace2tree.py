import json
import matplotlib.pyplot as plt
import networkx as nx

# 读取追踪数据
with open('user-post-home.json', 'r') as file:
    trace_data = json.load(file)

# 创建有向图
G = nx.DiGraph()

# 添加节点和边
for item in trace_data["data"]:
    trace_id = item["traceID"]
    print(trace_id)
    for span in item["spans"]:
        span_id = span["spanID"]
        operation_name = span["operationName"]
        print('\t'+span_id, operation_name)
        references = span.get("references", [])

        G.add_node(span_id, label=operation_name)

        for ref in references:
            parent_span_id = ref["spanID"]
            G.add_edge(parent_span_id, span_id)

# 绘制树状图
pos = nx.spring_layout(G, seed=42)  # 使用spring布局算法，seed可使布局保持一致
labels = nx.get_edge_attributes(G, 'label')
nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'), node_size=800, node_color="skyblue", font_size=8)
nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)

# 显示图形
# plt.show()
