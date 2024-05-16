
"""
查询指定服务的所有TraceID
"""
TRACES_QUERY = """
query queryTraces($condition: TraceQueryCondition) {
  data: queryBasicTraces(condition: $condition) {
    traces {
      traceIds
    }
  }}
"""

"""
查询所有服务ID
"""
SERVICES_ID_QUERY = """
query queryServices($layer: String!) {
  services: listServices(layer: $layer) {
    id
    value: name
  }
}
"""

SERVICES_ID_QUERY_VALIABLES = {"layer": "GENERAL"}

"""
查询指定TraceID的所有Span
"""
SPAN_QUERY = """
query queryTrace($traceId: ID!) {
  trace: queryTrace(traceId: $traceId) {
    spans {
      traceId
      segmentId
      spanId
      parentSpanId
      refs {
        traceId
        parentSegmentId
        parentSpanId
        type
      }
      serviceCode
      serviceInstanceName
      startTime
      endTime
      endpointName
      type
      peer
      component
      isError
      layer
      tags {
        key
        value
      }
      logs {
        time
        data {
          key
          value
        }
      }
    }
  }
}
"""

def get_span_query_valiables(traceId:str) -> dict:
    format = {
        "traceId": "d228e7ee6d1a4f73801bfbba6556de8b.100.17158430663210001"
    }
    format["traceId"] = traceId
    return format


def get_traces_query_valiables(serviceId:str, startTime:str, endTime:str) -> dict:
    format =  {
        "condition": {
            "queryDuration": {
                "start": "2024-05-16 1443",
                "end": "2024-05-16 1513",
                "step": "MINUTE"
                },
            "paging": {
                "pageNum": 1,
                "pageSize": 100
                },
            "traceState": "ALL",
            "queryOrder": "BY_START_TIME",
            "serviceId": "dHMtYXV0aC1zZXJ2aWNl.1",
            "minTraceDuration": None,
            "maxTraceDuration": None
        }
    }
    format["condition"]["queryDuration"]["start"] = startTime
    format["condition"]["queryDuration"]["end"] = endTime
    format["condition"]["serviceId"] = serviceId

    return format

