import json
import logging
import re
from pathlib import Path
from typing import Dict, Any

import fitz  # PyMuPDF for PDF handling

from structure_extractor import StructureExtractor

logging.basicConfig(level=logging.INFO)

PDF_PATH = "book.pdf"  # Specify the path to the PDF book here


class PDFBookProcessor:
    """
    Class to process a PDF book by extracting and organizing text according to a specified structure.
    """

    def __init__(self, pdf_path: str, start_page: int = 13):
        self.pdf_path = pdf_path
        self.structure_extractor = StructureExtractor(pdf_path)
        self.structure = self.structure_extractor.extract_structure()
        self.start_page = start_page
        self.text = ''
        self.output_dir = Path(__file__).resolve().parent

    @staticmethod
    def _format_regex(title: str) -> str:
        """Format title into a regex-friendly pattern."""
        return re.escape(title).replace(r'\ ', r'\s*')

    def _store_section_content(self, level_info: Dict[str, str], content: str):
        """Assign text content to the structure based on its level."""
        text_length = len(content.strip())
        chapter = level_info.get('chapter')
        section = level_info.get('section')
        subsection = level_info.get('subsection')

        if level_info['level'] == 'subsection':
            self.structure[chapter]['sections'][section]['subsections'][subsection].update({
                'text': content,
                'length': text_length
            })
        elif level_info['level'] == 'section':
            self.structure[chapter]['sections'][section].update({
                'text': content,
                'length': text_length
            })
        elif level_info['level'] == 'chapter':
            self.structure[chapter].update({
                'text': content,
                'length': text_length
            })

    def _extract_pdf_text(self):
        """Extract text content from the PDF starting at a specified page."""
        with fitz.open(self.pdf_path) as document:
            self.text = "\n".join(
                page.get_text("text") for page in document[self.start_page - 1:]
            )
        logging.info("Extracted text from PDF.")

    def _organize_structure(self):
        """Map extracted text to chapters, sections, and subsections defined in the structure."""
        previous_end = 0
        current_level = {'level': 'start'}

        for chapter_id, chapter_content in self.structure.items():
            chapter_pattern = rf"(?i)Глава\s*{chapter_id}\s*{self._format_regex(chapter_content.get('title', ''))}"
            match = re.search(chapter_pattern, self.text)
            if match:
                self._process_previous_level(current_level, match, previous_end)
                previous_end = match.end()
                current_level = {'level': 'chapter', 'chapter': chapter_id}

                for section_id, section_content in chapter_content.get('sections', {}).items():
                    section_pattern = rf"(?i){section_id}\s*{self._format_regex(section_content.get('title', ''))}"
                    match = re.search(section_pattern, self.text)
                    if match:
                        self._process_previous_level(current_level, match, previous_end)
                        previous_end = match.end()
                        current_level = {'level': 'section', 'chapter': chapter_id, 'section': section_id}

                        for subsection_id, subsection_content in section_content.get('subsections', {}).items():
                            subsection_pattern = rf"(?i){subsection_id}\s*{self._format_regex(subsection_content.get('title', ''))}"
                            match = re.search(subsection_pattern, self.text)
                            if match:
                                self._process_previous_level(current_level, match, previous_end)
                                previous_end = match.end()
                                current_level = {
                                    'level': 'subsection',
                                    'chapter': chapter_id,
                                    'section': section_id,
                                    'subsection': subsection_id
                                }
                            else:
                                logging.warning(f"Subsection '{subsection_id}' not found in text.")
            else:
                logging.warning(f"Chapter '{chapter_id}' not found in text.")

        # Process any remaining text after the last match
        if previous_end < len(self.text):
            self._store_section_content(current_level, self.text[previous_end:])

        logging.info("Completed organizing text structure.")

    def _process_previous_level(self, level_info: Dict[str, str], match, previous_end: int):
        """Handle content assignment for previous level in structure."""
        content = self.text[previous_end:match.start()]
        if content.strip():
            self._store_section_content(level_info, content)

    def process_pdf(self) -> Dict[str, Any]:
        """Process PDF and return structured data."""
        self._extract_pdf_text()
        self._organize_structure()
        return self.structure


def save_to_json(data: Dict[str, Any], file_path: str) -> None:
    """Save processed data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    processor = PDFBookProcessor(PDF_PATH)
    book_structure = processor.process_pdf()

    output_filename = 'structured_book_content.json'
    save_to_json(book_structure, output_filename)
    logging.info(f"Saved structured content to {output_filename}.")
