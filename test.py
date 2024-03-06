from pcap_ana import *
from trace_ana import *

def parse_pcap():
    # 读取并解析 pcap 文件
    pcap_file_path = './TrainTicket-F1-pcap/cancel.pcap'
    packets = get_HTTPpackets_from_pcap(pcap_file_path) # 获取所有的报文，已经被封装为自定义的HTTPPacket对象

    for http_packet in packets:
        if http_packet.type == "response": # 默认只有请求报文才有 url，这里为响应报文也填充对应请求报文的url
            req = get_request_packet(packets, http_packet) # 找出对应的请求报文
            http_packet.url = req.url

    for http_packet in packets:
        print("===================================")
        print(http_packet)
        


def parse_trace():
    # 读取并解析 trace 文件
    all_trace_files = list(get_all_files('TrainTicket-F1-trace'))
    for i in range(len(all_trace_files)):
        all_trace_files[i] = os.path.join('TrainTicket-F1-trace', all_trace_files[i])
    
    spans = []
    for file in all_trace_files:
        if file.endswith('.json'): # 可能有多个 trace 文件，将 span 一起收集
            print_span_tags(file)
            spans += get_span_tags(file)

    for span in spans:
        for tag in span.tags:
            if tag["key"] == "http.url":
                # print(tag["value"])
                pass
            print(f'    {tag["key"]:<20} {tag["value"]:<20}')

if __name__ == '__main__':
    parse_pcap()
    # parse_trace()