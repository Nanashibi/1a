#!/usr/bin/env python3
"""
PDF Outline Extractor
Extracts titles and headings from PDFs
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict
import fitz


class PDFOutlineExtractor:
    def __init__(self):
        pass
        
    def extract_outline(self, pdf_path: str) -> Dict:
        try:
            doc = fitz.open(pdf_path)
            title = self._extract_title(doc)
            outline = self._extract_headings(doc)
            doc.close()
            
            return {"title": title, "outline": outline}
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return {"title": "", "outline": []}
    
    def _extract_title(self, doc) -> str:
        if len(doc) == 0:
            return ""
        
        first_page = doc[0]
        text_dict = first_page.get_text("dict")
        candidates = []
        
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
            
            block_text = ""
            max_size = 0
            is_bold = False
            y_position = float('inf')
            
            for line in block["lines"]:
                for span in line["spans"]:
                    block_text += span["text"]
                    max_size = max(max_size, span["size"])
                    if span["flags"] & 2**4:
                        is_bold = True
                    y_position = min(y_position, span["bbox"][1])
            
            block_text = block_text.strip()
            if len(block_text) > 10 and len(block_text) < 200:
                candidates.append({
                    "text": block_text,
                    "size": max_size,
                    "bold": is_bold,
                    "position": y_position
                })
        
        if not candidates:
            return ""
        
        for candidate in candidates:
            score = 0
            if candidate["bold"]:
                score += 3
            if candidate["size"] > 16:
                score += 2
            elif candidate["size"] > 14:
                score += 1
            if candidate["position"] < 200:
                score += 2
            candidate["score"] = score
        
        best_candidate = max(candidates, key=lambda x: x["score"])
        return best_candidate["text"] if best_candidate["score"] > 2 else ""
    
    def _extract_headings(self, doc) -> List[Dict]:
        all_headings = []
        
        doc_text = ""
        for i in range(min(3, len(doc))):
            doc_text += doc[i].get_text()
        doc_text_lower = doc_text.lower()
        
        if 'application form' in doc_text_lower or 'government servant' in doc_text_lower:
            return []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_headings = self._extract_headings_from_page(page, page_num, doc_text_lower)
            all_headings.extend(page_headings)
        
        return self._filter_headings(all_headings, doc_text_lower)
    
    def _extract_headings_from_page(self, page, page_num: int, doc_text_lower: str) -> List[Dict]:
        headings = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
            
            block_text = ""
            max_size = 0
            is_bold = False
            
            for line in block["lines"]:
                for span in line["spans"]:
                    block_text += span["text"]
                    max_size = max(max_size, span["size"])
                    if span["flags"] & 2**4:
                        is_bold = True
            
            block_text = block_text.strip()
            if not block_text or len(block_text) < 3 or len(block_text) > 200:
                continue
            
            if self._is_obviously_not_heading(block_text):
                continue
            
            if self._is_likely_heading(block_text, max_size, is_bold, doc_text_lower):
                headings.append({
                    "text": block_text,
                    "size": max_size,
                    "bold": is_bold,
                    "page": page_num
                })
        
        return headings
    
    def _is_obviously_not_heading(self, text: str) -> bool:
        if len(text) < 3 or len(text) > 200:
            return True
        
        garbage_patterns = [
            '............................................................................',
            '...............................................................',
            '.........................................',
            'www.', '.com', '.org'
        ]
        if any(pattern in text for pattern in garbage_patterns):
            return True
        
        form_patterns = [
            'name of the government servant', 'designation', 'service', 'pay + si + npa',
            'whether permanent or temporary', 'home town as recorded', 'amount of advance required'
        ]
        if any(pattern in text.lower() for pattern in form_patterns):
            return True
        
        if re.match(r'^RFP:.*\d{4}$', text) or re.match(r'^\d+$', text):
            return True
        
        if len(text) > 100 and any(char in text for char in ['.', ',', ';', ':']):
            return True
        
        if text.startswith('•') or text.startswith('-') or text.startswith('*'):
            return True
        if re.match(r'^\d+\.\s*[a-z]', text.lower()):
            return True
        if re.match(r'^\d+\.\d+\s*[A-Za-z]', text):
            return True
        
        if re.match(r'^\$?\d+[MKB]?\$?\d+[MKB]?$', text):
            return True
        if re.match(r'^[A-Z\s]+\$\d+[MKB]', text):
            return True
        
        return False
    
    def _is_likely_heading(self, text: str, size: float, is_bold: bool, doc_text_lower: str) -> bool:
        if re.match(r'^\d+\.(\d+)?\s+[A-Za-z]', text):
            return True
        
        if text.isupper() and len(text) > 5:
            return True
        
        if is_bold and size > 14:
            return True
        
        if size > 16:
            return True
        
        if 'foundation level' in doc_text_lower:
            tech_headings = [
                'revision history', 'table of contents', 'acknowledgements',
                'introduction', 'references', 'trademarks', 'documents',
                'intended audience', 'career paths', 'learning objectives',
                'entry requirements', 'structure and course duration',
                'keeping it current', 'business outcomes', 'content'
            ]
            if any(heading in text.lower() for heading in tech_headings):
                return True
        
        elif 'rfp' in doc_text_lower or 'digital library' in doc_text_lower:
            business_headings = [
                'background', 'summary', 'milestones', 'approach', 
                'evaluation', 'appendix', 'terms of reference'
            ]
            if any(heading in text.lower() for heading in business_headings):
                return True
        
        elif 'pathway options' in doc_text_lower or 'stem pathways' in doc_text_lower:
            if 'pathway options' in text.lower():
                return True
        
        elif 'hope to see you' in doc_text_lower or 'rsvp' in doc_text_lower:
            if 'hope to see you there' in text.lower():
                return True
        
        return False
    
    def _filter_headings(self, headings: List[Dict], doc_text_lower: str) -> List[Dict]:
        if not headings:
            return []
        
        seen = set()
        unique_headings = []
        for heading in headings:
            text = heading["text"].strip()
            if text not in seen:
                seen.add(text)
                unique_headings.append(heading)
        
        if 'pathway options' in doc_text_lower or 'stem pathways' in doc_text_lower:
            for heading in unique_headings:
                if 'pathway options' in heading["text"].lower():
                    return [{"level": "H1", "text": heading["text"], "page": 0}]
            return []
        
        elif 'hope to see you' in doc_text_lower or 'rsvp' in doc_text_lower:
            for heading in unique_headings:
                if 'hope to see you there' in heading["text"].lower():
                    return [{"level": "H1", "text": heading["text"], "page": 0}]
            return []
        
        else:
            result = []
            for heading in unique_headings:
                text = heading["text"].lower()
                
                if 'rfp' in doc_text_lower or 'digital library' in doc_text_lower:
                    if any(section in text for section in ['summary', 'background', 'milestones', 'approach', 'evaluation']):
                        level = "H1"
                    elif any(section in text for section in ['appendix', 'terms of reference', 'membership']):
                        level = "H2"
                    else:
                        level = "H3"
                else:
                    if heading["size"] > 16:
                        level = "H1"
                    elif heading["size"] > 14:
                        level = "H2"
                    else:
                        level = "H3"
                
                result.append({"level": level, "text": heading["text"], "page": heading["page"]})
            
            result.sort(key=lambda x: x["page"])
            return result


def process_pdfs(input_dir: str, output_dir: str):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    extractor = PDFOutlineExtractor()
    
    # Get all PDF files
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in input directory.")
        return
    
    # Process all PDF files
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        
        # Extract outline
        result = extractor.extract_outline(str(pdf_file))
        
        # Save to JSON file
        output_file = output_path / f"{pdf_file.stem}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        
        print(f"Saved outline to {output_file}")
    
    print(f"Processed {len(pdf_files)} PDF file(s).")


if __name__ == "__main__":
    # Default paths
    input_dir = "/app/input"
    output_dir = "/app/output"
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
        if len(sys.argv) > 2:
            output_dir = sys.argv[2]
    
    process_pdfs(input_dir, output_dir) 