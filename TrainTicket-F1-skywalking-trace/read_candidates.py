import json
file = 'data-0502/res/candidate-pairs.json'
with open(file, 'r') as f:
    data = f.read()
    data = json.loads(data)
    for key, value in data.items():
        req1 = json.loads(value[0])
        req2 = json.loads(value[1])