from datetime import datetime
import pytz

import json
from fuzzywuzzy import fuzz, process
from spellchecker import SpellChecker

def get_establishments(user_input: str) -> str:
    """
    Searches a JSON file of establishments using fuzzy string matching.

    Args:
        user_input: A string representing the user's search query.

    Returns:
        A string representing the establishments that match the search query, formatted as a numbered list.
    """

    # Load JSON data
    with open('stores.json') as f:
        data = json.load(f)

    # Create spell checker instance
    spell = SpellChecker()

    # Define function to fuzzy search list of dictionaries based on multiple fields
    def fuzzy_search(query_text, list_of_dicts):
        query_text = query_text.lower().strip()
        fields = ['name', 'description', 'cuisines', 'category']

        def search_dict(search_string, my_dict):
            for field in fields:
                if field not in my_dict:
                    continue
                if my_dict[field] is not None and search_string in my_dict[field]:
                    return True
            return False
        
        ratio_threshold = 70
        matches = [x for x in list_of_dicts if search_dict(query_text, x) or
                   (fuzz.token_set_ratio(query_text, x[field]) >= ratio_threshold
                    if (field in x and x[field] is not None) else False
                    for field in fields)]
        matches = sorted(matches, key=lambda x: fuzz.token_set_ratio(query_text, x['name']), reverse=True)
        return [match for match in matches]

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

        # Generate lists of establishments that match each alternative query
        establishment_lists = []
        for alt_query in alternatives + spell_alternatives:
            try:
                establishment_lists.append(fuzzy_search(alt_query, data))
            except (TypeError, ValueError):
                pass

        # Flatten the list of establishment lists into a single list of establishments
        flattened_list = [establishment for sublist in establishment_lists for establishment in sublist]

        # Remove duplicates from the list of establishments
        final_list = [dict(tupleized) for tupleized in set(tuple(establishment.items()) for establishment in flattened_list)]

        return final_list
    
    # Find list of matching establishments
    matching_establishments = fuzzy_search(user_input, data)
    if not matching_establishments:
        # Look for exact name match case-insensitively
        matching_establishments = [establishment for establishment in data if establishment['name'].lower() == user_input.lower()]
        # If no exact name match, look for partial matches based on fuzzy search of multiple fields
        if not matching_establishments:
            alt_establishments = generate_alternatives(user_input)
            # Filter establishments to only include matches that have a name
            alt_establishments = [establishment for establishment in alt_establishments if 'name' in establishment]
            matching_establishments = fuzzy_search(user_input, alt_establishments)
            if not matching_establishments:
                # If no matching establishments were found, return an empty list
                return 'No matches found.'
            
    # Format results as a numbered list
    final_strings = []
    for i, establishment in enumerate(matching_establishments[:1]):
        name = establishment['name']
        cuisine = ', '.join(establishment.get('cuisines', []))
        rating = establishment.get('rating', '-')
        website = establishment.get('website', '-')
        formatted_hours = '-'
        
        # Get opening hours for the current day of week (in user's timezone)
        now = datetime.now(pytz.utc).astimezone()
        weekday = now.strftime('%A')
        hours_data = establishment.get('hours', [])
        hours_list = []
        for hours_string in hours_data:
            day_string, hours_string = hours_string.split(': ')
            if weekday in day_string:
                formatted_hours = hours_string
            hours_list.append(f'{day_string.capitalize()}: {hours_string}')
        formatted_hours = '\n'.join(hours_list)

        # Construct the formatted string for this establishment
        numbered_name = f'{i+1}. 🍔 {" ".join(word.capitalize() for word in name.split())}:'
        numbered_cuisine = f'🍽️ Cuisine: {cuisine.capitalize()}'
        numbered_rating = f'⭐️ Rating: {rating}'
        numbered_website = f'👾 Website: {website}'
        numbered_hours = f'🕥 Hours: {formatted_hours}'
    
    formatted_establishment = '\n'.join([
        numbered_name,
        numbered_cuisine, numbered_rating, numbered_website, numbered_hours])
    final_strings.append(formatted_establishment)

    # If no matching establishments were found,
    if not final_strings:
        return 'No matches found.'

    # Create final string by joining formatted results
    final_string = '\n\n'.join(final_strings)

    return final_string