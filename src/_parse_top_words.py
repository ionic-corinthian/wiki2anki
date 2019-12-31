"""Simple script to download word frequency list from Wiktionary"""
import pandas as pd
from bs4 import BeautifulSoup
from urllib.request import urlopen

URL = "https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/PG/2006/04/1-10000"
COLS = "rank word count".split()


def get_info(a_row):
    """Unpack a table row into it's text component. Relies upon ordering."""
    return pd.Series(el.get_text() for el in a_row.find_all("td"))


if __name__ == '__main__':

    html = urlopen(URL)
    bs = BeautifulSoup(html.read(), "html.parser")

    div = bs.find(id="mw-content-text")
    tables = div.find_all("table")

    def process_table(table):
        body = table.tbody
        rows = body.find_all("tr")[1:]   # Ignore title row
        df = pd.DataFrame({"raw": rows})
        df[COLS] = df["raw"].apply(get_info)
        return df[COLS]

    dfs = [process_table(table) for table in tables]
    df = pd.concat(dfs, ignore_index=True, sort="rank")
    df.to_csv("../data/english_10000.csv", index=False)
