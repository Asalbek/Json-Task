import json
import logging
import re
from typing import Dict, Any, Tuple
import fitz  

PDF_PATH = "book.pdf" 

logging.basicConfig(level=logging.INFO)

class StructureExtractor:
    """
    Extracts the structure of a PDF document (book) from its table of contents.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_structure(self) -> Dict[str, Any]:
        """Extract the structure from the table of contents of the PDF."""
        doc = fitz.open(self.pdf_path)
        toc = doc.get_toc()

        structure = {}
        current_chapter = None

        for level, title, page in toc:
            if level == 1:
                current_chapter, chapter_title = self._parse_chapter(title)
                if current_chapter:  # Only add if a valid chapter number was found
                    structure[current_chapter] = {"title": chapter_title, "sections": {}}
                else:
                    logging.warning(f"Invalid chapter title encountered: {title}")
            else:
                section_num, section_title = self._parse_section(title) if current_chapter else ("", "")
                if current_chapter:
                    self._add_section_to_structure(structure, current_chapter, level, section_num, section_title)

        return structure

    def _add_section_to_structure(self, structure: Dict[str, Any], chapter: str, level: int, section_num: str, section_title: str):
        """Add sections or subsections to the structure."""
        if self._is_section(section_num):
            # Ensure the section number is a valid key
            structure[chapter]["sections"][section_num] = {"title": section_title, "subsections": {}}
        elif self._is_subsection(section_num):
            # Get the most recently added section to add the subsection to
            section_keys = list(structure[chapter]["sections"].keys())
            if section_keys:
                current_section_key = section_keys[-1]  # Get the last added section key
                structure[chapter]["sections"][current_section_key]["subsections"][section_num] = {"title": section_title}
            else:
                logging.warning(f"No valid section found for subsection: {section_title}")
        else:
            logging.warning(f"Invalid section number format: {section_num}")

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text by removing extra whitespace."""
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_chapter(self, title: str) -> Tuple[str, str]:
        """Parse chapter number and title from the given title string."""
        # Updated regex pattern to match common chapter formats
        match = re.match(r'^(Глава\s+)?(\d+)\.?\s*(.*)', title, re.IGNORECASE)
        if match:
            return match.group(2), self._clean_text(match.group(3))
        else:
            logging.warning(f"Unexpected chapter title format: {title}")
            return self._clean_text(title), self._clean_text(title)

    def _parse_section(self, title: str) -> Tuple[str, str]:
        """Parse section number and title from the given title string."""
        # Updated regex pattern to match common section formats
        match = re.match(r'^(\d+(\.\d+)*\.?)\s+(.*)', title)
        if match:
            return match.group(1), self._clean_text(match.group(3))
        logging.warning(f"Unexpected section title format: {title}")
        return "", self._clean_text(title)

    @staticmethod
    def _is_section(section_num: str) -> bool:
        """Determine if the section number is valid."""
        return re.match(r'^\d+(\.\d+)?\.?$', section_num) is not None

    @staticmethod
    def _is_subsection(section_num: str) -> bool:
        """Determine if the subsection number is valid."""
        return re.match(r'^\d+\.\d+\.\d+\.?$', section_num) is not None


def save_json(data: Dict[str, Any], output_path: str) -> None:
    """Save the data to a JSON file."""
    with open(output_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)  # noqa


if __name__ == "__main__":
    extractor = StructureExtractor(PDF_PATH)
    struct = extractor.extract_structure()

    output_json = 'book_structure.json'
    save_json(struct, output_json)
    logging.info(f"Saved the structure to {output_json}.")
