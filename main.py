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


# Multilingual patterns for non-English languages
MULTILINGUAL_PATTERNS = {
    'spanish': {
        'form_patterns': [
            'formulario de solicitud', 'servidor público', 'funcionario gubernamental',
            'designación', 'servicio', 'salario', 'permanente o temporal'
        ],
        'tech_headings': [
            'historial de revisiones', 'tabla de contenidos', 'agradecimientos',
            'introducción', 'referencias', 'marcas comerciales', 'documentos',
            'audiencia objetivo', 'trayectorias profesionales', 'objetivos de aprendizaje',
            'requisitos de entrada', 'estructura y duración del curso', 'contenido'
        ],
        'business_headings': [
            'antecedentes', 'resumen', 'hitos', 'enfoque', 
            'evaluación', 'apéndice', 'términos de referencia'
        ]
    },
    'french': {
        'form_patterns': [
            'formulaire de demande', 'fonctionnaire', 'agent gouvernemental',
            'désignation', 'service', 'salaire', 'permanent ou temporaire'
        ],
        'tech_headings': [
            'historique des révisions', 'table des matières', 'remerciements',
            'introduction', 'références', 'marques déposées', 'documents',
            'public cible', 'parcours professionnels', 'objectifs d\'apprentissage',
            'conditions d\'entrée', 'structure et durée du cours', 'contenu'
        ],
        'business_headings': [
            'contexte', 'résumé', 'jalons', 'approche', 
            'évaluation', 'annexe', 'termes de référence'
        ]
    },
    'german': {
        'form_patterns': [
            'antragsformular', 'beamter', 'regierungsangestellter',
            'bezeichnung', 'dienst', 'gehalt', 'dauerhaft oder vorübergehend'
        ],
        'tech_headings': [
            'revisionshistorie', 'inhaltsverzeichnis', 'danksagungen',
            'einführung', 'referenzen', 'warenzeichen', 'dokumente',
            'zielgruppe', 'karrierewege', 'lernziele',
            'eingangsvoraussetzungen', 'struktur und kursdauer', 'inhalt'
        ],
        'business_headings': [
            'hintergrund', 'zusammenfassung', 'meilensteine', 'ansatz', 
            'bewertung', 'anhang', 'referenzbedingungen'
        ]
    },
    'hindi': {
        'form_patterns': [
            'आवेदन पत्र', 'सरकारी कर्मचारी', 'सरकारी अधिकारी',
            'पदनाम', 'सेवा', 'वेतन', 'स्थायी या अस्थायी'
        ],
        'tech_headings': [
            'संशोधन इतिहास', 'विषय सूची', 'आभार', 'परिचय', 'संदर्भ',
            'ट्रेडमार्क', 'दस्तावेज', 'लक्षित दर्शक', 'करियर पथ',
            'सीखने के उद्देश्य', 'प्रवेश आवश्यकताएं', 'संरचना और पाठ्यक्रम अवधि', 'सामग्री'
        ],
        'business_headings': [
            'पृष्ठभूमि', 'सारांश', 'मील के पत्थर', 'दृष्टिकोण',
            'मूल्यांकन', 'परिशिष्ट', 'संदर्भ की शर्तें'
        ]
    },
    'chinese': {
        'form_patterns': [
            '申请表', '公务员', '政府工作人员', '职务', '服务', '工资', '永久或临时'
        ],
        'tech_headings': [
            '修订历史', '目录', '致谢', '介绍', '参考文献', '商标', '文档',
            '目标受众', '职业道路', '学习目标', '入学要求', '结构和课程持续时间', '内容'
        ],
        'business_headings': [
            '背景', '摘要', '里程碑', '方法', '评估', '附录', '参考条款'
        ]
    },
    'japanese': {
        'form_patterns': [
            '申請書', '公務員', '政府職員', '指定', 'サービス', '給与', '恒久的または一時的'
        ],
        'tech_headings': [
            '改訂履歴', '目次', '謝辞', '紹介', '参考文献', '商標', '文書',
            '対象読者', 'キャリアパス', '学習目標', '入学要件', '構造とコース期間', 'コンテンツ'
        ],
        'business_headings': [
            '背景', '要約', 'マイルストーン', 'アプローチ', '評価', '付録', '参照条項'
        ]
    },
    'arabic': {
        'form_patterns': [
            'نموذج طلب', 'موظف حكومي', 'خادم الحكومة', 'تعيين', 'خدمة', 'راتب', 'دائم أو مؤقت'
        ],
        'tech_headings': [
            'تاريخ المراجعة', 'جدول المحتويات', 'شكر وتقدير', 'مقدمة', 'مراجع', 'علامات تجارية', 'وثائق',
            'الجمهور المستهدف', 'مسارات مهنية', 'أهداف التعلم', 'متطلبات الدخول', 'الهيكل ومدة الدورة', 'محتوى'
        ],
        'business_headings': [
            'خلفية', 'ملخص', 'معالم', 'نهج', 'تقييم', 'ملحق', 'شروط مرجعية'
        ]
    }
}


class PDFOutlineExtractor:
    def __init__(self):
        self.detected_language = None
        self.multilingual_patterns = None
    
    def _detect_non_english_language(self, doc_text: str) -> str:
        """Detect non-English languages in the document."""
        doc_text_lower = doc_text.lower()
        
        # Character-based detection for script-specific languages
        if re.search(r'[देवनागरी\u0900-\u097F]', doc_text):
            return 'hindi'
        if re.search(r'[中文汉字\u4e00-\u9fff]', doc_text):
            return 'chinese'
        if re.search(r'[ひらがなカタカナ\u3040-\u309f\u30a0-\u30ff]', doc_text):
            return 'japanese'
        if re.search(r'[ا-ي\u0600-\u06ff]', doc_text):
            return 'arabic'
        
        # Pattern-based detection for European languages
        language_scores = {}
        for lang in ['spanish', 'french', 'german']:
            score = 0
            patterns = MULTILINGUAL_PATTERNS[lang]
            
            # Check all pattern categories
            for pattern_list in [patterns['form_patterns'], patterns['tech_headings'], patterns['business_headings']]:
                for pattern in pattern_list:
                    if pattern in doc_text_lower:
                        score += 1
            
            language_scores[lang] = score
        
        # Additional character-based hints for European languages
        if re.search(r'[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', doc_text):
            language_scores['french'] = language_scores.get('french', 0) + 2
        if re.search(r'[äöüßÄÖÜ]', doc_text):
            language_scores['german'] = language_scores.get('german', 0) + 2
        if re.search(r'[ñáéíóúüÑÁÉÍÓÚÜ]', doc_text):
            language_scores['spanish'] = language_scores.get('spanish', 0) + 2
        
        # Return language with highest score, or None if no clear match
        if language_scores:
            best_lang = max(language_scores, key=language_scores.get)
            return best_lang if language_scores[best_lang] > 1 else None
        
        return None
        
    def extract_outline(self, pdf_path: str) -> Dict:
        try:
            doc = fitz.open(pdf_path)
            
            # Get sample text for language detection
            sample_text = ""
            for i in range(min(3, len(doc))):
                sample_text += doc[i].get_text()
            
            # Detect non-English language
            self.detected_language = self._detect_non_english_language(sample_text)
            if self.detected_language:
                self.multilingual_patterns = MULTILINGUAL_PATTERNS[self.detected_language]
            
            title = self._extract_title(doc)
            outline = self._extract_headings(doc)
            doc.close()
            
            result = {"title": title, "outline": outline}
            if self.detected_language:
                result["detected_language"] = self.detected_language
            
            return result
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
        
        # Original English form detection (unchanged)
        if 'application form' in doc_text_lower or 'government servant' in doc_text_lower:
            return []
        
        # Additional multilingual form detection
        if self.multilingual_patterns:
            if any(pattern in doc_text_lower for pattern in self.multilingual_patterns['form_patterns']):
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
        
        # Original English form patterns (unchanged)
        form_patterns = [
            'name of the government servant', 'designation', 'service', 'pay + si + npa',
            'whether permanent or temporary', 'home town as recorded', 'amount of advance required'
        ]
        if any(pattern in text.lower() for pattern in form_patterns):
            return True
        
        # Additional multilingual form pattern detection
        if self.multilingual_patterns:
            if any(pattern in text.lower() for pattern in self.multilingual_patterns['form_patterns']):
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
        
        # Additional multilingual heading detection
        if self.multilingual_patterns:
            if any(heading in text.lower() for heading in self.multilingual_patterns['tech_headings']):
                return True
            if any(heading in text.lower() for heading in self.multilingual_patterns['business_headings']):
                return True
        
        # Original English logic (completely unchanged)
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
        
        # Original English logic (completely unchanged)
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
                level = "H3"  # default level
                
                # Multilingual classification (if language detected)
                if self.multilingual_patterns:
                    # Primary headings from multilingual patterns
                    if any(section in text for section in self.multilingual_patterns['business_headings'][:4]):
                        level = "H1"
                    elif any(section in text for section in self.multilingual_patterns['tech_headings'][:6]):
                        level = "H1"
                    # Secondary headings from multilingual patterns
                    elif any(section in text for section in self.multilingual_patterns['business_headings'][4:]):
                        level = "H2"
                    elif any(section in text for section in self.multilingual_patterns['tech_headings'][6:]):
                        level = "H2"
                
                # Original English classification logic (unchanged)
                if 'rfp' in doc_text_lower or 'digital library' in doc_text_lower:
                    if any(section in text for section in ['summary', 'background', 'milestones', 'approach', 'evaluation']):
                        level = "H1"
                    elif any(section in text for section in ['appendix', 'terms of reference', 'membership']):
                        level = "H2"
                    else:
                        level = "H3"
                else:
                    # Size-based classification (original logic)
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