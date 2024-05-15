import requests
import json

address = "http://localhost:8080"
uid = ""
token = ""
headers = {
            'Proxy-Connection': 'keep-alive',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
def login(username="fdse_microservice", password="111111") -> bool:
    """
    登陆并建立session，返回登陆结果
    """
    global uid, headers, address, token
    url = f"{address}/api/v1/users/login"

    data = '{"username":"' + username + '","password":"' + \
        password + '","verificationCode":"1234"}'

    # 获取cookies
    verify_url = address + '/api/v1/verifycode/generate'
    r = requests.get(url=verify_url)
    r = requests.post(url=url, headers=headers,
                            data=data, verify=False)

    if r.status_code == 200:
        data = r.json().get("data")
        uid = data.get("userId")
        token = data.get("token")
        headers["Authorization"] = f"Bearer {token}"
        print(f"login success, uid: {uid}")
        return True
    else:
        print("login failed")
        return False

def send_package(str):
    global token
    req = eval(str)
    url = req['url']
    p_headers = req['headers']
    method = req['method']
    content = req['content']

    p_headers["Authorization"] = f"Bearer {token}"
    p_headers["Host"] = 'localhost:12032'

    print(json.dumps(p_headers, indent=4))
    # print(content)


    url = 'http://localhost:12032'

    response = requests.post(
        url, timeout=5, headers=p_headers, json=content
    )
    if response.status_code == 200:
        print(response.content)
    else:
        print(response)

str1 = ""
str2 = ""
with open('data-0509/http/http_flows.json', 'r') as f:
    lines = f.readlines()
    str1 = lines[44].strip()
    str2 = lines[46].strip()

login()
send_package(str1)
send_package(str2)



