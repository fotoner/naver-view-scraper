import datetime
from dateutil.relativedelta import relativedelta
import time
import requests
import json

from urllib.parse import urlsplit
from bs4 import BeautifulSoup


class BlogScraper:
    SEARCH_URL = 'https://s.search.naver.com/p/blog/search.naver'  #: 검색조건 설정
    BLOG_URL = 'https://blog.naver.com/PostView.nhn'
    TIME_VALUE_PATH = 'time_value.csv'
    FAKE_HEADER = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36'
    }
    REQUEST_SLEEP_TIME = 1

    def __init__(self, search_query):
        self.search_query = search_query

    @staticmethod
    def get_time_value():
        with open(BlogScraper.TIME_VALUE_PATH, 'r') as f:
            raw_date = f.readline()
        raw_date = raw_date.split(',')

        year = int(raw_date[0])
        month = int(raw_date[1])
        day = int(raw_date[2])

        return year, month, day

    @staticmethod
    def set_time_value(year, month, day):
        with open(BlogScraper.TIME_VALUE_PATH, 'w') as f:
            f.write("%d,%d,%d" % (year, month, day))

    @staticmethod
    def date_parse(raw_date):
        raw_date = raw_date.replace(' ', '')
        post_date = raw_date.split('.')

        if len(post_date) == 1:
            date = datetime.datetime.now()
            date = date - datetime.timedelta(days=1)
            date = datetime.datetime(year=date.year, month=date.month, day=date.day)
            # str_date = "%d-%02d-%02d" % (now.year, now.month, now.day)

        else:
            date = datetime.datetime(year=int(post_date[0]), month=int(post_date[1]), day=int(post_date[2]))
            # str_date = "%s-%02d-%02d" % (post_date[0], int(post_date[1]), int(post_date[2]))

        return date

    @staticmethod
    def blog_post(raw_url):
        try:
            res = requests.get(raw_url, headers=BlogScraper.FAKE_HEADER)
            html_data = BeautifulSoup(res.text, 'html.parser')
            frame = html_data.find('iframe', id='mainFrame')

            if frame is None:
                frame = html_data.find('iframe', id='screenFrame')
                src = frame.attrs['src']

                res = requests.get(src, headers=BlogScraper.FAKE_HEADER)
                html_data = BeautifulSoup(res.text, 'html.parser')
                frame = html_data.find('iframe', id='mainFrame')

            src = frame.attrs['src']

            parse_url = urlsplit(src)
            query = parse_url.query.split('&')

            blog_id = query[0].split('=')[1]
            content_id = query[1].split('=')[1]

            values = {
                'blogId': blog_id,  # 검색 대상(블로그, 웹문서 등)
                'logNo': content_id,  # 문서 id
            }

            res = requests.get(BlogScraper.BLOG_URL, params=values,  headers=BlogScraper.FAKE_HEADER)
            html_data = BeautifulSoup(res.text, 'html.parser')

            return blog_id, content_id, html_data

        except Exception as e:
            print("ERROR: blog_post Fail")
            print(e)
            return None

    def search_post(self, start, date_from, date_to):
        values = {
            'where': 'blog',  # 검색 대상(블로그, 웹문서 등)
            'sm': 'tab_pge',  # ???
            'query': self.search_query,  # 검색할 내용
            'api_type': 1,
            'rev': 43,
            'post_blogurl': 'blog.naver.com',
            'post_blogurl_without': None,
            'dup_remove': 1,
            'start': start,  # start page
            'nso': f'a:t,p:from{date_from}to{date_to}',
            'nlu_query': None,
            'dkey': None,
            'spq': 0
        }
        # print(values)

        try:
            res = requests.get(BlogScraper.SEARCH_URL, params=values, headers=BlogScraper.FAKE_HEADER)

            return json.loads(res.text.strip()[1:-1])

        except Exception as e:
            print(e)
            return None

    def traverse_url(self, article_num, date_from, date_to):
        start = 1
        urls_set = set()
        while article_num > len(urls_set):
            print(f"{len(urls_set)} / {article_num}")
            time.sleep(BlogScraper.REQUEST_SLEEP_TIME)

            cur_data = self.search_post(len(urls_set) + 1, date_from, date_to)
            article_num = int(cur_data['total'])
            cur_data = BeautifulSoup(cur_data['html'], 'html.parser')

            article_link_raw = cur_data.find_all('a', class_="total_tit")

            parse_size = len(article_link_raw)
            start += parse_size

            for i in range(parse_size):
                raw_url = article_link_raw[i].attrs['href']
                try:
                    urls_set.add(f'{raw_url}')
                except:
                    continue

        return urls_set

    def extract_post(self, prev_str, cur_str):
        html_data = self.search_post('1', prev_str, cur_str)
        # print(html_data)
        try:
            article_num = int(html_data['total'])

        except:
            print("article not exist")
            return []

        url_set = self.traverse_url(article_num, prev_str, cur_str)
        url_list = list(url_set)

        return self.url_list_parse(url_list)

    def url_list_parse(self, url_list):
        parse_list = []

        for i, raw_url in enumerate(url_list):
            print(f"[{i + 1} / {len(url_list)}] scrap target: {raw_url}")
            raw_url = raw_url.strip('\n')
            parse_result = self.scrap_detail(raw_url)

            if parse_result is not None:
                parse_list.append(parse_result)
            else:
                with open("fail_case.txt", "a+")as f:
                    f.write("%s\n" % raw_url)

        return parse_list

    def scrap_detail(self, raw_url):
        time.sleep(BlogScraper.REQUEST_SLEEP_TIME)

        writer_id, content_id, html = self.blog_post(raw_url)

        if html is None:
            return None
        try:
            nickname = html.find('meta', property="naverblog:nickname").attrs["content"]
            post_title = html.find('meta', property="og:title").attrs["content"]

        except: # 게시글 삭제처리
            return None

        main = html.find("div", id="post-view" + content_id)

        edit_list = [html.find('div', id="postViewArea"),  # 스마트에디터 1
                     main.find_all('div', class_="se_component_wrap"),  # 스마트에디터 2
                     main.find('div', class_="se-main-container")]  # 스마트에디터3

        date_list = [html.find('p', class_="_postAddDate"),
                     main.find('span', class_="se_publishDate"),
                     main.find('span', class_="se_publishDate")]

        for i, edit in enumerate(edit_list):
            if edit is not None:
                if i == 1:
                    if len(edit) == 0:
                        continue
                    else:
                        target = edit[1]
                else:
                    target = edit

                cur_date = self.date_parse(date_list[i].text)

                result_data = {
                    'writer_id': writer_id,
                    'content_id': content_id,
                    'post_title': post_title,
                    'post_day': str(cur_date),
                    'nickname': nickname,
                    'parse_text': target.text.strip(),
                    'html': str(target)
                }

                return result_data

        print("ERROR: parse_fail %s/%s" % (writer_id, content_id))
        return None


    def year_scraping(self, start_year, end_year):
        url_list = []
        for cur_year in range(start_year, end_year + 1):
            for month in range(1, 13):
                cur_date = datetime.datetime(cur_year, month, 1)
                next_date = cur_date + relativedelta(months=1) - datetime.timedelta(days=1)

                date_from = "%d%02d%02d" % (cur_date.year, cur_date.month, cur_date.day)
                date_to = "%d%02d%02d" % (next_date.year, next_date.month, next_date.day)

                html_data = self.search_post('1', date_from, date_to)
                try:
                    article_num = int(
                        html_data.find('span', class_="title_num").text.split('/')[1].strip()[:-1].replace(',', ''))
                except:
                    continue

                url_set = self.traverse_url(article_num, date_from, date_to)
                cur_list = list(url_set)
                url_list = url_list + cur_list

        return self.url_list_parse(url_list)


if __name__ == "__main__":
    blog = BlogScraper("+산후도우미 +후기")

    result = blog.extract_post("20201101", "20201101")
    # result = blog.search_post(1, "20200909", "20200910")
    # result = blog.year_scraping(2010, 2020)
    #
    # with open('data_set.json', 'r', encoding='cp949') as f:
    #     result = json.load(f)