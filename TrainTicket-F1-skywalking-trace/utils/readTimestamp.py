import json

def readTraceFile(filename):
    with open(filename, 'r') as f:
        return json.load(f)["data"]["trace"]["spans"]
    
def readHTTPFile(filename) -> list:
    logs = []
    with open(filename, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            log_entry = json.loads(line)
            logs.append(log_entry)
    return logs
    
def get_timestamps_trace(data) -> list:
    timestamps = []
    for span in data:
        if("/api/v1" in str(span["tags"])):
            if("startTime" in span):
                # print(span["startTime"])
                timestamps.append(span["startTime"])
            if("endTime" in span):
                # print(span["endTime"])
                timestamps.append(span["endTime"])
    return timestamps

def get_timestamps_http(data) -> list:
    timestamps = []
    for p in data:
        # print(p["headers"]["X-Timestamp"])
        timestamps.append(p["headers"]["X-Timestamp"])
    return timestamps

def main():
    span = readTraceFile('../data-0502/trace.json')
    timestamps = sorted(get_timestamps_trace(span))
    print(len(timestamps))
    for t in timestamps:
        print(t)
    print("----")
    data = readHTTPFile('../data-0502/http_data.json')
    timestamps2 = sorted(get_timestamps_http(data))
    print(len(timestamps2))
    for t in timestamps2:
        print(t)

if __name__ == "__main__":
    main()