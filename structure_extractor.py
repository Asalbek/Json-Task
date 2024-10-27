import json
import logging
import re
from typing import Dict, Any, Tuple

import pymupdf as fitz

PDF_PATH = "book.pdf"  # replace with the path to the PDF book

logging.basicConfig(level=logging.INFO)


class StructureExtractor:
    """
    Extracts the structure of a PDF document (book) from its table of contents.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_structure(self) -> Dict[str, Any]:
        doc = fitz.open(self.pdf_path)
        toc = doc.get_toc()  # noqa

        structure = {}
        current_chapter = None
        current_section = None

        for level, title, page in toc:
            chapter_num, chapter_title = self._parse_chapter(title) if level == 1 else ("", "")
            section_num, section_title = self._parse_section(title) if level in [2, 3] and current_chapter else ("", "")

            if chapter_num:
                current_chapter = chapter_num
                structure[current_chapter] = {"title": chapter_title, "sections": {}}
                if not chapter_title:
                    next_item = toc[toc.index([level, title, page]) + 1] if toc.index(
                        [level, title, page]) + 1 < len(toc) else None
                    structure[current_chapter]["title"] = self._clean_text(next_item[1]) if next_item else ""
            elif section_num:
                if self._is_section(section_num):
                    current_section = section_num
                    structure[current_chapter]["sections"][current_section] = {"title": section_title,
                                                                               "subsections": {}}
                elif self._is_subsection(section_num) or (level == 3 and current_section):
                    if current_section:
                        structure[current_chapter]["sections"][current_section]["subsections"][section_num] = {
                            "title": section_title}

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


def save_json(data: Dict[str, Any], output_path: str) -> None:
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)  # noqa


if __name__ == "__main__":
    extractor = StructureExtractor(PDF_PATH)
    struct = extractor.extract_structure()

    output_json = 'book_structure.json'
    save_json(struct, output_json)
    logging.info(f"Saved the structure to {output_json}.")
