import json
import re
from object import Span, Req

def create_http_req(httpSpan:Span) -> Req:
    """
    提取 HTTP span 中的相关信息构成 HTTP 报文
    """
    if "http.method" not in httpSpan.tags.keys():
        raise Exception(f"span {httpSpan} is not a valid HTTP span!")
    
    http_method = httpSpan.tags["http.method"]
    url = httpSpan.tags["url"]
    http_body = ""
    if "http.param" in httpSpan.tags.keys():
        http_body = httpSpan.tags["http.param"]

    if httpSpan.x_operation_type == "":
        raise Exception(f"httpSpan.x_operation_type is empty, something wrong! \n {httpSpan}")

    return Req(http_method, url, http_body, httpSpan.endpointName, httpSpan.x_operation_type)

def origin_output(candidate_pairs:dict, output_dir):
    """
    不处理路径中的参数
    """
    for id, pair_list in candidate_pairs.items():
        output_file = output_dir + "/candidatePairs" + "_" + id + ".json"
        res = {}
        for i, reqPair in enumerate(pair_list):
            req1 = create_http_req(reqPair[0])
            req2 = create_http_req(reqPair[1])
            if(req1 == req2):
                continue
            
            res[i] = [
                req1.__dict__(),
                req2.__dict__()
            ]
        if len(res) == 0:
            continue
        json_data = json.dumps(res, indent=4)
        print(f"{output_file}: total {len(res)} pairs")
        with open(output_file, 'w') as f:
            f.write(json_data)

def mask_parameters_output(candidate_pairs:dict, output_dir):
    """
    将路径中的参数模糊处理为通配符 ?
    再输出
    """
    def _mask_parameters(req: Req):
        """
        input: GET:/api/v1/cancelservice/cancel/{orderId}/{loginId}
        output: /api/v1/cancelservice/cancel/?/?
        """
        endpoint_url = req.endpointName
        # 正则表达式匹配一个或多个大写字母后跟冒号和空格
        # 去除匹配的前缀
        endpoint_url = re.sub(r'^[A-Z]+:', '', endpoint_url)
        # 将变量部分替换为问号
        endpoint_url = re.sub(r'\{[^\}]+\}', '?', endpoint_url)
        # print(endpoint_url)
        req.url = endpoint_url

    for id, pair_list in candidate_pairs.items():
        output_file = output_dir + "/candidatePairs" + "_" + id
        res = {}
        for i, reqPair in enumerate(pair_list):
            req1 = create_http_req(reqPair[0])
            req2 = create_http_req(reqPair[1])
            if(req1 == req2):
                continue

            _mask_parameters(req1)
            _mask_parameters(req2)
            
            res[i] = [
                req1.__dict__(),
                req2.__dict__()
            ]
        if len(res) == 0:
            continue
        json_data = json.dumps(res, indent=4)
        print(f"{output_file}: total {len(res)} pairs")
        with open(output_file, 'w') as f:
            f.write(json_data)

def save_segments(segments:dict, output_file):
    with open(output_file, 'w') as f:
        for segmentID, spans in segments.items():
            f.write(f"[Segment] {segmentID}\n")
            for span in spans:
                f.write(span.endpointName + "\n")
            f.write("\n")
    