from lib.scraper import BlogScraper

blog = BlogScraper("+코로나")
result = blog.extract_post("202103014", "202103024")
