import asyncio
import aiohttp
import time
import requests
from datetime import datetime

datestr = time.strftime("%Y-%m-%d", time.localtime())

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

place_pair = ("Shang Hai", "Su Zhou")

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
    
async def query_tickets():
    global uid, headers, address, token
    # =================== 高铁车票查询 =====================
    async with aiohttp.ClientSession() as session:
        query_url = f"{address}/api/v1/travelservice/trips/left"
        query_payload = {
                    "departureTime": datestr,
                    "startPlace": place_pair[0],
                    "endPlace": place_pair[1],
                }
        print("发送车票查询请求")
        async with session.post(query_url, timeout=10, headers=headers, json = query_payload) as response:
            if response.status == 200:
                print("车票查询成功")
                return await response.json()
            else:
                raise Exception(f"查询请求失败，状态码：{response.status}")
                
async def preserve_ticket(trip_id, contact_id):
    global uid, headers, address, token
    # =================== 高铁车票预订 =====================
    async with aiohttp.ClientSession() as session:
        preserve_url = f"{address}/api/v1/preserveservice/preserve"
        preserve_payload = {
            "accountId": uid,
            "assurance": "0",
            "contactsId": contact_id,
            "date": datestr,
            "from": place_pair[0],
            "to": place_pair[1],
            "tripId": trip_id,
            "foodType": "0",
            "seatType": 2
        }
        
        print("发送车票预订请求")
        async with session.post(preserve_url, timeout=10, headers=headers, json = preserve_payload) as response:
            if response.status == 200:
                print("车票预订成功")
                return await response.json()
            else:
                raise Exception(f"预订请求失败，状态码：{response.status}")
            
async def pay_ticket(order_id: str, trip_id):
    global uid, headers, address, token
    async with aiohttp.ClientSession() as session:
        pay_url = f"{address}/api/v1/inside_pay_service/inside_payment"
        pay_paytload = {
            "orderId": order_id,
            "tripId": trip_id
        }

        async with session.post(pay_url, timeout=10, headers=headers, json=pay_paytload) as response:
            if response.status == 200:
                print("车票支付")
                return await response.json()
            else:
                raise Exception(f"车票支付失败，状态码：{response.status}")

async def cancel_ticket(order_id:str):
    global uid, headers, address, token
    async with aiohttp.ClientSession() as session:
        cancel_url = f"{address}/api/v1/cancelservice/cancel/{order_id}/{uid}"

        async with session.get(cancel_url, timeout=10, headers=headers) as response:
            if response.status == 200:
                print("车票取消")
            else:
                raise Exception(f"车票取消失败，状态码：{response.status}")

async def main():
    current_time = datetime.now()
    # 格式化时间字符串
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    # 打印格式化的当前时间
    print("当前时间：", formatted_time)

    trip_id = 'D1345'
    contact_id = "d2a0c450-b180-40d9-8e29-a6e63afe84d1" 

    task1 = asyncio.ensure_future(preserve_ticket(trip_id, contact_id))
    task2 = asyncio.ensure_future(query_tickets())

    _, res2 = await asyncio.gather(task2,task1)
    order_id = res2["data"]
    print(f"order_id: {order_id}")
    if order_id != None:
        task3 = asyncio.ensure_future(pay_ticket(order_id, trip_id))
        task4 = asyncio.ensure_future(cancel_ticket(order_id))
        res3, res4 = await asyncio.gather(task3, task4)
        print(res3)
        print(res4)
    else:
        print("preserve order failed!")

login()
loop = asyncio.get_event_loop()

asyncio.run(main())
# tasks = [task1, task2]
# loop.run_until_complete(asyncio.wait(tasks))