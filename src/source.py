"""Simple test script before refactoring"""
import re
from wiktionaryparser import WiktionaryParser
from bs4 import BeautifulSoup
from urllib.request import urlopen
import pandas as pd

LANGUAGE = "english"
WHITESPACE = re.compile(r"\s+")
NON_ALNUM = re.compile(r"[^\w\s]")
PARSER = WiktionaryParser()


def get_page(url: str) -> BeautifulSoup:
    """Open the url given and return a BeautifulSoup object"""
    html = urlopen(url)
    bs = BeautifulSoup(html.read(), "html.parser")
    return bs


def get_wiki_body(bs: BeautifulSoup) -> str:
    """Takes a BeautifulSoup object of a Wikipedia page and returns the
    main body of text"""
    body = bs.find(id="bodyContent")
    return body.get_text()


def remove_punctuation(string) -> str:
    """Remove punctuation from string"""
    return NON_ALNUM.sub("", string)


def get_words(body: str) -> list:
    """Split a string of text into individual words (naive)"""
    words = WHITESPACE.split(body)
    return words


def _query_wiktionary(word) -> str:
    """Query Wiktionary for the definition of word"""
    entry = PARSER.fetch(word, language=LANGUAGE)

    # If an empty list is returned then there is a Wiktionary page but no entry under English
    if entry == []:
        print(f"No {LANGUAGE} definition found for: '{word}'")
        return None

    # Just return the first definition for now
    first_entry = entry[0]
    definitions = first_entry["definitions"]

    try:
        first_major_def = definitions[0]
    except IndexError:
        print(f"No definition found for: '{word}'")
        return None

    text = first_major_def["text"]
    first_minor_def = text[1]

    return first_minor_def


def query_wiktionary(word) -> str:
    """Try lowercase if first attempt doesn't find a definition"""
    result = _query_wiktionary(word)
    if result is None:
        lower = word.lower()
        if lower != word:
            result = _query_wiktionary(lower)
    return result


def as_flashcard(row: pd.Series) -> str:
    """Take in a DataFrame row with 'word' and 'definition' columns available and create a
    line representing an Anki flashcard (trivial)"""
    return "{0.word}; {0.definition}".format(row)


def write_out(series: pd.Series, loc: str) -> None:
    """Write out the flashcard series as a .txt file to be imported into Anki!"""
    with open(loc, "w") as f:
        f.write("\n".join(series.values))


def remove_common(df, top=5000):
    """Remove words from df which occur in the top n most common English words"""
    common = pd.read_csv("../data/english_10000.csv").head(n=top)
    mask = df["word"].isin(common["word"])
    mask |= df["word"].str.lower().isin(common["word"])
    return df[~mask]
