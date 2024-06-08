import requests
import json
import os
import re
import datetime

URL = "http://localhost:16686/api"

def _date2timestamp(time_str:str):
    """
    时间字符串转16位时间戳
    时间字符串：2024-05-18 20:50:00
    """
    time_format = "%Y-%m-%d %H:%M:%S"
    # 转换为 datetime 对象
    dt_object = datetime.datetime.strptime(time_str, time_format)
    return int(dt_object.timestamp() * 1e6)

def _timestamp2date(timestamp):
    """
    16位时间戳转时间字符串
    """
    timestamp_secs = timestamp / 1e6
    # 转换为 datetime 对象
    dt_object = datetime.datetime.fromtimestamp(timestamp_secs)
    return str(dt_object)

def query_services():
    url = URL + '/services'
    response = requests.get(url)
    if response.status_code == 200:
        response_json = response.json()
        return response_json["data"]
    else:
        raise Exception(f"query_services 失败：{response.status_code}, {response.text}")

def query_operations(ref_url, service:str):
    url  = URL + '/services/' + service + '/operations'
    response = requests.get(url, headers={'Referer': ref_url})
    if response.status_code == 200:
        response_json = response.json()
        return response_json["data"]
    else:
        raise Exception(f"query_operation 失败：{response.status_code}, {response.text}")
    
def get_query_url(prefix, start, end, service, operation=None):
    """
    start: e.g. 2024-05-18 20:50:00
    """
    start = "&start=" + str(_date2timestamp(start))
    end = "&end=" + str(_date2timestamp(end))
    limit = "&limit=" + '500'
    service = "&service=" + service
    if operation is not None:
        operation = "&operation=" + operation
    else:
        operation = ""
    
    url = URL.replace("api", "") + prefix + 'lookback=custom' + start + end + limit + service + operation

    return url


def query_trace_list(url):
    response = requests.get(url)
    if response.status_code == 200:
        response_json = response.json()
        return response_json["data"]
    else:
        raise Exception(f"query_trace_list 失败：{response.status_code}, {response.text}")


def main():
    services = query_services()
    services.remove("jaeger-all-in-one")
    start = "2024-06-08 07:30:00"
    end =  "2024-06-08 07:33:00"
    print(services)

    trace_visited = []
    span_visited = []

    db_req_cnt = 0

    for service in services:
        # ref = get_query_url('search?', start, end, service)
        # operations = query_operations(ref, service)
        
        # pattern = re.compile(r'redis|mongo')
        # matched_items = [item for item in operations if pattern.search(item)]

        url = get_query_url('api/traces?', start, end, service)
        # print(url)
        trace_data = query_trace_list(url)
        # print("trace_data: ", len(trace_data))
        for trace in trace_data:
            traceID = trace["traceID"]
            if traceID in trace_visited:
                continue
            trace_visited.append(traceID)
            for span in trace["spans"]:
                spanID = span["spanID"]
                if spanID in span_visited:
                    continue
                span_visited.append(spanID)
                pattern = re.compile(r'redis|mongo|Mongo|Redis')
                if pattern.search(span["operationName"]):
                    db_req_cnt += 1
                    print(f"[{span['spanID']}] {span['operationName']}")

    print(db_req_cnt)

if __name__ == "__main__":
    main()

