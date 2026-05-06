from icrawler.builtin import BingImageCrawler

# Blast disease extra images
crawler = BingImageCrawler(storage={"root_dir": "dataset/blast"})
crawler.crawl(keyword="millet blast infected leaf close up", max_num=20)

# Rust disease extra images
crawler = BingImageCrawler(storage={"root_dir": "dataset/rust"})
crawler.crawl(keyword="millet rust disease infected leaf", max_num=20)

# Healthy leaf extra images
crawler = BingImageCrawler(storage={"root_dir": "dataset/healthy"})
crawler.crawl(keyword="healthy green millet leaf close up", max_num=20)

# Downy mildew extra images
crawler = BingImageCrawler(storage={"root_dir": "dataset/downy_mildew"})
crawler.crawl(keyword="millet downy mildew infected leaf close up", max_num=20)

print("Extra images downloaded")