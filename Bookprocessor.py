import json
import logging
import re
from pathlib import Path
from typing import Dict, Any

import pymupdf as fitz  # pip install PyMuPDF

from structure_extractor import StructureExtractor

logging.basicConfig(level=logging.INFO)

PDF_PATH = "book.pdf"  # replace with the path to the PDF book


class BookProcessor:
    """
    Processes a PDF book by extracting text and organizing content based on the provided structure.
    """

    def __init__(
            self,
            pdf_path: str,
            start_page: int = 13
    ):
        self.pdf_path = pdf_path
        self.structure_extractor = StructureExtractor(pdf_path)
        self.structure = self.structure_extractor.extract_structure()
        self.start_page = start_page
        self.text = ''
        self.current_dir = Path(__file__).resolve().parent

    @staticmethod
    def _prepare_regex(title: str) -> str:
        """
        Escapes special characters and replaces spaces with '\\s*' for regex usage.
        """
        return re.escape(title).replace('\\ ', '\\s*')

    def _set_section_text(self, prev_level: dict, section_text: str):
        """
        Sets the text and length for the previous level in the structure.
        """
        length = len(section_text.strip())

        if prev_level['level'] == 'subsection':
            chapter = prev_level['chapter']
            section = prev_level['section']
            subsection = prev_level['subsection']
            self.structure[chapter]['sections'][section]['subsections'][subsection]['text'] = section_text
            self.structure[chapter]['sections'][section]['subsections'][subsection]['length'] = length
        elif prev_level['level'] == 'section':
            chapter = prev_level['chapter']
            section = prev_level['section']
            self.structure[chapter]['sections'][section]['text'] = section_text
            self.structure[chapter]['sections'][section]['length'] = length
        elif prev_level['level'] == 'chapter':
            chapter = prev_level['chapter']
            self.structure[chapter]['text'] = section_text
            self.structure[chapter]['length'] = length

    def _extract_text(self):
        """
        Extracts text from the PDF starting from the specified page.
        """
        text_list = []
        with fitz.open(self.pdf_path) as doc:
            for page_num in range(self.start_page - 1, len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text("text")
                if page_text:
                    text_list.append(page_text)
        self.text = '\n'.join(text_list)
        logging.info("Text extraction complete.")

    def _match_structure(self):
        """
        Matches the text to the provided structure and sets the text for chapters, sections, and subsections.
        """
        prev_match_end = 0
        prev_level = {'level': 'start'}

        for chapter_num, chapter_dict in self.structure.items():
            # Regex for chapter
            chapter_title_regex = self._prepare_regex(chapter_dict.get('title', ''))
            chapter_regex = rf"(?i)Глава\s*{chapter_num}\s*{chapter_title_regex}"
            match = re.search(chapter_regex, self.text)
            if match:
                chapter_start = match.start()
                chapter_end = match.end()
                # Process previous level
                section_text = self.text[prev_match_end:chapter_start]
                if section_text.strip():
                    self._set_section_text(prev_level, section_text)
                prev_match_end = chapter_end
                prev_level = {'level': 'chapter', 'chapter': chapter_num}
            else:
                logging.warning(f"No match found for chapter: {chapter_num}")
                continue

            sections = chapter_dict.get('sections', {})
            for section_num, section_dict in sections.items():
                # Regex for section
                section_title_regex = self._prepare_regex(section_dict.get('title', ''))
                section_regex = rf"(?i){section_num}\s*{section_title_regex}"
                match = re.search(section_regex, self.text)
                if match:
                    section_start = match.start()
                    section_end = match.end()
                    # Process previous level
                    section_text = self.text[prev_match_end:section_start]
                    if section_text.strip():
                        self._set_section_text(prev_level, section_text)
                    prev_match_end = section_end
                    prev_level = {
                        'level': 'section',
                        'chapter': chapter_num,
                        'section': section_num
                    }
                else:
                    logging.warning(f"No match found for section: {section_num}")
                    continue

                subsections = section_dict.get('subsections', {})
                for subsection_num, subsection_dict in subsections.items():
                    # Regex for subsection
                    subsection_title_regex = self._prepare_regex(subsection_dict.get('title', ''))
                    subsection_regex = rf"(?i){subsection_num}\s*{subsection_title_regex}"
                    match = re.search(subsection_regex, self.text)
                    if match:
                        subsection_start = match.start()
                        subsection_end = match.end()
                        # Process previous level
                        section_text = self.text[prev_match_end:subsection_start]
                        if section_text.strip():
                            self._set_section_text(prev_level, section_text)
                        prev_match_end = subsection_end
                        prev_level = {
                            'level': 'subsection',
                            'chapter': chapter_num,
                            'section': section_num,
                            'subsection': subsection_num
                        }
                    else:
                        logging.warning(f"No match found for subsection: {subsection_num}")
                        continue

        # Process the last section
        if prev_match_end < len(self.text):
            section_text = self.text[prev_match_end:]
            self._set_section_text(prev_level, section_text)

        logging.info("Structure matching complete.")

    def process_book(self) -> dict:
        """
        Main method to process the book.
        """
        self._extract_text()
        self._match_structure()
        return self.structure


def save_json(data: Dict[str, Any], output_path: str) -> None:
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)  # noqa


if __name__ == "__main__":
    processor = BookProcessor(PDF_PATH)
    response = processor.process_book()

    output_json = 'book_structure_with_text.json'
    save_json(response, output_json)
    logging.info(f"Saved the structure with text to {output_json}.")
