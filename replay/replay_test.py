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
    
def str2package(str) -> dict:
    req = eval(str)
    req['headers']["Authorization"] = f"Bearer {token}"
    req['headers']["Host"] = 'localhost:12032'

    return req

def send_package(req):
    url = 'http://localhost:12032'

    response = requests.post(
        url, timeout=5, headers=req["headers"], json=req["content"]
    )
    if response.status_code == 200:
        print(response.text)
    else:
        print(response.status_code, response.text)

def replay(req1, req2):
    send_package(req1)
    send_package(req2)

if __name__ == "__main__":
    str1 = ""
    str2 = ""
    with open('data-0509-f1/http/http_flows.json', 'r') as f:
        lines = f.readlines()
        str1 = lines[44].strip()
        str2 = lines[46].strip()
    
    login()
    req1 = str2package(str1)
    req2 = str2package(str2)
    replay(req1, req2)



