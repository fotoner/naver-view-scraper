from lib.scraper import CafeScraper
import json



blog = CafeScraper("+산후도우미 +후기")
result = blog.extract_post("20210114", "20210114")

print(json.dumps(result, ensure_ascii=False))


