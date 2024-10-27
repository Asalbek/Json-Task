import json
import logging
import re
from typing import Dict, Any, Tuple

import fitz  # PyMuPDF

PDF_PATH = "book.pdf"  # replace with the path to the PDF book

logging.basicConfig(level=logging.INFO)


class StructureExtractor:
    """
    Extracts the structure and content of a PDF document (book) based on its table of contents.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_structure(self) -> Dict[str, Any]:
        doc = fitz.open(self.pdf_path)
        toc = doc.get_toc()

        structure = {}
        current_chapter = None
        current_section = None

        for level, title, page in toc:
            chapter_num, chapter_title = self._parse_chapter(title) if level == 1 else ("", "")
            section_num, section_title = self._parse_section(title) if level in [2, 3] and current_chapter else ("", "")

            if chapter_num:
                current_chapter = chapter_num
                structure[current_chapter] = {
                    "title": chapter_title,
                    "start_page": page - 1,  # PyMuPDF pages are 0-based
                    "sections": {}
                }
            elif section_num:
                if self._is_section(section_num):
                    current_section = section_num
                    structure[current_chapter]["sections"][current_section] = {
                        "title": section_title,
                        "start_page": page - 1,
                        "subsections": {}
                    }
                elif self._is_subsection(section_num) and current_section:
                    structure[current_chapter]["sections"][current_section]["subsections"][section_num] = {
                        "title": section_title,
                        "start_page": page - 1
                    }

        doc.close()
        return structure

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_chapter(self, title: str) -> Tuple[str, str]:
        match = re.match(r'(Глава\s*)?(\d+)\.?\s*(.*)', title, re.IGNORECASE)
        if match:
            return match.group(2), self._clean_text(match.group(3))
        return "", self._clean_text(title)

    def _parse_section(self, title: str) -> Tuple[str, str]:
        match = re.match(r'^(\d+(\.\d+)*\.?)\s+(.*)', title)
        if match:
            return match.group(1), self._clean_text(match.group(3))
        return "", self._clean_text(title)

    @staticmethod
    def _is_section(section_num: str) -> bool:
        return re.match(r'^\d+(\.\d+)?\.?$', section_num) is not None

    @staticmethod
    def _is_subsection(section_num: str) -> bool:
        return re.match(r'^\d+\.\d+\.\d+\.?$', section_num) is not None

    def extract_content(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        doc = fitz.open(self.pdf_path)

        for i, (chapter_num, chapter_data) in enumerate(structure.items()):
            start_page = chapter_data['start_page']
            next_chapter_start = structure.get(str(int(chapter_num) + 1), {}).get('start_page', doc.page_count)
            end_page = next_chapter_start

            chapter_content = self._get_content(doc, start_page, end_page)
            structure[chapter_num]["content"] = chapter_content
            logging.info(f"Extracted content for Chapter {chapter_num}: {chapter_data['title']}")

            for section_num, section_data in chapter_data["sections"].items():
                section_start_page = section_data['start_page']
                next_section_start = self._get_next_section_start(chapter_data["sections"], section_num, end_page)
                section_end_page = min(next_section_start, end_page)

                section_content = self._get_content(doc, section_start_page, section_end_page)
                structure[chapter_num]["sections"][section_num]["content"] = section_content

                for subsection_num, subsection_data in section_data["subsections"].items():
                    subsection_start_page = subsection_data['start_page']
                    next_subsection_start = self._get_next_section_start(section_data["subsections"], subsection_num, section_end_page)
                    subsection_end_page = min(next_subsection_start, section_end_page)

                    subsection_content = self._get_content(doc, subsection_start_page, subsection_end_page)
                    structure[chapter_num]["sections"][section_num]["subsections"][subsection_num]["content"] = subsection_content

        doc.close()
        return structure

    def _get_next_section_start(self, sections, current_num, default_end_page):
        """
        Gets the start page of the next section or subsection by finding the next sequential key.
        """
        section_numbers = sorted(sections.keys(), key=lambda x: list(map(int, x.split('.'))))
        try:
            current_index = section_numbers.index(current_num)
            next_section_num = section_numbers[current_index + 1]
            return sections[next_section_num]["start_page"]
        except (IndexError, KeyError, ValueError):
            return default_end_page

    def _get_content(self, doc, start_page: int, end_page: int) -> str:
        content = []
        for page_num in range(start_page, end_page):
            page = doc[page_num]
            content.append(page.get_text())
        return "\n".join(content)


def save_json(data: Dict[str, Any], output_path: str) -> None:
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    extractor = StructureExtractor(PDF_PATH)
    structure = extractor.extract_structure()
    logging.info("Structure extracted from TOC successfully.")

    structured_content = extractor.extract_content(structure)
    logging.info("Completed organizing text structure.")

    output_json = 'structured_book_content.json'
    save_json(structured_content, output_json)
    logging.info(f"Saved structured content to {output_json}.")
