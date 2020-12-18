from lib.naver_blog import BlogScraper
import json

blog = BlogScraper("+산후도우미 +후기")
result = blog.extract_post("20201101", "20201101")

print(json.dumps(result, ensure_ascii=False))