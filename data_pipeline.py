import os
import re
import hashlib
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
from models import ScrapeLog

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset')
TARGET_SIZE = (224, 224)

# The 22 targeted classes
DISEASE_CLASSES = [
    "Healthy", "Blast", "Downy_Mildew", "Rust", "Leaf_Spot", "Smut", "Ergot",
    "Anthracnose", "Grain_Mold", "Cercospora_Leaf_Spot", "Helminthosporium_Leaf_Blight",
    "Bacterial_Leaf_Blight", "Bacterial_Stripe", "Mosaic_Disease", "Leaf_Curl_Virus",
    "Shoot_Fly_Damage", "Stem_Borer_Damage", "Aphid_Attack", "Armyworm_Damage",
    "Nitrogen_Deficiency", "Potassium_Deficiency", "Zinc_Deficiency"
]

def get_search_queries(disease_class):
    """Generate search queries for a specific millet disease class."""
    base_name = disease_class.replace("_", " ")
    if disease_class == "Healthy":
        return ["healthy pearl millet crop", "healthy finger millet leaves"]
    elif "Deficiency" in disease_class:
        return [f"millet {base_name}", f"millet {base_name} leaves"]
    elif "Damage" in disease_class or "Attack" in disease_class:
        return [f"millet {base_name}", f"pearl millet {base_name}"]
    else:
        return [f"millet {base_name} disease", f"pearl millet {base_name} disease symptoms"]

def fetch_image_urls_bing(query, max_results=10):
    """Scrape image URLs using Bing Images as a public source."""
    url = f"https://www.bing.com/images/search?q={requests.utils.quote(query)}&FORM=HDRSC2"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=3)
        # Regex to find image URLs in the Bing HTML source
        # Usually they are inside m="{...murl:\"(http...)\"...}"
        matches = re.findall(r'murl&quot;:&quot;(.*?)&quot;', response.text)
        if not matches:
             # Fallback regex if the format varies
             matches = re.findall(r'murl":"(.*?)"', response.text)
        
        valid_urls = []
        for match in matches:
            if match.lower().endswith(('.jpg', '.jpeg', '.png')) and "http" in match:
                valid_urls.append(match)
            if len(valid_urls) >= max_results:
                break
        
        return list(set(valid_urls))[:max_results]
    except Exception as e:
        print(f"Error fetching URLs for query '{query}': {list}")
        return []

def get_image_hash(image):
    """Calculate MD5 hash of an Image object."""
    return hashlib.md5(image.tobytes()).hexdigest()

def ensure_class_dir(disease_class):
    class_dir = os.path.join(DATASET_DIR, disease_class)
    os.makedirs(class_dir, exist_ok=True)
    return class_dir

def get_existing_hashes():
    """Returns a set of hashes for all currently downloaded images to prevent duplicates."""
    hashes = set()
    for root, _, files in os.walk(DATASET_DIR):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(root, file)
                try:
                    img = Image.open(filepath)
                    hashes.add(get_image_hash(img))
                except:
                    pass
    return hashes

def download_and_process_image(url, disease_class, existing_hashes):
    """
    Downloads an image, validates it, resizes it, checks for duplicates,
    and saves it to the appropriate dataset folder.
    Returns (status, local_path).
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=2)
        
        if response.status_code != 200:
            return "failed", None
            
        img = Image.open(BytesIO(response.content)).convert('RGB')
        
        # Check if too small
        if img.width < 50 or img.height < 50:
            return "corrupt", None
            
        img = img.resize(TARGET_SIZE)
        img_hash = get_image_hash(img)
        
        if img_hash in existing_hashes:
            return "duplicate", None
            
        existing_hashes.add(img_hash)
        
        # Save image
        class_dir = ensure_class_dir(disease_class)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        filename = f"{disease_class}_{timestamp}.jpg"
        local_path = os.path.join(class_dir, filename)
        
        img.save(local_path, "JPEG", quality=90)
        
        # Relative path for DB storage
        db_path = f"dataset/{disease_class}/{filename}"
        return "downloaded", db_path

    except Exception as e:
        return "corrupt", None

def run_pipeline(limit_per_class=10):
    """
    Main function to execute the data collection pipeline.
    """
    os.makedirs(DATASET_DIR, exist_ok=True)
    existing_hashes = get_existing_hashes()
    
    total_downloaded = 0
    total_failed = 0
    total_duplicates = 0
    
    from app import app
    from models import db
    
    with app.app_context():
        for disease_class in DISEASE_CLASSES:
            print(f"Collecting images for class: {disease_class}")
            ensure_class_dir(disease_class)
            
            queries = get_search_queries(disease_class)
            
            downloaded_for_class = 0
            for query in queries:
                if downloaded_for_class >= limit_per_class:
                    break
                    
                print(f"  Searching: {query}")
                urls = fetch_image_urls_bing(query, max_results=limit_per_class*2)
                
                for url in urls:
                    if downloaded_for_class >= limit_per_class:
                        break
                        
                    # Check if URL already in DB for this execution run (basic check)
                    existing_log = ScrapeLog.query.filter_by(image_url=url).first()
                    if existing_log and existing_log.status == 'downloaded':
                        total_duplicates += 1
                        continue

                    status, local_path = download_and_process_image(url, disease_class, existing_hashes)
                    
                    if status == "downloaded":
                        downloaded_for_class += 1
                        total_downloaded += 1
                    elif status == "failed":
                        total_failed += 1
                    elif status == "duplicate":
                        total_duplicates += 1
                    elif status == "corrupt":
                        total_failed += 1
                        
                    # Log to database
                    log = ScrapeLog(
                        disease_class=disease_class,
                        image_url=url,
                        local_path=local_path,
                        status=status
                    )
                    db.session.add(log)
                    db.session.commit()
                    
        print(f"Pipeline finished. Downloaded: {total_downloaded}, Failed: {total_failed}, Duplicates: {total_duplicates}")
        return {
            "downloaded": total_downloaded,
            "failed": total_failed,
            "duplicates": total_duplicates
        }

if __name__ == "__main__":
    run_pipeline(limit_per_class=2)
