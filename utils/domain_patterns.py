import json
import os

_KEYWORDS_PATH = os.path.join("utils", "domain_keywords.json")

def load_keywords():
    """Load domain keywords from JSON file."""
    with open(_KEYWORDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def find_titled_people(text, titles):
    """Find people by splitting text and checking for prefix titles."""
    found = set()
    words = text.split()
    
    for i, word in enumerate(words):
        # Clean the word for matching
        clean_word = word.rstrip('.').rstrip(',')
        
        if clean_word in titles and i + 1 < len(words):
            # Grab the next one or two words if they are capitalized
            name_parts = []
            if words[i+1][0].isupper():
                name_parts.append(words[i+1].rstrip(',').rstrip('.'))
                if i + 2 < len(words) and words[i+2][0].isupper():
                    name_parts.append(words[i+2].rstrip(',').rstrip('.'))
            
            if name_parts:
                found.add(f"{clean_word} {' '.join(name_parts)}")
    
    return sorted(list(found))

def find_pound_amounts(text):
    """Find pound amounts by searching for the £ symbol."""
    found = set()
    words = text.split()
    
    for word in words:
        if word.startswith('£'):
            # Remove the £ and any commas, then check if it's a number
            amount = word.replace('£', '').replace(',', '').rstrip('.').rstrip(',')
            if amount.isdigit():
                found.add(f"£{amount}")
    return sorted(list(found))

def find_years_mentioned(text):
    """Find 4-digit years using basic string logic."""
    years = set()
    for word in text.split():
        clean_word = word.strip('.,()[]')
        if len(clean_word) == 4 and clean_word.isdigit():
            year = int(clean_word)
            if 1800 <= year <= 1999:
                years.add(year)
    return sorted(list(years))

def find_known_places(text, places):
    """Check if specific place names exist in the text string."""
    # Using lowercase for a 'cheap' case-insensitive search
    lower_text = text.lower()
    return sorted([place for place in places if place.lower() in lower_text])

def find_known_organisations(text, organisations):
    """Check if specific organizations exist in the text string."""
    lower_text = text.lower()
    return sorted([org for org in organisations if org.lower() in lower_text])