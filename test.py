from pcap_ana import *
from trace_ana import *

if __name__ == '__main__':
    # 1. 解析全部的HTTP报文
    pcap_files = list(get_all_files('TrainTicket-F1-pcap'))
    for i in range(len(pcap_files)):
        pcap_files[i] = os.path.join('TrainTicket-F1-pcap', pcap_files[i])
    
    http_packets = []
    for file in pcap_files:
        print(f"正在解析 {file}……")
        http_packets += load_HTTPpackets_from_pcap(file)
    
    # 报文去重
    http_packets = deduplicate_packets(http_packets)

    print(f"http_packets 共有 {len(http_packets)} 个报文\n")

    # 2. 解析 trace
    all_trace_files = list(get_all_files('TrainTicket-F1-trace'))
    for i in range(len(all_trace_files)):
        all_trace_files[i] = os.path.join('TrainTicket-F1-trace', all_trace_files[i])

    spans = []
    for file in all_trace_files:
        # 只处理.json结尾的文件
        if file.endswith('.json'):
            spans += load_spans_from_file(file)

    # 3. 在全部报文中收集所出现的 ID 值，这一步是为了能找出那些在URL中携带ID的报文
    # 候选关键词列表
    keywords = ["id", "ID", "Id"]
    # 收集所出现的 ID 值
    ids = set()
    cnt = 0
    # 记录字段名
    keys_contain_keyword = set()
    for packet in http_packets:
        data = packet.data
        found = False
        for key in data:
            if any(key.endswith(keyword) for keyword in keywords):
                keys_contain_keyword.add(key)
                found = True
                # print(f"在报文{packet}中找到关键词{key}，其值为{data[key]}")
                ids.add(data[key])
            if isinstance(data[key], dict):
                for nested_key in data[key]:
                    if any(nested_key.endswith(keyword) for keyword in keywords):
                        keys_contain_keyword.add(nested_key)
                        found = True
                        # print(f"在报文{packet}中找到关键词{nested_key}，其值为{data[key][nested_key]}")
                        ids.add(data[key][nested_key])
            elif isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict):
                        for nested_key in item:
                            if any(nested_key.endswith(keyword) for keyword in keywords):
                                keys_contain_keyword.add(nested_key)
                                found = True
                                # print(f"在报文{packet}中找到关键词{nested_key}，其值为{item[nested_key]}")
                                ids.add(item[nested_key])
        if found :
            cnt += 1
    print(f"共找到 {cnt} 个报文包含 ID 关键词\n")
    print(f"包含 ID 关键词的字段名：{keys_contain_keyword}\n" )
    print(f"找到 ids: {ids}\n")
    # TODO：{'loginId', 'accountId', 'orderNumOfValidOrder', 'id'}，暂定只算以ID结尾的词

    # 4. 筛选ID值，只保留那些也在span里出现过的ID值
    filtered_ids = set()
    for span in spans:
        for id in ids:
            if id in str(span):
                filtered_ids.add(id)

    print(f"在 span 中也出现过的 ID 值: {filtered_ids}\n")
    
    # 5. 找出URL或数据字段中包含这些ID值的请求报文
    packets_contain_id = []
    for packet in http_packets:
        if packet.type != "request":
            continue
        if any(id in str(packet.data) or id in packet.url for id in filtered_ids):
            packets_contain_id.append(packet)

    print(f"filtered_packets 共有 {len(packets_contain_id)} 个报文\n")

    # 输出到文件
    with open('filtered_packets.txt', 'w') as f:
        for packet in packets_contain_id:
            f.write(str(packet) + '\n\n')

    # 6. 找出这些请求报文对应的span（要求URL能够部分匹配，且时间戳相近（差值小于500））
    matched_span_packet = {}
    for packet in packets_contain_id:
        found = False
        for span in spans:
            timestamp = span.logTimestamp if span.logTimestamp else span.startTime
            if packet.url in str(span) and abs(packet.time - timestamp) < 10000:
                matched_span_packet[packet] = span
                found = True
                break
        if not found:
            print(f"未找到与报文{packet}对应的span\n")
        
    print(f"共 {len(matched_span_packet)} 个匹配对\n")

    # 输出到文件
    with open('matched_span_packet.txt', 'w') as f:
        for packet in matched_span_packet:
            f.write(f"报文：{packet}\n对应的span：{matched_span_packet[packet]}\n\n")

