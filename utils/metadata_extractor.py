import re
import spacy
from llama_index.core.extractors import BaseExtractor
from utils.domain_patterns import (
    load_keywords,
    find_titled_people,
    find_pound_amounts,
    find_years_mentioned,
    find_known_organisations,
    find_known_places
)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")
keywords = load_keywords()

def _parse_filename(filename):
    # remove file extensions
    filename = filename.replace(".docx", "").replace(".pdf", "")
    clean_name = filename.strip()
    parts = clean_name.split()

    # file attribute
    year = None
    source = "Unknown"
    article_id = None
    title = clean_name

    # Check if we have enough parts
    if len(parts) > 0:
        first_part = parts[0]

        # Check if it followed the standard of ([year/month/date] [p2]) etc...
        if first_part.isdigit() and len(first_part) == 8:
            # Get the year
            year = ""
            for i in range(4):
                year += first_part[i]
            year = int(year)

            # Look for Article ID
            id_index = None
            for index in range(1, len(parts)):
                if parts[index].isdigit() and len(parts[index]) > 5:
                    id_index = index
                    break

            # Extract the source and title based on where the ID is
            if id_index is not None:
                # The Article ID 
                article_id = parts[id_index]

                # If page exists (like p2) source usually start at index 2
                start_at = 2 if len(parts) > 2 and "p" in parts[1] else 1

                # The Source
                source_parts = []
                for i in range(start_at, id_index):
                    source_parts.append(parts[i])
                source = " ".join(source_parts)

                # The Title
                title_parts = []
                for i in range(id_index + 1, len(parts)):
                    title_parts.append(parts[i])
                title = " ".join(title_parts)
            else:
                # Fall back to use everything after the date as the title
                title_parts = []
                for i in range(1, len(parts)):
                    title_parts.append(parts[i])
                title = " ".join(title_parts)

        return {
            "year": year,
            "source": source if source.strip() else "Unknown",
            "article_id": article_id,
            "title": title.strip()
            
        }
    
def _extract_entities(text):
    # Cap text length
    doc = nlp(text[:10_000])

    # spaCy people
    spacy_people = set(
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ == "PERSON" and len(ent.text.strip()) > 2
    )

    # Domain: titled people
    titled_people = set(find_titled_people(text, keywords["titles"]))

    # Domain: known SA places
    domain_places = set(find_known_places(text, keywords["places"]))

    # spaCy places
    spacy_places = set(
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ in ("GPE", "LOC") and len(ent.text.strip()) > 2
    )

    domain_orgs = set(find_known_organisations(text, keywords["organisations"]))

    # spaCy orgs
    spacy_orgs  = set(
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ == "ORG" and len(ent.text.strip()) > 2
    )

    return {
        "people": sorted(spacy_people | titled_people),
        "places": sorted(domain_places | spacy_places),
        "organisations": sorted(domain_orgs | spacy_orgs),
        "amounts": find_pound_amounts(text),
        "years_mentioned": find_years_mentioned(text),
    }


class MetaDataExtractor(BaseExtractor):
    async def aextract(self, nodes):
        metadata_list = []

        for node in nodes:
            filename = node.metadata.get("file_name", "").strip()
            # remove file extensions
            filename = filename.replace(".docx", "").replace(".pdf", "")
            parts = filename.split()

            # file attribute
            year = None
            source = "Unknown"
            article_id = None
            title = filename

            # Check if it followed the standard of ([year/month/date] [p2]) etc...
            if parts[0].isdigit() and len(parts[0]) == 8:

                # Get year
                year = ""
                count = 0
                for char in parts[0]:
                    if count >= 4:
                        break
                    year += char
                    count += 1
                # type cast to int
                year = int(year)

                # Check for article id
                id_index = None
                for i in range(2, len(parts)):
                    if parts[i].isdigit():
                        id_index = i
                        break

                if id_index is not None:
                    source = " "
                    for i in range(2, id_index):
                        # Add each word before the article id
                        source += parts[i]
                        source += " "

                    # Get article ID
                    article_id = parts[id_index]

                    # Get title
                    title = " "
                    for i in range(id_index + 1, len(parts)):
                        title += parts[i]
                        title += " "

            # If it doesn't follow the naming convention
            # then we'll use the entire length as a name
            else:
                title = filename

            metadata_list.append({
                "year": year,
                "source": source,
                "article_id": article_id,
                "title": title
            })

        return metadata_list