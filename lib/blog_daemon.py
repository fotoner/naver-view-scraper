import time
import datetime
import threading
from lib.naver_blog import BlogScraper
from lib.blog_endpoint import *


class BlogDaemon(threading.Thread):
    def __init__(self, query_id, query, refresh_interval=60 * 5):
        self.scraper = BlogScraper(query)
        self.id = query_id

        self.refresh_interval = refresh_interval
        threading.Thread.__init__(self, name="BlogDaemon")
        self.setDaemon(True)
        self.result = []



    def init_daemon(self):
        prev_date = self.get_prev_date()
        cur_date = datetime.datetime.now()

        if prev_date.year == 2010:
            print(datetime.datetime.now(), "update all")
            data_list = self.scraper.year_scraping(prev_date.year, cur_date.year)
            send_all(data_list)

        else:
            print(datetime.datetime.now(), "update previous")
            day_delta = datetime.timedelta(days=1)
            cur_date -= day_delta

            while (prev_date := prev_date + day_delta) <= cur_date:
                data_list = self.extract_days(prev_date, prev_date)
                if len(data_list) != 0:
                    send_all(data_list)

                print()


    def extract_days(self, prev_date, next_date):
        prev_str = "%d%02d%02d" % (prev_date.year, prev_date.month, prev_date.day)
        next_str = "%d%02d%02d" % (next_date.year, next_date.month, next_date.day)

        print(datetime.datetime.now(), prev_str + " / " + next_str)

        data_list = self.scraper.extract_post(prev_str, next_str)

        return data_list

    def get_prev_date(self):
        data = get_lastday()

        raw_str = data['lastday'].split('T')[0]
        date_raw = list(map(int, raw_str.split('-')))
        prev_date = datetime.datetime(date_raw[0], date_raw[1], date_raw[2])

        return prev_date

    def run(self):
        day_delta = datetime.timedelta(days=1)

        while True:
            prev_date = self.get_prev_date()
            now = datetime.datetime.now()

            print(time.ctime(), end=" ")
            if prev_date.day != (now - day_delta).day:
                now -= day_delta
                print(datetime.datetime.now(), "Update Post")

                prev_str = "%d%02d%02d" % (now.year, now.month, now.day)

                self.extract_result(prev_str)

                print(datetime.datetime.now(), "Update finish")

            else:
                print(datetime.datetime.now(), "pass")
            time.sleep(self.refresh_interval)

    def extract_result(self, str_date):
        data_list = self.scraper.extract_post(str_date, str_date)
        if len(data_list) != 0:
            send_all(data_list)
        else:
            print("extract size is 0")


# if __name__ == "__main__":
#     pass
#     daemon = BlogDaemon(1, "+산후도우미 +후기", 60)
#     daemon.run()
#     # daemon.start()
