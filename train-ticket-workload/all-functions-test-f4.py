import asyncio
import aiohttp
import time
import requests
from datetime import datetime
import random

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

# place_pair = ("Shang Hai", "Su Zhou")
place_pair = ("Shang Hai", "Nan Jing")

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
        async with session.post(query_url, headers=headers, json = query_payload) as response:
            if response.status == 200:
                print("车票查询成功")
                return await response.json()
            else:
                raise Exception(f"查询请求失败，状态码：{response.status}")

def _query_orders_all_info(query_other: bool = False) -> list[tuple]:
    """
    查询订单信息
    返回(orderId, tripId) triple list for consign service
    :param headers:
    :return:
    """

    global uid, headers, address, token, place_pair

    if query_other:
        url = f"{address}/api/v1/orderOtherService/orderOther/refresh"
    else:
        url = f"{address}/api/v1/orderservice/order/refresh"

    payload = {
        "loginId": uid,
    }

    response = requests.post(url=url, headers=headers, json=payload)
    if response.status_code != 200 or response.json().get("data") is None:
        print(f"query orders failed, response data is {response.text}")
        return None

    data = response.json().get("data")
    pairs = []
    for d in data:
        result = {}
        result["accountId"] = d.get("accountId")
        result["targetDate"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        result["orderId"] = d.get("id")
        result["from"] = d.get("from")
        result["to"] = d.get("to")
        pairs.append(result)
    print(f"queried {len(pairs)} orders")

    return pairs

def query_one_and_put_consign():
    global uid, headers, address, token, place_pair

    pairs = _query_orders_all_info(query_other=True)
    pair = random.choice(pairs)
    print(f"{pair['orderId']} queried and put consign")

    url = f"{address}/api/v1/consignservice/consigns"
    consignload = {
        "accountId": pair["accountId"],
        "handleDate": time.strftime('%Y-%m-%d', time.localtime(time.time())),
        "targetDate": pair["targetDate"],
        "from": pair["from"],
        "to": pair["to"],
        "orderId": pair["orderId"],
        "consignee": "32",
        "phone": "12345677654",
        "weight": "32",
        "id": "",
        "isWithin": False
    }
    response = requests.put(url=url, headers=headers,
                            json=consignload)

    order_id = pair["orderId"]
    if response.status_code == 200 | response.status_code == 201:
        print(f"{order_id} put consign success")
    else:
        print(f"{order_id} failed! {response.status_code}")
        return None

    return order_id

async def preserve_ticket(trip_id):
    global uid, headers, address, token

    def _query_assurances(headers: dict = {}):
        url = f"{address}/api/v1/assuranceservice/assurances/types"
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200 or response.json().get("data") is None:
            print(f"query assurance failed, response data is {response.json()}")
            return None
        data = response.json().get("data")
        # assurance只有一种

        return [{"assurance": "1"}]
    
    def _query_food(place_pair: tuple = ("Shang Hai", "Su Zhou"), train_num: str = "D1345", headers: dict = {}):
        url = f"{address}/api/v1/foodservice/foods/2021-07-14/{place_pair[0]}/{place_pair[1]}/{train_num}"

        response = requests.get(url=url, headers=headers)
        if response.status_code != 200 or response.json().get("data") is None:
            print(f"query food failed, response data is {response}")
            return None
        data = response.json().get("data")

        # food 是什么不会对后续调用链有影响，因此查询后返回一个固定数值
        return [{
            "foodName": "Soup",
            "foodPrice": 3.7,
            "foodType": 2,
            "stationName": "Su Zhou",
            "storeName": "Roman Holiday"
        }]


    def _query_contacts(headers: dict = {}) -> list[str]:
        """
        返回座位id列表
        :param headers:
        :return: id list
        """
        url = f"{address}/api/v1/contactservice/contacts/account/{uid}"

        response = requests.get(url=url, headers=headers)
        if response.status_code != 200 or response.json().get("data") is None:
            print(f"query contacts failed, response data is {response.json()}")
            return None

        data = response.json().get("data")
        # print("contacts")
        # pprint(data)

        ids = [d.get("id") for d in data if d.get("id") is not None]
        # pprint(ids)
        return ids

    # =================== 普通车票预订 =====================
    async with aiohttp.ClientSession() as session:
        preserve_url = f"{address}/api/v1/preserveotherservice/preserveOther"

        _ = _query_assurances(headers=headers)
        food_result = _query_food(headers=headers)
        contacts_result = _query_contacts(headers=headers)

        preserve_payload = {
            "accountId": uid,
            "assurance": "0",
            "date": datestr,
            "from": place_pair[0],
            "to": place_pair[1],
            "tripId": trip_id,
            "seatType": 9 # to trigger the fault
        }

        preserve_payload.update(random.choice(food_result))
        contacts_id = random.choice(contacts_result)
        preserve_payload["contactsId"] = contacts_id
    
        print("发送车票预订请求")
        async with session.post(preserve_url, headers=headers, json=preserve_payload) as response:
            if response.status == 200:
                print("车票预订成功")
                return await response.json()
            else:
                raise Exception(f"预订请求失败，状态码：{response.status}")

async def preserve_gaotie_ticket(trip_id):
    global uid, headers, address, token

    def _query_assurances(headers: dict = {}):
        url = f"{address}/api/v1/assuranceservice/assurances/types"
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200 or response.json().get("data") is None:
            print(f"query assurance failed, response data is {response.json()}")
            return None
        data = response.json().get("data")
        # assurance只有一种

        return [{"assurance": "1"}]
    
    def _query_food(place_pair: tuple = ("Shang Hai", "Su Zhou"), train_num: str = "D1345", headers: dict = {}):
        url = f"{address}/api/v1/foodservice/foods/2021-07-14/{place_pair[0]}/{place_pair[1]}/{train_num}"

        response = requests.get(url=url, headers=headers)
        if response.status_code != 200 or response.json().get("data") is None:
            print(f"query food failed, response data is {response}")
            return None
        data = response.json().get("data")

        # food 是什么不会对后续调用链有影响，因此查询后返回一个固定数值
        return [{
            "foodName": "Soup",
            "foodPrice": 3.7,
            "foodType": 2,
            "stationName": "Su Zhou",
            "storeName": "Roman Holiday"
        }]


    def _query_contacts(headers: dict = {}) -> list[str]:
        """
        返回座位id列表
        :param headers:
        :return: id list
        """
        url = f"{address}/api/v1/contactservice/contacts/account/{uid}"

        response = requests.get(url=url, headers=headers)
        if response.status_code != 200 or response.json().get("data") is None:
            print(f"query contacts failed, response data is {response.json()}")
            return None

        data = response.json().get("data")
        # print("contacts")
        # pprint(data)

        ids = [d.get("id") for d in data if d.get("id") is not None]
        # pprint(ids)
        return ids
    
    # =================== 高铁车票预订 =====================
    async with aiohttp.ClientSession() as session:
        preserve_url = f"{address}/api/v1/preserveservice/preserve"

        _ = _query_assurances(headers=headers)
        food_result = _query_food(headers=headers)
        contacts_result = _query_contacts(headers=headers)

        preserve_payload = {
            "accountId": uid,
            "assurance": "0",
            "date": datestr,
            "from": place_pair[0],
            "to": place_pair[1],
            "tripId": trip_id,
        }

        preserve_payload.update(random.choice(food_result))
        contacts_id = random.choice(contacts_result)
        preserve_payload["contactsId"] = contacts_id
        
        print("发送车票预订请求")
        async with session.post(preserve_url, headers=headers, json=preserve_payload) as response:
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

        async with session.post(pay_url, headers=headers, json=pay_paytload) as response:
            if response.status == 200:
                print("车票支付")
                return await response.json()
            else:
                raise Exception(f"车票支付失败，状态码：{response.status}")

async def cancel_ticket(order_id:str):
    global uid, headers, address, token
    async with aiohttp.ClientSession() as session:
        cancel_url = f"{address}/api/v1/cancelservice/cancel/{order_id}/{uid}"

        async with session.get(cancel_url, headers=headers) as response:
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
    # trip_id = 'D1345'
    trip_id = "Z1234"

    await query_tickets()
    task1 = asyncio.ensure_future(preserve_ticket(trip_id))
    task2 = asyncio.ensure_future(preserve_ticket(trip_id))
    pre_res, _ = await asyncio.gather(task1, task2)
    order_id = pre_res["data"]
    print(f"order_id: {order_id}")
    if order_id != None:
        res3 = await pay_ticket(order_id, trip_id)
        res4 = await cancel_ticket(order_id)
        print(res3)
        print(res4)

login()
loop = asyncio.get_event_loop()
asyncio.run(main())
