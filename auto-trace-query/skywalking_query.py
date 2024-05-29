import requests
import json
import os
from querys import *

# 目标URL
URL = 'http://localhost:8090/graphql'

def query_traces(serviceId, startTime, endTime):
    variables = get_traces_query_valiables(serviceId, startTime, endTime)
    payload = {
        "query": TRACES_QUERY,
        "variables": variables
    }
    response = requests.post(URL, json=payload, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        response_json = response.json()
        # print(json.dumps(response_json, indent=2))  # 格式化输出JSON
        return response_json
    else:
        raise Exception(f"query_traces 失败：{response.status_code}, {response.text}")

def query_services():
    payload = {
        "query": SERVICES_ID_QUERY,
        "variables": SERVICES_ID_QUERY_VALIABLES
    }
    response = requests.post(URL, json=payload, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        response_json = response.json()
        # print(json.dumps(response_json, indent=2))  # 格式化输出JSON
        return response_json
    else:
        raise Exception(f"query_services 失败：{response.status_code}, {response.text}")
    
def query_spans(traceId):
    payload = {
        "query": SPAN_QUERY,
        "variables": get_span_query_valiables(traceId)
    }
    response = requests.post(URL, json=payload, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        response_json = response.json()
        # print(json.dumps(response_json, indent=2))  # 格式化输出JSON
        return response_json
    else:
        raise Exception(f"query_spans 失败：{response.status_code}, {response.text}")

def system_get_all_spans(output_dir, startTime, endTime):
    """
    startTime: "2024-05-16 1443"
    endTime: "2024-05-16 1513"
    获取指定时间段内的全系统所有微服务的 span 数据
    输出到 output_dir 目录
    """

    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output dir '{output_dir}' created or existed.")
    except OSError as error:
        print(f"error when creating output dir: {error}")

    # 查询所有服务ID
    print("Query all service IDs...\n")
    services = query_services()
    service_ids = []
    for s in services["data"]["services"]:
        service_ids.append(s["id"])
    # print(service_ids)
    print(f"Total service IDs: {len(service_ids)}\n")

    print("Query all trace IDs...\n")
    trace_ids = []
    for service_id in service_ids:
        data = query_traces(service_id, startTime, endTime)
        for trace in data["data"]["data"]["traces"]:
            trace_ids += trace["traceIds"]
    # print(trace_ids)
    print(f"Total trace IDs: {len(trace_ids)}\n")

    print("Query all spans...\n")
    for trace_id in trace_ids:
        res = query_spans(trace_id)
        filename = trace_id + ".json"
        file_name = os.path.join(output_dir, filename)
        with open(file_name, "w") as f:
            json.dump(res, f, indent=2)
        print(f"save file success: {trace_id}")
        
if __name__ == "__main__":
    system_get_all_spans('./data/f1-response', "2024-05-29 0940", "2024-05-29 0941")



    



