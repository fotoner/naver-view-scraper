import datetime
from dateutil.relativedelta import relativedelta

import time
import requests
import json
import re
import kss

from abc import ABCMeta, abstractmethod
from selenium import webdriver

from urllib.parse import urlsplit, urlparse, parse_qs
from bs4 import BeautifulSoup


class Scraper(metaclass=ABCMeta):
    SEARCH_URL = ''

    FAKE_HEADER = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
    }
    REQUEST_SLEEP_TIME = 1

    @abstractmethod
    def scrap_detail(self, raw_url):
        pass

    @abstractmethod
    def init_scraper_by_type(self):
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

    def __init__(self, search_query, name_include=True):
        self.search_query = search_query
        self.init_scraper_by_type()
        self.name_include = name_include

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

            html = BeautifulSoup(res.text, 'html.parser')
            html_data = html.prettify(formatter='html')

            raw_blog_number: str = html_data[html_data.find('blogNo') + 6:]
            blog_number = raw_blog_number[raw_blog_number.find("'") + 1: raw_blog_number.find(";") - 1]

            return blog_id, content_id, blog_number, html

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
            'nso': f'{"a:t," if self.name_include else ""}p:from{date_from}to{date_to}',
        }

        try:
            res = requests.get(BlogScraper.SEARCH_URL, params=values, headers=BlogScraper.FAKE_HEADER)

            return json.loads(res.text.strip()[1:-1])

        except Exception as e:
            print(e)
            return None


    def scrap_comment(self, raw_url, content_id, group_id):
        cur_header = BlogScraper.FAKE_HEADER.copy()
        cur_header['referer'] = raw_url

        api_url = 'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json'
        values = {
            'ticket': 'blog',
            'pool': 'cbox9',
            '_callback': 'Res',
            'lang': 'ko',
            'objectId': f'{group_id}_201_{content_id}',
            'pageSize': 50,
            'indexSize': 10,
            'groupId': group_id,
            'listType': 'OBJECT',
            'pageType': 'default',
            'page': 1,
            'initialize': 'true',
            'useAltSort': 'true',
            'replyPageSize': 10,
            'showReply': 'true'
        }

        try:
            res = requests.get(api_url, params=values, headers=cur_header)
            json_dict = json.loads(res.text.strip()[4:-2])

        except Exception as e:
            print(e)
            return []

        if json_dict['code'] != '1000':
            return []

        comments = json_dict['result']['commentList']

        result = [{
            'username': item['userName'] if not item['secret'] else None,
            'user_id': item['profileUserId'] if not item['secret'] else None,
            'is_secret': item['secret'],
            'is_delete': item['deleted'],
            'is_reply': item['replyLevel'] == 2,
            'contents': item['contents'],
            'sticker': item['stickerId'] if item['stickerId'] else None,
            'image': item['imageList'][0]['thumbnail'] if item['imageList'] else None
        } for item in comments]

        result.reverse()

        return result

    def scrap_detail(self, raw_url):
        time.sleep(BlogScraper.REQUEST_SLEEP_TIME)

        blog_id, content_id, blog_number, html = self.blog_post(raw_url)
        comments = self.scrap_comment(raw_url, content_id, blog_number)

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
                    'html': str(target),
                    'comments': comments
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

            cafe_intro = html_data.find("a", class_="link_board")
            query_dict = parse_qs(urlparse(cafe_intro.attrs["href"]).query)
            cafe_id = query_dict['search.clubid'][0]

            url_info = urlparse(raw_url)
            cafe_name, content_id = url_info.path[1:].split('/')  # ex) '/imsanbu/53910553'
            query_dict = parse_qs(url_info.query)
            art = query_dict['art'][0]

            return cafe_name, content_id, art, cafe_id, html_data

        except Exception as e:
            print("ERROR: blog_post Fail")
            print(e)
            return None


    def scrap_info(self, art, cafe_id, content_id):
        api_url = f"https://apis.naver.com/cafe-web/cafe-articleapi/cafes/{cafe_id}/articles/{content_id}/comments/pages/1"
        values = {
            'art': art,
        }

        try:
            res = requests.get(api_url, params=values)
            json_dict = json.loads(res.text)

        except Exception as e:
            print(e)
            return None

        return json_dict

    def init_scraper_by_type(self):
        CafeScraper.SEARCH_URL = 'https://s.search.naver.com/p/cafe/search.naver'  #: 검색조건 설정
        driver_path = './chromedriver'

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
        cafe_name, content_id, art, cafe_id, html = self.cafe_post(raw_url)

        assert isinstance(html, BeautifulSoup)
        target = html.find('div', class_="se-main-container")
        target = html.find('div', class_="article_viewer") if target is None else target

        article_info = self.scrap_info(art, cafe_id, content_id)
        raw_comments = article_info['comments']['items']

        comment_list = [{
            'username': item['writer']['nick'],
            'user_id': item['writer']['id'],
            'is_secret': False,
            'is_deleted': item['isDeleted'],
            'is_reply': item['isRef'],
            'contents': item['content'],
            'sticker': item['image']['url'] if 'image' in item else None,
            'image': item['sticker']['url'] if 'sticker' in item else None,
        } for item in raw_comments]


        result_data = {
            'cafe_name': article_info['cafe']['name'],
            'cafe_id': article_info['cafe']['id'],
            'cafe_url': article_info['cafe']['url'],
            'content_id': content_id,
            'post_title': article_info['article']['subject'],
            'post_day': datetime.datetime.fromtimestamp(article_info['article']['writeDate']/1000),
            'nickname': article_info['article']['writer']['nick'],
            'user_id': article_info['article']['writer']['id'],
            'parse_text': self.parse_article_main(target.get_text(' ')),
            'html': str(target),
            'comment_list': comment_list
        }

        return result_data


    def search_post(self, start, date_from, date_to):
        values = {
            'where': 'article',
            'sm': 'tab_viw.cafe',
            'query': self.search_query,
            'start': start,
            'dup_remove': 1,
            'nso': f'{"a:t," if self.name_include else ""}p:from{date_from}to{date_to}',
            'prmore': 1
        }

        try:
            res = requests.get(CafeScraper.SEARCH_URL, params=values, headers=CafeScraper.FAKE_HEADER)

            return json.loads(res.text.strip()[1:-1])

        except Exception as e:
            print(e)
            return None


if __name__ == "__main__":
    blog = BlogScraper("+밀리시타")

    result = blog.extract_post("20201101", "20201111")
