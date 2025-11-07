import os
import sys
import json
import logging
import pdfplumber
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure basic logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class DataIngestion:
    def __init__(self):
        self.raw_data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw_pdfs')
        self.output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'jee_ingestion_data.json')
        self.image_output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'images')
        
        # Ensure image directory exists
        os.makedirs(self.image_output_dir, exist_ok=True)
    
    def save_parsed_data(self, data):
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Parsed element data saved to: {self.output_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving parsed data: {e}")
            return False
    
    def load_parsed_data(self):
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"📂 Loaded {len(data)} papers from cached element file: {self.output_path}")
                return data
            except Exception as e:
                logging.error(f"Error loading parsed data: {e}")
                return None
        return None

    def process_single_pdf(self, pdf_path, file):
        """
        Processes a single PDF, extracting all text words and images
        with their coordinates. Saves images to disk.
        
        Args:
            pdf_path (str): Path to the PDF file
            file (str): Filename
            
        Returns:
            dict: Paper data with elements, or None if processing fails
        """
        try:
            paper_data = {
                "source_file": file,
                "pages": []
            }
            
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_data = {
                        "page_number": i + 1,
                        "elements": []
                    }

                    # 1. Extract text words with coordinates
                    for word in page.extract_words(use_text_flow=True):
                        page_data["elements"].append({
                            "type": "text",
                            "text": word["text"],
                            "x0": word["x0"],
                            "top": word["top"],
                            "x1": word["x1"],
                            "bottom": word["bottom"]
                        })

                    # 2. Extract images, save them, and store their paths
                    for img_index, img in enumerate(page.images):
                        # Create a unique, clean filename
                        img_basename = os.path.splitext(file)[0]
                        img_filename = f"{img_basename}_page_{i+1}_img_{img_index}.png"
                        img_path_rel = os.path.join('images', img_filename) # Relative path
                        img_path_abs = os.path.join(self.image_output_dir, img_filename)
                        
                        try:
                            # Crop the image from the page and save it
                            img_obj = page.crop(
                                (img["x0"], img["top"], img["x1"], img["bottom"])
                            )
                            img_obj.to_image().save(img_path_abs, format="PNG")
                            
                            # Add image element to our data
                            page_data["elements"].append({
                                "type": "image",
                                "path": img_path_rel, # Store the relative path
                                "x0": img["x0"],
                                "top": img["top"],
                                "x1": img["x1"],
                                "bottom": img["bottom"]
                            })
                        except Exception as e:
                            logging.warning(f"Could not save image {img_index} from {file} page {i+1}: {e}")

                    # Sort all elements on the page by their vertical position (top)
                    # then by horizontal (x0). This reconstructs the reading order.
                    page_data["elements"].sort(key=lambda e: (e["top"], e["x0"]))
                    
                    paper_data["pages"].append(page_data)
            
            return paper_data
            
        except Exception as e:
            logging.error(f"Error processing {file}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def initiate_data_ingestion(self, max_files=None, max_workers=1, use_cache=True):
        if use_cache:
            cached_data = self.load_parsed_data()
            if cached_data:
                return cached_data
        
        all_papers_data = [] 
        pdf_files = []
        for root, dirs, files in os.walk(self.raw_data_path):
            for file in files:
                if file.endswith(".pdf"):
                    pdf_path = os.path.join(root, file)
                    pdf_files.append((pdf_path, file))
        
        if max_files:
            pdf_files = pdf_files[:max_files]
        
        print(f"📁 Found {len(pdf_files)} PDF file(s) to process")
        print(f"🚀 Processing sequentially for stability\n")
        
        # Process sequentially instead of parallel to avoid crashes
        for pdf_path, file in tqdm(pdf_files, desc="Processing PDFs", unit="file"):
            paper_data = self.process_single_pdf(pdf_path, file)
            if paper_data and paper_data["pages"]:
                all_papers_data.append(paper_data)
        
        self.save_parsed_data(all_papers_data)
        return all_papers_data

if __name__ == "__main__":
    print("🔧 Starting Data Ingestion...\n")
    ingestion = DataIngestion()
    # Process all PDFs
    parsed_data = ingestion.initiate_data_ingestion(max_files=None, use_cache=False)
    
    if parsed_data:
        total_pages = sum(len(paper['pages']) for paper in parsed_data)
        total_elements = sum(len(elem) for paper in parsed_data for page in paper['pages'] for elem in page['elements'])
        print(f"\n✅ Data Ingestion complete!")
        print(f"📊 Total papers processed: {len(parsed_data)}")
        print(f"📄 Total pages extracted: {total_pages}")
        print(f"🔤 Total elements extracted: {total_elements}")
    else:
        print("\n❌ Data Ingestion failed!")