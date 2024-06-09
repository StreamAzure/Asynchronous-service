import time
import requests
import random
import requests
import json
from utils.db_helper import *
import re

headers = {
    'Proxy-Connection': 'keep-alive',
    'Accept': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Content-Type': 'application/json',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}
address = "http://localhost:8080"

def login(username="fdse_microservice", password="111111") -> bool:
    """
    Log in and establish a session, returning the login result.
    """
    global headers, address
    url = address + "/api/v1/users/login"
    data = '{"username":"' + username + '","password":"' + \
           password + '","verificationCode":"1234"}'
    # Get cookies
    verify_url = "http://localhost:8080" + '/api/v1/verifycode/generate'
    r = requests.get(url=verify_url)
    r = requests.post(url=url, headers=headers,
                      data=data, verify=False)

    if r.status_code == 200:
        data = r.json().get("data")
        uid = data.get("userId")
        token = data.get("token")
        headers["Authorization"] = f"Bearer {token}"
        print(f"login success, uid: {uid}")
        print(f"login success, token: {token}")
        return True
    else:
        print("login failed")
        return False

def send_a_request(request_info, response_log_path="./temp_log.txt"):
    """
    Construct and send an HTTP request.
    """
    # Parse request information
    flow_id = request_info.get("flow_id")
    flow_span_id = request_info.get("flow_span_id")
    http_method = request_info.get("http_method").upper()
    http_url = request_info.get("http_url")
    http_body = request_info.get("http_body")

    log = f"flow_id {flow_id} flow_span_id {flow_span_id}\n"

    # Extract service name
    parts = http_url.split("http://")
    service_name = parts[1].split("/")[0] if len(parts) > 1 else None
    print(f"Service: {service_name}")
    log += f"Service: {service_name}\n"

    # Set request headers
    global headers, address
    api_index = http_url.find("/api")
    http_url = address + http_url[api_index:]
    print(f"Request: {http_url}")
    log += f"Request: {http_url}\n"

    # Construct request based on HTTP method
    if http_method == "GET":
        response = requests.get(http_url, headers=headers)
    elif http_method == "POST":
        response = requests.post(http_url, headers=headers, json=http_body)
    elif http_method == "PUT":
        response = requests.put(http_url, headers=headers, json=http_body)
    elif http_method == "DELETE":
        response = requests.delete(http_url, headers=headers)
    else:
        raise ValueError("Unsupported HTTP method: {}".format(http_method))

    print(f"Response: {response.json()}")
    log += f"Response: {response.json()}\n\n"
    with open(response_log_path, "a+") as f:
        f.write(log)
    return response


def test_a_pair(pair_info, backup_dir, restore_dir, response_log_path, key):
    """
    Interleaving testing a pari of suspicious requests.
    """
    # List of affected databases
    databases = list(set(pair_info[0]["databases"]))
    service_name_1 = pair_info[1]["http_url"].split("http://")[1].split("/")[0]
    service_name_2 = pair_info[2]["http_url"].split("http://")[1].split("/")[0]

    # 1->2
    with open(response_log_path, "a+") as f:
        f.write(f"{key}/1-2:\n")
    start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6] + 'Z'
    response_1 = send_a_request(pair_info[1], response_log_path)
    response_2 = send_a_request(pair_info[2], response_log_path)
    end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6] + 'Z'
    # Backup and restore databases
    backup_databases(databases, backup_dir + "/1-2")
    restore_databases(databases, restore_dir)
    # Validate-1-Service-Log
    get_docker_logs(service_name_1, start_time, end_time, backup_dir + f"/1-2/{service_name_1}-log.txt")
    get_docker_logs(service_name_2, start_time, end_time, backup_dir + f"/1-2/{service_name_2}-log.txt")

    # 2->1
    with open(response_log_path, "a+") as f:
        f.write(f"\n{key}/2-1\n")
    start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6] + 'Z'
    response_3 = send_a_request(pair_info[2], response_log_path)
    response_4 = send_a_request(pair_info[1], response_log_path)
    end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6] + 'Z'
    # Backup and restore databases
    backup_databases(databases, backup_dir + "/2-1")
    restore_databases(databases, restore_dir)

    # Validate-2-Service-Log
    get_docker_logs(service_name_1, start_time, end_time, backup_dir + f"/2-1/{service_name_1}-log.txt")
    get_docker_logs(service_name_2, start_time, end_time, backup_dir + f"/2-1/{service_name_2}-log.txt")

    # Validate-2-response
    if response_1.json() != response_4.json():
        log = f"There is an inconsistency in request 1."
        print(log)
        with open(response_log_path, "a+") as f:
            f.write(log)
    if response_2.json() != response_3.json():
        log = f"There is an inconsistency in request 2."
        print(log)
        with open(response_log_path, "a+") as f:
            f.write(log)

    # Validate-3-Database
    print("Please validate the databases: " + backup_dir + "/1-2 and " + backup_dir + "/2-1")

def process_a_json(json_file_path, backup_dir, restore_dir, response_log_path):
    with open(json_file_path, "r") as f:
        data = json.load(f)
    for key, value in data.items():
        log = f"\n-----------------Start test pair {key}------------------\n"
        print(log)
        with open(response_log_path, "a+") as f:
            f.write(log)
        test_a_pair(value, backup_dir + f"/{key}", restore_dir, response_log_path, key)
        log = f"\n-----------------Finish test pair {key}------------------\n"
        print(log)
        with open(response_log_path, "a+") as f:
            f.write(log)


def compare_service_log(log_file_path1, log_file_path2):
    """
    Compare the service logs.
    """
    # Read log files and store log levels
    def read_log_levels(file_path):
        with open(file_path, 'r') as file:
            log_entries = file.readlines()
        log_levels = [line.split()[3] for line in log_entries if line.strip()]
        return log_levels

    # Compare log levels of two log files
    def compare_levels(levels1, levels2):
        unique_levels1 = set(levels1)
        unique_levels2 = set(levels2)
        if unique_levels1 != unique_levels2:
            print("Log levels are inconsistent:")
            print("Levels unique to file 1:", unique_levels1 - unique_levels2)
            print("Levels unique to file 2:", unique_levels2 - unique_levels1)
        else:
            print("Log levels in both log files are consistent.")

    # Execute functions
    log_levels1 = read_log_levels(log_file_path1)
    log_levels2 = read_log_levels(log_file_path2)
    compare_levels(log_levels1, log_levels2)


def compare_database_sql(file_path1, file_path2):
    """
    Reads two SQL files, extracts and compares INSERT statements, and prints differences.

    Parameters:
    file_path1 (str): The path to the first SQL file.
    file_path2 (str): The path to the second SQL file.
    """

    def read_sql_file(file_path):
        """Helper function to read the content of a SQL file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Error: The file {file_path} does not exist.")
            return None

    def extract_insert_statements(sql_content):
        """Helper function to extract INSERT statements from SQL content"""
        pattern = re.compile(r'INSERT INTO .*?;', re.DOTALL)
        return pattern.findall(sql_content)

    def compare_statements(statements1, statements2):
        """Helper function to compare differences in INSERT statements between two lists"""
        return list(set(statements1) ^ set(statements2))

    # Read SQL file contents
    sql_content1 = read_sql_file(file_path1)
    sql_content2 = read_sql_file(file_path2)

    if sql_content1 is None or sql_content2 is None:
        return  # Exit the function if the file does not exist or fails to read

    # Extract INSERT statements
    insert_statements1 = extract_insert_statements(sql_content1)
    insert_statements2 = extract_insert_statements(sql_content2)

    # Compare INSERT statements and print differences
    differences = compare_statements(insert_statements1, insert_statements2)
    if differences:
        print("Differences in INSERT statements between the two files:")
        for diff in differences:
            print(diff)
    else:
        print("No differences found in INSERT statements.")


if __name__ == '__main__':
    # Get Token
    login()

    # Read a JSON file
    json_file_path = "f3-re/pairs/candidatePairs_e6aa5a4a-ff99-4cd0-9d30-82c25dab7b53.json"
    backup_dir = "f3-re/json2"
    restore_dir = "f3-re/replay_backup_origin"
    response_log_path = backup_dir + "/response-logs.txt"
    process_a_json(json_file_path, backup_dir, restore_dir, response_log_path)

    # with open(json_file_path, "r") as f:
    #     data = json.load(f)
    # # response = send_a_request(data["0"][1])
    # # # response = build_a_request(data["0"][2])
    # response_1 = send_a_request(data["1"][1])
    #
    # response_2 = send_a_request(data["1"][2])
    # # # response = build_a_request(data["2"][2])
    # # # response = build_a_request(data["2"][2])
    #
    # print(response_1.json)
    # print(response_2.json)
