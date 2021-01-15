import datetime
from dateutil.relativedelta import relativedelta

import time
import requests
import json
import re
import kss

from abc import ABCMeta, abstractmethod
from selenium import webdriver

from urllib.parse import urlsplit, urlparse
from bs4 import BeautifulSoup


class Scraper(metaclass=ABCMeta):
    SEARCH_URL = ''

    FAKE_HEADER = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36'
    }
    REQUEST_SLEEP_TIME = 1

    @abstractmethod
    def init_scraper_by_type(self):
        pass

    @abstractmethod
    def scrap_detail(self, raw_url):
        pass

    @abstractmethod
    def search_post(self, start, date_from, date_to):
        pass

    @staticmethod
    def date_parse(raw_date):
        raw_date = raw_date.replace(' ', '')
        post_date = raw_date.split('.')

        if len(post_date) == 1:
            date = datetime.datetime.now()
            date = date - datetime.timedelta(days=1)
            date = datetime.datetime(year=date.year, month=date.month, day=date.day)

        else:
            date = datetime.datetime(year=int(post_date[0]), month=int(post_date[1]), day=int(post_date[2]))

        return date

    @staticmethod
    def parse_article_main(raw_text):
        raw_text = re.sub(r'\\x..', r' ', raw_text)
        raw_text = re.sub(r'\\u....', r' ', raw_text)
        raw_text = raw_text.replace(u'\xa0', u' ')
        raw_text = raw_text.replace(u'\ufeff', u' ')
        raw_text = raw_text.replace(u'\u200b', u' ')
        raw_text = raw_text.replace(u'\n', u' ')
        raw_text = " ".join(raw_text.split())

        parse_text = "\n".join(kss.split_sentences(raw_text))

        return parse_text

    def __init__(self, search_query):
        self.search_query = search_query
        self.init_scraper_by_type()

    def year_scraping(self, start_year, end_year):
        url_list = []
        for cur_year in range(start_year, end_year + 1):
            for month in range(1, 13):
                cur_date = datetime.datetime(cur_year, month, 1)
                next_date = cur_date + relativedelta(months=1) - datetime.timedelta(days=1)

                date_from = f'{cur_date:%Y%m%d}'
                date_to = f'{next_date:%Y%m%d}'

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

    def traverse_url(self, article_num, date_from, date_to):
        start = 1
        urls_set = set()
        while article_num > len(urls_set):
            print(f"{len(urls_set)} / {article_num}")
            time.sleep(Scraper.REQUEST_SLEEP_TIME)

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
                    f.write(f'{raw_url}\n')

        return parse_list


class BlogScraper(Scraper):
    BLOG_URL = 'https://blog.naver.com/PostView.nhn'

    def init_scraper_by_type(self):
        BlogScraper.SEARCH_URL = 'https://s.search.naver.com/p/blog/search.naver'  #: 검색조건 설정

    def blog_post(self, raw_url):
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

            res = requests.get(BlogScraper.BLOG_URL, params=values, headers=BlogScraper.FAKE_HEADER)

            html_data = BeautifulSoup(res.text, 'html.parser')
            html_data = html_data.prettify(formatter='html')

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
            'post_blogurl': 'blog.naver.com',
            'post_blogurl_without': None,
            'dup_remove': 1,
            'start': start,  # start page
            'nso': f'a:t,p:from{date_from}to{date_to}',
        }

        try:
            res = requests.get(BlogScraper.SEARCH_URL, params=values, headers=BlogScraper.FAKE_HEADER)

            return json.loads(res.text.strip()[1:-1])

        except Exception as e:
            print(e)
            return None

    def scrap_detail(self, raw_url):
        time.sleep(BlogScraper.REQUEST_SLEEP_TIME)

        blog_id, content_id, html = self.blog_post(raw_url)

        if html is None:
            return None
        try:
            nickname = html.find('meta', property="naverblog:nickname").attrs["content"]
            post_title = html.find('meta', property="og:title").attrs["content"]

        except:  # 게시글 삭제처리
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
                    'writer_id': blog_id,
                    'content_id': content_id,
                    'post_title': post_title,
                    'post_day': str(cur_date),
                    'nickname': nickname,
                    'parse_text': self.parse_article_main(target.get_text(' ')),
                    'html': str(target)
                }

                return result_data

        print(f'ERROR: parse_fail {blog_id}/{content_id}')
        return None


class CafeScraper(Scraper):
    def cafe_post(self, raw_url):
        try:
            self.driver.get(raw_url)
            time.sleep(CafeScraper.REQUEST_SLEEP_TIME * 2)

            self.driver.switch_to.frame('cafe_main')

            html_data: BeautifulSoup = BeautifulSoup(self.driver.page_source, 'html.parser')
            # html_data = BeautifulSoup(html_data.prettify(formatter='html'), 'html.parser')

            url_info = urlparse(raw_url)
            cafe_id, content_id = url_info.path[1:].split('/')  # ex) '/imsanbu/53910553'

            return cafe_id, content_id, html_data

        except Exception as e:
            print("ERROR: blog_post Fail")
            print(e)
            return None

    def init_scraper_by_type(self):
        CafeScraper.SEARCH_URL = 'https://s.search.naver.com/p/cafe/search.naver'  #: 검색조건 설정
        driver_path = '/usr/local/bin/chromedriver'

        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('windows-size=1920x1080')
        options.add_argument('disable-gpu')
        options.add_argument('lang=ko_KR')
        options.add_argument(f'user-agent={Scraper.FAKE_HEADER["User-Agent"]}')

        self.driver = webdriver.Chrome(driver_path, options=options)

    def __del__(self):
        self.driver.quit()

    def scrap_detail(self, raw_url):
        cafe_id, content_id, html = self.cafe_post(raw_url)

        assert isinstance(html, BeautifulSoup)
        nickname = html.find('a', class_='nickname').text.strip()
        post_title = html.find('div', class_='ArticleTitle').find('h3', class_='title_text').text.strip()

        target = html.find('div', class_="se-main-container")
        target = html.find('div', class_="article_viewer") if target is None else target

        cur_date = html.find('div', class_="article_info").find('span', class_='date').text.strip()
        cur_date = self.date_parse(cur_date)

        # TODO 댓글 파싱기능 넣기.

        result_data = {
            'cafe_id': cafe_id,
            'content_id': content_id,
            'post_title': post_title,
            'post_day': str(cur_date),
            'nickname': nickname,
            'parse_text': self.parse_article_main(target.get_text(' ')),
            'html': str(target)
        }

        return result_data


    def search_post(self, start, date_from, date_to):
        values = {
            'where': 'article',
            'sm': 'tab_viw.cafe',
            'query': self.search_query,
            'start': start,
            'dup_remove': 1,
            'nso': f'a:t,p:from{date_from}to{date_to}',
            'prmore': 1
        }

        try:
            res = requests.get(CafeScraper.SEARCH_URL, params=values, headers=CafeScraper.FAKE_HEADER)

            return json.loads(res.text.strip()[1:-1])

        except Exception as e:
            print(e)
            return None



if __name__ == "__main__":
    blog = BlogScraper("+산후도우미 +후기")

    result = blog.extract_post("20201101", "20201101")
    # result = blog.search_post(1, "20200909", "20200910")
    # result = blog.year_scraping(2010, 2020)
    #
    # with open('data_set.json', 'r', encoding='cp949') as f:
    #     result = json.load(f)
