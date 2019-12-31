"""Classes for reading Wikipedia and breaking into individual words"""
import attr
import pandas as pd
import re
from wiktionaryparser import WiktionaryParser
from bs4 import BeautifulSoup
from urllib.request import urlopen
from typing import Iterable, ClassVar

LANGUAGE = "english"
WHITESPACE = re.compile(r"\s+")
NON_ALNUM = re.compile(r"[^\w\s]")
PARSER = WiktionaryParser()


@attr.s
class Cleaner:
    @staticmethod
    def remove_punctuation(string):
        """Remove all punctuation from the string"""
        return NON_ALNUM.sub("", string)

    @staticmethod
    def split_by_whitespace(string):
        """Break body of text into word units by whitespace"""
        return WHITESPACE.split(string)

    def clean(self, string):
        raise NotImplementedError


class BasicEnglishCleaner(Cleaner):
    def clean(self, string):
        """Clean up the page into distinct words by removing punctuation and splitting by whitespace"""
        return self.split_by_whitespace(self.remove_punctuation(string))


@attr.s
class Definer:
    def define(self, word):
        raise NotImplementedError


@attr.s
class WiktionaryDefiner(Definer):
    language: str = attr.ib()

    def __attrs_post_init__(self):
        self.parser = WiktionaryParser()
        self.entry = None

    def lookup_word(self, word):
        self.entry = self.parser.fetch(word, language=self.language)

    def get_definition(self, word: str, entry_n: int = 0, definition_n: int = 0):
        self.lookup_word(word=word)

        if self.entry == []:
            print(f"No {self.language} definition found for: '{word}'")
            return None

        entry = self.entry[entry_n]
        definitions = entry["definitions"]

        try:
            definition = definitions[definition_n]
        except IndexError:
            print(f"No definition found for: '{word}'")
            return None

        text = definition["text"]
        definition = text[1]

        return definition

    def define(self, word):
        result = self.get_definition(word)
        if result is None:
            lower = word.lower()
            if lower != word:
                result = self.get_definition(lower)
        return result


@attr.s
class Page:
    """Find a block of text at id=text_location at the given URL, and clean text using registered a Cleaner object."""
    url: str = attr.ib()
    text_location: str = attr.ib()

    def __attrs_post_init__(self):
        self.html = urlopen(self.url)
        self.page = BeautifulSoup(self.html.read(), "html.parser")

    def get_text(self):
        """Find element in the page to convert into text to clean"""
        text_element = self.page.find(id=self.text_location)
        return text_element.get_text()

    def get_words(self, cleaner):
        """Apply cleaner object's clean method to create a list of words"""
        return cleaner.clean(self.get_text())


@attr.s
class Word:
    """Class to hold a word and register a method to use to find the word's definition"""
    word: str = attr.ib()

    def __attrs_post_init__(self):
        self.definition = None

    def get_definition(self, definer: Definer):
        """Use a Definer object to get definition of word"""
        self.definition = definer.define(self.word)

    def get_flashcard(self):
        """Format word and definition as a standard Anki flashcard"""
        return f'{self.word}; "{self.definition}"'


@attr.s
class Flashcard:
    """Trivial class to hold a word and a definition, and represent it in a simple Anki format"""

    word: str = attr.ib()
    definition: str = attr.ib()

    def get_flashcard(self):
        """Return a string which can be imported into Anki"""
        return f'{self.word}; "{self.definition}"'

    @classmethod
    def from_word(cls, word):
        """Construct a Flashcard object directly from a Word object"""
        return cls(word=word.word, definition=word.definition)


class Deck(list):
    """Trivial class to hold a list of flashcards and create the string representing the entire deck"""

    def as_string(self):
        """Join all cards together into a single string representing the entire deck"""
        # Remove cards which have no definition
        cards = [card for card in self if card.definition is not None]
        # Remove cards which have no word
        cards = [card for card in cards if card.word]
        return "\n".join([card.get_flashcard() for card in cards])


@attr.s
class Wiki2Anki:
    url: str = attr.ib()
    top: int = attr.ib(default=5000)

    def __attrs_post_init__(self):
        self.wiki = Page(url=self.url, text_location="bodyContent")
        self.definer = WiktionaryDefiner("english")
        self.cleaner = BasicEnglishCleaner()
        self.common = pd.read_csv("../data/english_10000.csv").head(n=self.top)

    def get_words(self):
        """Get a list of Word object for each word in the page"""
        words = self.wiki.get_words(cleaner=self.cleaner)
        df = pd.DataFrame({"word": words})
        df = df.drop_duplicates("word")
        df = df.head(100)
        mask = df["word"].isin(self.common["word"])
        mask |= df["word"].str.lower().isin(self.common["word"])

        words = [ Word(word) for word in df[~mask]["word"] ]
        for word in words:
            word.get_definition(definer=self.definer)

    def get_cards(self):
        """Get a list of Flashcard objects for each word in the page"""
        return [Flashcard.from_word(word) for word in self.get_words()]

    def get_deck(self):
        """Join all cards together into a single string representing the entire deck"""
        deck = Deck(self.get_cards())
        return deck.as_string()

    def write(self, location: str):
        """Save the page as a .txt file ready to be imported into Anki"""
        with open(location, "w") as f:
            f.write(self.get_deck())


if __name__ == "__main__":

    url = "https://en.wikipedia.org/wiki/Red-tailed_tropicbird"
    wiki2anki = Wiki2Anki(url=url)
    wiki2anki.write("../data/test.txt")
