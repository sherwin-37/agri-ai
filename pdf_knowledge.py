import math
import re
from collections import Counter

import pymupdf


TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u0B80-\u0BFF]+", re.IGNORECASE)
BLOCK_HEADING_PATTERN = re.compile(
    r"^\s*(?:[#*]+\s*)?(?:\d+[.)]\s*)?([A-Za-z][A-Za-z -]{2,40}?)\s+Block\s*[:*]?\s*$",
    re.IGNORECASE,
)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "can", "could", "do",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of",
    "on", "or", "should", "the", "there", "this", "to", "under", "what",
    "when", "where", "which", "with", "would", "you", "your",
}
ALIASES = {
    "sivagangai": "sivaganga",
    "sivaganga": "sivaganga",
    "kalayarkoil": "kalayarkovil",
    "kalayarkovil": "kalayarkovil",
    "kalal": "kallal",
    "kallal": "kallal",
    "irrigate": "irrigation",
    "irrigated": "irrigation",
    "irrigating": "irrigation",
    "irrigat": "irrigation",
    "rice": "paddy",
    "sow": "sowing",
    "sown": "sowing",
    "treat": "treatment",
    "treated": "treatment",
    "rotate": "rotation",
    "rotated": "rotation",
    "rotating": "rotation",
    "pests": "pest",
    "insects": "insect",
}
QUERY_EXPANSIONS = {
    "irrigation": "water application schedule moisture wet dry",
    "seed": "seed treatment sowing priming rhizobium phosphobacteria",
    "treatment": "seed treatment sowing priming rhizobium phosphobacteria",
    "rotation": "crop rotation intercrop sequence season crop family",
    "pest": "insect disease management control monitoring",
    "insect": "pest disease management control monitoring",
    "compost": "farmyard manure FYM vermicompost organic matter decomposed",
    "fertilizer": "nutrient nitrogen phosphorus potassium NPK soil test manure compost",
    "nutrient": "fertilizer nitrogen phosphorus potassium NPK soil test manure compost",
}


def tokenize(text: str) -> list[str]:
    words = []
    for word in TOKEN_PATTERN.findall(text.lower()):
        word = ALIASES.get(word, word)
        if word.endswith("ies") and len(word) > 4:
            word = word[:-3] + "y"
        elif word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
            word = word[:-1]
        if word.endswith("ing") and len(word) > 5:
            word = word[:-3]
        elif word.endswith("ed") and len(word) > 4:
            word = word[:-2]
        word = ALIASES.get(word, word)
        if word not in STOP_WORDS:
            words.append(word)
    return words


def load_pdf_chunks(pdf_path: str, words_per_chunk: int = 220, overlap: int = 45) -> list[dict]:
    chunks = []
    document = pymupdf.open(pdf_path)
    current_block = ""

    def add_chunk_group(page_number: int, block: str, words: list[str]) -> None:
        block_context = f"Block context: {block}\n" if block else ""
        start = 0
        while start < len(words):
            end = min(start + words_per_chunk, len(words))
            chunk_text = " ".join(words[start:end])
            indexed_text = block_context + chunk_text
            terms = tokenize(indexed_text)
            if terms:
                chunks.append({
                    "page": page_number,
                    "text": indexed_text,
                    "terms": terms,
                })
            if end == len(words):
                break
            start = end - overlap

    try:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text", sort=True).replace("\x00", " ").strip()
            group_words = []
            page_block = current_block
            for line in text.splitlines():
                heading_match = BLOCK_HEADING_PATTERN.match(line.strip())
                if heading_match:
                    add_chunk_group(page_number, page_block, group_words)
                    group_words = []
                    current_block = heading_match.group(1).strip()
                    page_block = current_block
                group_words.extend(line.split())
            add_chunk_group(page_number, page_block, group_words)
    finally:
        document.close()
    return chunks


def retrieve_relevant_chunks(question: str, chunks: list[dict], limit: int = 6) -> list[dict]:
    query_terms = set(tokenize(question))
    if not query_terms or not chunks:
        return []

    non_crop_topics = {
        "fertilizer", "nutrient", "irrigation", "compost", "pest", "insect",
        "disease", "seed", "treatment", "rotation",
    }
    crop_selection_terms = {"crop", "grow", "suitable", "cultivation", "plant"}
    is_crop_selection_question = bool(query_terms.intersection(crop_selection_terms))
    is_other_topic_question = bool(query_terms.intersection(non_crop_topics))

    if "sivaganga" in query_terms and is_crop_selection_question and not is_other_topic_question:
        query_terms.update(tokenize("district paddy groundnut pulse millet"))
    if "kalayarkovil" in query_terms and is_crop_selection_question and not is_other_topic_question:
        query_terms.update(tokenize("groundnut sesame millet pulse"))
    if "kallal" in query_terms and is_crop_selection_question and not is_other_topic_question:
        query_terms.update(tokenize("groundnut millet sesame pulse mango cashew guava"))
    for term in tuple(query_terms):
        if term in QUERY_EXPANSIONS:
            query_terms.update(tokenize(QUERY_EXPANSIONS[term]))

    document_count = len(chunks)
    term_document_counts = Counter(
        term for chunk in chunks for term in set(chunk["terms"])
    )
    average_length = sum(len(chunk["terms"]) for chunk in chunks) / document_count
    scores = []

    for index, chunk in enumerate(chunks):
        frequencies = Counter(chunk["terms"])
        length = len(chunk["terms"])
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            document_frequency = term_document_counts[term]
            inverse_frequency = math.log(
                1 + (document_count - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            score += inverse_frequency * (
                frequency * 2.2
                / (frequency + 1.2 * (0.25 + 0.75 * length / average_length))
            )
        if score > 0:
            scores.append((score, index))

    scores.sort(reverse=True)
    selected = []
    selected_pages = set()
    for _, index in scores:
        chunk = chunks[index]
        if chunk["page"] in selected_pages:
            continue
        selected.append(chunk)
        selected_pages.add(chunk["page"])
        if len(selected) == limit:
            break
    return selected