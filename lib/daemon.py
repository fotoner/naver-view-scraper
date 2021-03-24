import time
import datetime
import threading
from lib.scraper import BlogScraper, CafeScraper, Scraper
from lib.endpoint import BlogEndpoint, CafeEndpoint, Endpoint
from abc import *


class Daemon(metaclass=ABCMeta, threading.Thread):
    def __init__(self, query_id, query, refresh_interval=60 * 5):
        self.scraper: Scraper = self.load_scraper(query)
        self.endpoint: Endpoint = self.load_endpoint()
        self.id = query_id

        self.refresh_interval = refresh_interval
        threading.Thread.__init__(self, name=f"Daemon-{query_id}")
        self.setDaemon(True)

    @abstractmethod
    def load_scraper(self, query):
        pass

    @abstractmethod
    def load_endpoint(self):
        pass


    def get_prev_date(self):
        data = self.endpoint.get_last_update()

        raw_str = data['lastday'].split('T')[0]
        date_raw = list(map(int, raw_str.split('-')))
        prev_date = datetime.datetime(date_raw[0], date_raw[1], date_raw[2])

        return prev_date


    def init_daemon(self):
        prev_date = self.get_prev_date()
        cur_date = datetime.datetime.now()

        if prev_date.year == 765:
            print(datetime.datetime.now(), "update all")
            data_list = self.scraper.year_scraping(prev_date.year, cur_date.year)
            self.endpoint.send_all(data_list)

        else:
            print(datetime.datetime.now(), "update previous")
            day_delta = datetime.timedelta(days=1)
            cur_date -= day_delta

            while (prev_date := prev_date + day_delta) <= cur_date:
                data_list = self.extract_days(prev_date, prev_date)
                if len(data_list) != 0:
                    self.endpoint.send_all(data_list)

                print()

    def extract_days(self, prev_date, next_date):
        prev_str = f"{prev_date.year}{prev_date.month:02d}{prev_date.day:02d}"
        next_str = f"{next_date.year}{next_date.month:02d}{next_date.day:02d}"

        print(datetime.datetime.now(), prev_str + " / " + next_str)

        data_list = self.scraper.extract_post(prev_str, next_str)

        return data_list

    def run(self):
        day_delta = datetime.timedelta(days=1)

        while True:
            prev_date = self.get_prev_date()
            now = datetime.datetime.now()

            print(time.ctime(), end=" ")
            if prev_date.day != (now - day_delta).day:
                now -= day_delta
                print(datetime.datetime.now(), "Update Post")
                prev_str = f"{now.year}{now.month:02}{now.day:02}"

                self.extract_result(prev_str)

                print(datetime.datetime.now(), "Update finish")

            else:
                print(datetime.datetime.now(), "pass")
            time.sleep(self.refresh_interval)

    def extract_result(self, str_date):
        data_list = self.scraper.extract_post(str_date, str_date)
        if len(data_list) != 0:
            self.endpoint.send_all(data_list)
        else:
            print("extract size is 0")


class BlogDaemon(Daemon):
    def load_scraper(self, query):
        return BlogScraper(query)

    def load_endpoint(self):
        return BlogEndpoint()


class CafeDaemon(Daemon):
    def load_scraper(self, query):
        return CafeScraper(query)

    def load_endpoint(self):
        return CafeEndpoint()
