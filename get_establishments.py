import json
from fuzzywuzzy import fuzz
from spellchecker import SpellChecker
from typing import List

def get_establishments(user_input: str) -> List[str]:
    """
    Searches a JSON file of establishments using fuzzy string matching.

    Args:
        user_input: A string representing the user's search query.

    Returns:
        A list of strings representing the names of the establishments that match the 
        search query.
    """

    # Load JSON data
    with open('stores.json') as f:
        data = json.load(f)

    # Create spell checker instance
    spell = SpellChecker()

    # Define search function
    def fuzzy_search(query_text):
        # Define fields to search
        fields = ['name', 'description', 'cuisine']

        # Use process.extractBests to find matching documents
        matches = []
        for doc in data:
            score = max([fuzz.token_set_ratio(query_text.lower(), 
                                              doc[field].lower()) for field in fields])
            if score > 70:
                matches.append((doc, score))

        # Sort matches by score
        matches = sorted(matches, key=lambda x: x[1], reverse=True)

        return [match[0] for match in matches]

    # Define function to generate alternative searches
    def generate_alternatives(query_text):
        # Split query text into words
        words = query_text.split()

        # Generate alternative searches
        alternatives = []
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                alternative = ' '.join(words[:i] + words[j:])
                alternatives.append(alternative)

        # Use spell checker to generate additional alternatives
        spell_alternatives = []
        for alternative in alternatives:
            misspelled_words = spell.unknown(alternative.split())
            for word in misspelled_words:
                corrections = spell.correction(word)
                for correction in corrections.split():
                    corrected_alternative = alternative.replace(word, correction)
                    if corrected_alternative not in alternatives:
                        spell_alternatives.append(corrected_alternative)

        return alternatives + spell_alternatives

    # Search for matching documents
    query = user_input
    results = fuzzy_search(query)

    # Generate alternative searches if no results are found
    if len(results) == 0:
        alternatives = generate_alternatives(query)
        for alternative in alternatives:
            results = fuzzy_search(alternative)
            if len(results) > 0:
                break

    # Format matching documents as a numbered list
    formatted_results = []
    for i, result in enumerate(results):
        if i >= 3:
            break
        formatted_result = f"{i+1}. {result['name']} ({result['cuisine']}): {result['description']} \n"  # noqa: E501
        formatted_results.append(formatted_result)

    # Create final string by joining formatted results
    final_string = "\n".join(formatted_results)

    return final_string