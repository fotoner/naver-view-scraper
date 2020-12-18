import requests
import json

API_IP = 'http://192.168.29.252:5000'


def send_all(data_list):
    base_res = send_base(data_list)
    print(base_res.status_code)

    return


def send_base(data):
    res = requests.post(API_IP + '/ml/article/blog/list', json=data)

    return res


def get_lastday():
    res = requests.get(API_IP + '/article/blog/lastday')

    return json.loads(res.text)


if __name__ == "__main__":
    with open('data_set.json', 'r', encoding='cp949') as f:
        data_list = json.load(f)

    send_all(data_list)
