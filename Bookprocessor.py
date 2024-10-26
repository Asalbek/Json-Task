import json
import logging
import re
from pathlib import Path
from typing import Dict, Any

import pymupdf as fitz  # pip install PyMuPDF

from structure_extractor import StructureExtractor

logging.basicConfig(level=logging.INFO)

PDF_PATH = "book.pdf"  # Replace with the path to the PDF book


class BookProcessor:
    """
    Processes a PDF book by extracting text and organizing content based on the provided structure.
    """

    def __init__(self, pdf_path: str, start_page: int = 13):
        self.pdf_path = pdf_path
        self.structure_extractor = StructureExtractor(pdf_path)
        self.structure = self.structure_extractor.extract_structure()
        self.start_page = start_page
        self.text = ''
        self.current_dir = Path(__file__).resolve().parent

    @staticmethod
    def _prepare_regex(title: str) -> str:
        """Prepare a regex pattern from the title."""
        return re.escape(title).replace('\\ ', '\\s*')

    def _set_section_text(self, level_info: Dict[str, str], section_text: str):
        """Set text and length for the given level in the structure."""
        length = len(section_text.strip())
        level = level_info['level']
        chapter = level_info.get('chapter')
        section = level_info.get('section')
        subsection = level_info.get('subsection')

        if level == 'subsection':
            self.structure[chapter]['sections'][section]['subsections'][subsection]['text'] = section_text
            self.structure[chapter]['sections'][section]['subsections'][subsection]['length'] = length
        elif level == 'section':
            self.structure[chapter]['sections'][section]['text'] = section_text
            self.structure[chapter]['sections'][section]['length'] = length
        elif level == 'chapter':
            self.structure[chapter]['text'] = section_text
            self.structure[chapter]['length'] = length

    def _extract_text(self):
        """Extract text from the PDF starting from the specified page."""
        with fitz.open(self.pdf_path) as doc:
            self.text = '\n'.join(page.get_text("text") for page in doc[self.start_page - 1:])
        logging.info("Text extraction complete.")

    def _match_structure(self):
        """Match the extracted text to the provided structure."""
        prev_match_end = 0
        prev_level = {'level': 'start'}

        for chapter_num, chapter_dict in self.structure.items():
            chapter_regex = rf"(?i)Глава\s*{chapter_num}\s*{self._prepare_regex(chapter_dict.get('title', ''))}"
            if match := re.search(chapter_regex, self.text):
                self._process_match(prev_level, match, prev_match_end)
                prev_match_end = match.end()
                prev_level = {'level': 'chapter', 'chapter': chapter_num}

                for section_num, section_dict in chapter_dict.get('sections', {}).items():
                    section_regex = rf"(?i){section_num}\s*{self._prepare_regex(section_dict.get('title', ''))}"
                    if match := re.search(section_regex, self.text):
                        self._process_match(prev_level, match, prev_match_end)
                        prev_match_end = match.end()
                        prev_level = {'level': 'section', 'chapter': chapter_num, 'section': section_num}

                        for subsection_num, subsection_dict in section_dict.get('subsections', {}).items():
                            subsection_regex = rf"(?i){subsection_num}\s*{self._prepare_regex(subsection_dict.get('title', ''))}"
                            if match := re.search(subsection_regex, self.text):
                                self._process_match(prev_level, match, prev_match_end)
                                prev_match_end = match.end()
                                prev_level = {
                                    'level': 'subsection',
                                    'chapter': chapter_num,
                                    'section': section_num,
                                    'subsection': subsection_num
                                }
                            else:
                                logging.warning(f"No match found for subsection: {subsection_num}")

            else:
                logging.warning(f"No match found for chapter: {chapter_num}")

        # Process any remaining text
        if prev_match_end < len(self.text):
            self._set_section_text(prev_level, self.text[prev_match_end:])

        logging.info("Structure matching complete.")

    def _process_match(self, prev_level: Dict[str, str], match, prev_match_end: int):
        """Process matched text based on the previous level."""
        section_text = self.text[prev_match_end: match.start()]
        if section_text.strip():
            self._set_section_text(prev_level, section_text)

    def process_book(self) -> Dict[str, Any]:
        """Main method to process the book."""
        self._extract_text()
        self._match_structure()
        return self.structure


def save_json(data: Dict[str, Any], output_path: str) -> None:
    """Save data to a JSON file."""
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)  # noqa


if __name__ == "__main__":
    processor = BookProcessor(PDF_PATH)
    response = processor.process_book()

    output_json = 'book_structure_with_text.json'
    save_json(response, output_json)
    logging.info(f"Saved the structure with text to {output_json}.")
