import json
file = '/home/stream/Research/Asynchronous-service/test_output/candidatePairs_a7e15b90-2481-401e-ab59-baf13a9dfd56.json'
with open(file, 'r') as f:
    data = f.read()
    data = json.loads(data)
    for index, value in data.items():
        req1 = value[0]
        print(req1["http_method"], req1["http_url"])
        req2 = value[1]
        print(req2["http_method"], req2["http_url"])