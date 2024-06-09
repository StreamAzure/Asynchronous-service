import logging
from time import sleep
from queries import Query
from scenarios import query_and_preserve

# login train-ticket and store the cookies
url = 'http://localhost:8080'
q = Query(url)
if not q.login():
    print('login failed')

print("login success")

# execute scenario on current user
while(True):
    # query_and_preserve(q)
    start = "Shang Hai"
    end = "Nan Jing"
    other_place_pair = (start, end)
    trip_ids = q.query_normal_ticket(place_pair=other_place_pair)
    sleep(1)