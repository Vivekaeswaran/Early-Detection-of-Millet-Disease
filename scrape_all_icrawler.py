from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
import os

DISEASE_CLASSES = [
    "Healthy", "Blast", "Downy_Mildew", "Rust", "Leaf_Spot", "Smut", "Ergot",
    "Anthracnose", "Grain_Mold", "Cercospora_Leaf_Spot", "Helminthosporium_Leaf_Blight",
    "Bacterial_Leaf_Blight", "Bacterial_Stripe", "Mosaic_Disease", "Leaf_Curl_Virus",
    "Shoot_Fly_Damage", "Stem_Borer_Damage", "Aphid_Attack", "Armyworm_Damage",
    "Nitrogen_Deficiency", "Potassium_Deficiency", "Zinc_Deficiency"
]

def get_search_queries(disease_class):
    base_name = disease_class.replace("_", " ")
    if disease_class == "Healthy":
        return [("healthy pearl millet crop", 25), ("healthy finger millet leaves", 25)]
    elif "Deficiency" in disease_class:
        return [(f"millet {base_name}", 25), (f"millet {base_name} leaves", 25)]
    elif "Damage" in disease_class or "Attack" in disease_class:
        return [(f"millet {base_name}", 25), (f"pearl millet {base_name}", 25)]
    else:
        return [(f"millet {base_name} disease", 25), (f"pearl millet {base_name} disease symptoms", 25)]

def scrape_images():
    for disease_class in DISEASE_CLASSES:
        print(f"--- Scraping for {disease_class} ---")
        dataset_dir = os.path.join("dataset", disease_class)
        os.makedirs(dataset_dir, exist_ok=True)
        
        queries = get_search_queries(disease_class)
        for keyword, count in queries:
            print(f"Scraping {count} images for '{keyword}' in {dataset_dir}...")
            
            # Using Google and Bing to maximize chances of getting enough good images
            try:
                # Bing Crawler
                bing_crawler = BingImageCrawler(storage={"root_dir": dataset_dir}, downloader_threads=4)
                bing_crawler.crawl(keyword=keyword, max_num=count)
                
                # Google Crawler
                google_crawler = GoogleImageCrawler(storage={"root_dir": dataset_dir}, downloader_threads=4)
                google_crawler.crawl(keyword=keyword, max_num=count)

                # Log to database
                from app import app
                from models import db, ScrapeLog
                with app.app_context():
                    log = ScrapeLog(
                        disease_class=disease_class,
                        image_url=keyword, # Using keyword as proxy for URL in this context
                        local_path=dataset_dir,
                        status='completed'
                    )
                    db.session.add(log)
                    db.session.commit()

            except Exception as e:
                print(f"Error scraping {keyword}: {e}")

if __name__ == '__main__':
    scrape_images()
    print("Scraping completed.")
