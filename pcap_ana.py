import os
from scapy.all import *
from scapy.layers.http import HTTPRequest
from scapy.layers.http import HTTP
from scapy.packet import Raw
from scapy.layers.inet import IP, TCP
import http.client
import json

class HTTPPair:
    def __init__(self, request, response):
        self.request = request
        self.response = response

    def __str__(self):
        return f'Request: {self.request}\nResponse: {self.response}'

    def __repr__(self):
        return f'HTTPPair(request={self.request}, response={self.response})'

class HTTPPacket:
    def __init__(self, packet, header, type, data=None, request_line=None):
        self.packet = packet  # 原始报文
        self.type = type  # 报文类型，请求或响应
        self.data = data  # Body携带的请求数据，json对象
        self.header = header  # 首部
        self.ack = packet[TCP].ack  # 序列号
        self.seq = packet[TCP].seq  # 确认号
        self.time = int(packet.time * 1000000)
        self.data_keys = set(data.keys())
        self.request_line = request_line
        self.url = request_line.split(b' ')[1].decode()

    def __str__(self):
        return f'Type: {self.type}\nTime: {self.time}\nData Keys: {self.data_keys}\nURL: {self.url}\nBody: {json.dumps(self.data, indent=4, ensure_ascii=False)}\n'

    def __repr__(self):
        return f'HTTPPacket(packet={self.packet}, header={self.header}, type={self.type}, data={self.data}, request_line={self.request_line})'

# 遍历指定目录
def traverse_directory(path):
    for root, dirs, files in os.walk(path):
        for name in files:
            print(os.path.join(root, name))
        for name in dirs:
            print(os.path.join(root, name))

def pair_http_packets(pcap_file):
    """
    遍历 pcap 文件中的所有HTTP报文，并匹配请求和响应报文
    """
    packets = rdpcap(pcap_file)
    http_requests = {}
    http_pairs = []
    cnt = 0
    for packet in packets:
        if packet.haslayer(TCP) and packet.haslayer(Raw) and b"HTTP" in packet[Raw].load:
            cnt += 1
            ack = packet[TCP].ack
            seq = packet[TCP].seq
            raw_data = packet[Raw].load
            headers_alone, body = raw_data.split(b'\r\n\r\n', 1)
            request_line, headers_alone = headers_alone.split(b'\r\n', 1)
            # print(request_line)
            if b"200" in request_line:
                # 响应报文
                if seq in http_requests: # 找之前出现的请求报文
                    http_pairs.append(HTTPPair(http_requests[seq], packet))
                    # http_requests.pop(seq)
                else:
                    print("该响应报文找不到对应请求报文！")
            else:
                # 请求报文
                http_requests[ack] = packet
    return http_pairs

def print_http_packets(pcap_file):
    """
    遍历并打印 pcap 文件中的所有 HTTP 报文
    """
    packets = rdpcap(pcap_file)
    cnt = 0
    for packet in packets:
        if packet.haslayer(Raw):
            raw_data = packet[Raw].load
            if b"HTTP" in raw_data:
                cnt = cnt + 1
                print(f'===== 第 {cnt} 个 HTTP 报文 =====')
                headers_alone, body = raw_data.split(b'\r\n\r\n', 1)
                request_line, headers_alone = headers_alone.split(b'\r\n', 1)
                headers = http.client.parse_headers(io.BytesIO(headers_alone))
                print(f'Request Line: {request_line.decode()}')
                if body != b'':
                    body_str = body.decode()
                    # 尝试解析 JSON
                    json_start = body_str.find('{')
                    json_end = body_str.rfind('}') + 1
                    if json_start != -1 and json_end != -1:
                        body_json = json.loads(body_str[json_start:json_end])
                        print('Body:', json.dumps(body_json, indent=4, ensure_ascii=False))
                # print('Headers:')
                # for name, value in headers.items():
                #     print(f'{name}: {value}')
                print('\n')

def packet2HTTPPacket(http_packet):
    """
    将原始 packet 转换成自定义的 HTTPPacket，方便处理报文数据
    """
    raw_data = http_packet[Raw].load
    if b"HTTP" in raw_data:
        headers_alone, body = raw_data.split(b'\r\n\r\n', 1)
        request_line, headers_alone = headers_alone.split(b'\r\n', 1)
        header = http.client.parse_headers(io.BytesIO(headers_alone))
        type = ""
        if b"200" in request_line:
            # 响应报文
            type = "response"
        else:
            # 请求报文
            type = "request"
        if body != b'':
            body_str = body.decode()
            # 尝试解析 JSON
            json_str = re.search(r'\{.*\}|\[.*\]', body_str).group()
            if json_str != '':
                body_json = json.loads(json_str)
                if isinstance(body_json, list):
                    body_json = {"data": body_json}
                return HTTPPacket(http_packet, header, type, body_json, request_line)
            else:
                raise Exception(f"JSON解析失败, 原始Body：{body_str}")
        else:
            return HTTPPacket(http_packet, header, type, {}, request_line)
    else:
        raise Exception("转换失败：未找到HTTP报文")

def get_HTTPpackets_from_pcap(pcap_file):
    """
    从 pcap 文件中获取所有 HTTP 报文
    return: HTTPPacket 对象列表
    """
    packets = rdpcap(pcap_file)
    http_packets = []
    for packet in packets:
        if packet.haslayer(Raw):
            raw_data = packet[Raw].load
            if b"HTTP" in raw_data:
                http_packet = packet2HTTPPacket(packet)
                if http_packet:
                    http_packets.append(http_packet)
    return http_packets

def print_packet(packet):
    """
    打印单个 packet 的请求行和Body（如果有）
    """
    raw_data = packet[Raw].load
    if b"HTTP" in raw_data:
        headers_alone, body = raw_data.split(b'\r\n\r\n', 1)
        request_line, headers_alone = headers_alone.split(b'\r\n', 1)
        print(f'Request Line: {request_line.decode()}')
        if body != b'':
            body_str = body.decode()
            try:
                # 尝试解析 JSON
                json_start = body_str.find('{')
                json_end = body_str.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    body_json = json.loads(body_str[json_start:json_end])
                    print('Body:', json.dumps(body_json, indent=4, ensure_ascii=False))
            except json.JSONDecodeError:
                # 如果 body 不是有效的 JSON，那么就直接打印
                print("json解析失败")
                print('Body:', body_str)
    else:
        print("该 packet 不是 HTTP 报文！")

def get_request_packet(http_packets, response):
    """
    根据响应报文，从HTTP报文列表中找到对应的请求报文
    """
    for packet in http_packets:
        if packet.ack == response.seq:
            return packet
    print("未能找到对应的请求报文！")
    return None

def calculate_overlap_rate(packet1, packet2):
    json1 = packet1.data
    json2 = packet2.data
    keys1 = set(json1.keys())
    keys2 = set(json2.keys())
    if(len(keys1 | keys2) == 0):
        return 0
    overlap_rate = len(keys1 & keys2) / len(keys1 | keys2)
    return overlap_rate

def main(file_path):
    """
    所有响应报文两两之间配对data数据中的Json字段
    计算字段重合率，构成三元组(报文1，报文2，重合率)写入列表
    对于重合率最高的一对响应报文，打印出对应的请求报文和响应报文的data字段
    """

    overlap_rates = []
    packets = []
    packets = get_HTTPpackets_from_pcap(file_path)
    max_overlap = 0
    max_overlap_pair = None

    for i in range(len(packets)):
        for j in range(i + 1, len(packets)):
            overlap_rate = calculate_overlap_rate(packets[i], packets[j])
            overlap_rates.append((packets[i].data_keys, packets[j].data_keys, overlap_rate))
    
    overlap_rates.sort(key=lambda x: x[2], reverse=True)

    for item in overlap_rates:
        print(item)

    # print(f'最大重合率：{max_overlap}')
    # print(f'最大重合率对应的请求报文：')
    # print_packet(max_overlap_pair.request)
    # print(f'最大重合率对应的响应报文：')
    # print_packet(max_overlap_pair.response)

if __name__ == '__main__':
    file_path = './TrainTicket-F1-pcap/order-other.pcap'
    print_http_packets(file_path)
    # packets = get_HTTPpackets_from_pcap(file_path)
    # main(file_path)
    # print(len(packets))
    # for http_packet in packets:
    #     # 打印全部信息
    #     print(http_packet.)

        # if http_packet.type == "response":
        #     req = get_request_packet(packets, http_packet)
        #     http_packet.url = req.url

    # main(file_path)