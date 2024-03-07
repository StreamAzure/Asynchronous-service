from scapy.all import *
from scapy.packet import Raw
from scapy.layers.inet import TCP
import http.client
import json
from file_helper import *

class HTTPPacket:
    def __init__(self, packet, header, type, data=None, request_line=None):
        self.packet = packet  # 原始报文
        self.type = type  # 报文类型，请求或响应
        self.req_type = request_line.split(b' ')[0].decode() if self.type == 'request' else None # 请求方法
        self.data = data  # Body携带的请求数据，json对象
        self.header = header  # 首部
        self.ack = packet[TCP].ack  # 序列号
        self.seq = packet[TCP].seq  # 确认号
        self.time = int(packet.time * 1000000)
        self.request_line = request_line
        self.url = request_line.split(b' ')[1].decode()

    def __str__(self):
        return f'Type: {self.type}\nReq_Type: {self.req_type}\nURL: {self.url}\nTime: {self.time}\nBody: {json.dumps(self.data, indent=4, ensure_ascii=False)}'

    def __repr__(self):
        return f'HTTPPacket(packet={self.packet}, header={self.header}, type={self.type}, data={self.data}, request_line={self.request_line})'

    # def get_packet_data_keys(self) -> set:
    #     """
    #     获取报文中所有的数据字段名称。若字段中还有字段，一并加入
    #     """
    #     data = self.data
    #     keys = set()
    #     for key, value in data.items():
    #         keys.add(key)
    #         if isinstance(value, dict):
    #             keys |= value.keys()
    #     return keys

def print_http_packets(pcap_file):
    """
    速览 pcap 文件中的HTTP报文
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

def load_HTTPpackets_from_pcap(pcap_file):
    """
    从 pcap 文件中加载所有 HTTP 报文
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
                    # print(f"正在加载第 {len(http_packets) + 1} 个报文")
                    http_packets.append(http_packet)
    return http_packets

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
    if(len(keys1) == 0 or len(keys2) == 0 or len(keys1 | keys2) == 0):
        return 0
    overlap_rate = len(keys1 & keys2) / len(keys1) if len(keys1) > len(keys2) else len(keys1 & keys2) / len(keys2)
    return overlap_rate

if __name__ == '__main__':
    pcap_files = list(get_all_files('TrainTicket-F1-pcap'))
    for i in range(len(pcap_files)):
        pcap_files[i] = os.path.join('TrainTicket-F1-pcap', pcap_files[i])

    HTTPPackets = []
    for file in pcap_files: # 加载全部的 pcap 文件
        print(f"正在加载 {file}……")
        HTTPPackets += load_HTTPpackets_from_pcap(file)


    HTTPPackets.sort(key=lambda packet: packet.time)
    cnt = 0
    with open('pcap_output.txt', 'w') as f:
        for http_packet in HTTPPackets:
            # 打印全部信息
            cnt += 1
            f.write(f"==== packet {cnt} ====\n")
            f.write(str(http_packet)+"\n\n")