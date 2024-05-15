import json
import re
from object import RequestSpanBundle

def origin_output(candidate_pairs:list, output_file):
    """
    原始 candidate_pairs 输出（可以是剪枝后的），已按匹配分数从高到低排序
    每个元素为一个tuple: (RequestSpanBundle, RequestSpanBundle)
    """
    res = {}
    for i, pairs in enumerate(candidate_pairs):
        if len(pairs) == 0:
            continue
        res[i] = [str(pairs[0].req), str(pairs[1].req)]
    json_data = json.dumps(res, indent=4)
    with open(output_file, 'w') as f:
        f.write(json_data)

def mask_parameters_output(candidate_pairs:list, output_file):
    """
    将路径中的参数模糊处理为通配符 ?
    再输出
    """
    def _mask_parameters(bundle: RequestSpanBundle):
        endpoint_url = bundle.req.endpoint_name
        # 正则表达式匹配一个或多个大写字母后跟冒号和空格
        # 去除匹配的前缀
        endpoint_url = re.sub(r'^[A-Z]+:', '', endpoint_url)
        # 将变量部分替换为问号
        endpoint_url = re.sub(r'\{[^\}]+\}', '?', endpoint_url)
        # print(endpoint_url)
        bundle.req.url = endpoint_url

        # input: GET:/api/v1/cancelservice/cancel/{orderId}/{loginId}
        # output: /api/v1/cancelservice/cancel/?/?

    res = {}
    for i, pairs in enumerate(candidate_pairs):
        if len(pairs) == 0:
            continue
        _mask_parameters(pairs[0])
        _mask_parameters(pairs[1])
        # res[i] = [str(pairs[0].req), str(pairs[1].req)]
        res[i] = [
            json.dumps(pairs[0].req, default=lambda obj: obj.__json__()),
            json.dumps(pairs[1].req, default=lambda obj: obj.__json__())
        ]
    json_data = json.dumps(res, indent=4)
    with open(output_file, 'w') as f:
        f.write(json_data)
