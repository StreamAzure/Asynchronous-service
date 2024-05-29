from object import *
from utils.io import print_red, print_blue, print_green, read_request_flows, print_flow_by_id

if __name__ == '__main__':
    data_dir = './output'
    request_flow_file = data_dir + '/request_flows.pkl'

    flows = read_request_flows(request_flow_file)
    for flow_id, flow in flows.items():
        print_flow_by_id(flows, flow_id)

    