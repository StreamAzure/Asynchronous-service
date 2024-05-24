import json
file = './candidate-pairs.json'
with open(file, 'r') as f:
    data = f.read()
    data = json.loads(data)
    for index, value in data.items():
        req1 = value[0]
        req2 = value[1]