from lib.daemon import BlogDaemon

print("scraper startup")
daemon = BlogDaemon(1, "+산후도우미 +후기", 60 * 5)
daemon.init_daemon()
daemon.run()
