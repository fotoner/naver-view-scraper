import requests
import os
import json
from abc import *
from dotenv import load_dotenv

load_dotenv(dotenv_path='./.env', verbose=True)


class Endpoint(metaclass=ABCMeta):
    def __init__(self):
        self.__API_IP = os.getenv('API_IP')

    def send_all(self, data_list):
        base_res = self.upload_data(data_list)
        print(base_res.status_code)

        return

    @staticmethod
    def send_post(uri, data):
        return requests.post(uri, json=data)

    @staticmethod
    def send_get(uri):
        return requests.get(uri)

    @abstractmethod
    def upload_data(self, data):  # send base
        pass

    @abstractmethod
    def get_last_update(self):  # send base
        pass


class BlogEndpoint(Endpoint):
    def upload_data(self, data):
        uri = f'{self.__API_IP}/ml/blog/list'
        return self.send_post(uri, data)

    def get_last_update(self):
        uri = f'{self.__API_IP}/article/blog/lastday'
        res = self.send_get(uri)
        return json.loads(res.text)


class CafeEndpoint(Endpoint):
    def upload_data(self, data):
        uri = f'{self.__API_IP}/ml/cafe/list'
        return self.send_post(uri, data)

    def get_last_update(self):
        uri = f'{self.__API_IP}/article/cafe/lastday'
        res = self.send_get(uri)
        return json.loads(res.text)
