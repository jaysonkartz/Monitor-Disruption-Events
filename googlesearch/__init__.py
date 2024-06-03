import urllib.parse
"""googlesearch is a Python library for searching Google, easily."""
from time import sleep
from bs4 import BeautifulSoup
from requests import get
from .user_agents import get_useragent
import urllib
from typing import Union, List, Dict,NamedTuple,Generator
from datetime import datetime
import re
from colorlog import ColoredFormatter
import logging
# regrex
import re
from datetime import datetime, timedelta
import json 

formatter = ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s %(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

def _req(term, results, lang, start, proxies, timeout):
    resp = get(
        url="https://www.google.com/search",
        headers={
            "User-Agent": get_useragent()
        },
        params={
            "q": term,
            "num": results + 2,  # Prevents multiple requests
            "hl": lang,
            "start": start,
            "tbm": "nws",
        },
        proxies=proxies,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp


CATEGORY_KEYWORD = {
    "Airport Disruption": ["airport disruption recent", "flight delay", "airport closure"],
    "Bankruptcy": ["bankruptcy news", "financial insolvency", "company bankruptcy"],
    "Business Spin-off": ["business spin-off", "corporate separation", "division spin-off"],
    "Business Sale": ["business sale news", "company acquisition", "selling a business"],
    "Chemical Spill": ["chemical spill", "toxic waste spill", "environmental contamination"],
    "Corruption": ["corruption scandal", "government corruption", "bribery investigation"],
    "Company Split": ["company split news", "corporate division", "splitting a corporation"],
    "Cyber Attack": ["cyber attack", "data breach", "cybersecurity incident"],
    "FDA/EMA/OSHA Action": ["FDA action", "EMA regulation", "OSHA compliance"],
    "Factory Fire": ["factory fire", "industrial blaze", "manufacturing plant fire"],
    "Fine": ["legal fine", "financial penalty", "monetary fine"],
    "Geopolitical": ["geopolitical news", "international relations", "global politics"],
    "Leadership Transition": ["leadership change", "CEO transition", "change in leadership"],
    "Legal Action": ["legal action news", "lawsuit update", "court case"],
    "Merger & Acquisition": ["merger and acquisition", "M&A news", "corporate merger"],
    "Port Disruption": ["port disruption", "shipping delay", "dockworker strike"],
    "Protest/Riot": ["protest news", "civil unrest", "riot demonstration"],
    "Supply Shortage": ["supply shortage", "product scarcity", "shortfall in supply"],
    "Earthquake": ["Earthquake disaster now"],
    "Extreme Weather": ["extreme weather recent", "severe weather conditions", "weather catastrophe"],
    "Flood": ["flood news now", "flooding event", "flash flood"],
    "Hurricane": ["hurricane news recent", "tropical storm", "hurricane forecast"],
    "Tornado": ["tornado news", "twister warning", "tornado outbreak"],
    "Volcano": ["volcano eruption", "volcanic activity", "volcanic eruption"],
    "Human Health": ["public health crisis", "healthcare news", "health epidemic"],
    "Power Outage": ["power outage", "electricity failure", "grid blackout"],
    "CNA":["CNA Natural Disaster"],
    "Port Disruption":["Port Disruption"],
}

class GoogleSearch:
    """Main Wrapper for Google Search for MDE Project"""

    @staticmethod
    def convertTextDate(text: str) -> Union[datetime, None]:
        """Convert the text date to datetime object

        Args:
            text (str): The text date scraped from the google search results
            Example: 20 hours ago, 1 day ago,1 month ago,4 weeks ago, 14 Jul 2023

        Returns:
            Union[datetime, None]: The datetime object of the text date or None if the text date is invalid
        """
        CurrentDate = datetime.now()
        # Check if the text date is in the format of "num xxxxx ago"
        match = re.search(r"(\d+)\s+(min|hour|day|week|month|year)s?\s+ago", text)
        if match:
            # Extract the number and the unit of time
            num, unit = match.groups()
            # Convert the number to int
            num = int(num)
            # Calculate the timedelta
            if unit == "min":
                delta = timedelta(minutes=num)
            elif unit == "hour":
                delta = timedelta(hours=num)
            elif unit == "day":
                delta = timedelta(days=num)
            elif unit == "week":
                delta = timedelta(weeks=num)
            elif unit == "month":
                delta = timedelta(days=num * 30)
            elif unit == "year":
                delta = timedelta(days=num * 365)
            else:
                return None
            # Calculate the date
            date = CurrentDate - delta
            return date
        # Check if the text date is in the format of "dd mmm yyyy"
        match = re.search(r"(\d+)\s+(\w+)\s+(\d+)", text)
        if match:
            # Extract the day, month and year
            day, month, year = match.groups()
            # Convert the day to int
            day = int(day)
            # Convert the month to int
            month = datetime.strptime(month, "%b").month
            # Convert the year to int
            year = int(year)
            # Calculate the date
            date = datetime(year, month, day)
            return date
        else:
            return None
        
    @staticmethod
    def _scrapeDate(a_href_div) -> Union[datetime, None]:
        """Scrape the date from the bottom div of the a_href_divs

        Args:
            a_href_div
                > Assumes the child_div is vaild and follows the structure of google search results
                and must be called as one of the div in a_href_divs.
        """
        # access the child div one level down only
        child_div = a_href_div.find("div", recursive=False)
        if child_div:
            # Find the div with style="bottom:0px"
            bottom_div = child_div.find("div", attrs={"style": "bottom:0px"})
            if bottom_div:
                # Get the <span> tag with the publication date
                span = bottom_div.find("span")
                if span:
                    return GoogleSearch.convertTextDate(span.text)
        return None
    
    @classmethod
    def search(cls, term, num_results=5, lang="en", proxy=None, sleep_interval=0, timeout=5, start=0):
        """Main Method to 
        Search the Google search engine and retrieve a result from the first page.
        Returns:
        """

        escaped_term = urllib.parse.quote_plus(term) # make 'site:xxx.xxx.xxx ' works.

        # Proxy
        proxies = None
        if proxy:
            if proxy.startswith("https"):
                proxies = {"https": proxy}
            else:
                proxies = {"http": proxy}

        # Send request
        resp = _req(escaped_term, num_results,
                    lang, start, proxies, timeout)
        # Parse
        soup = BeautifulSoup(resp.text, "html.parser")
        # Find the a tags with href attribute
        article_divs = soup.find_all("a", attrs={"href": True})
        # Extract the urls from the href attributes
        for div in article_divs:
            url = div["href"]
            # Filter out non-article links
            if not re.match(r"^https://(?!.*google).*", url):
                continue
            
            try:
                article_published_date = GoogleSearch._scrapeDate(div)
            except Exception as e:
                logger.error(f"Error in extracting date from source")
                article_published_date = datetime.now()
            
            article_url_date = {
                "url": url,
                "published_date": article_published_date
            }
            yield article_url_date

        sleep(sleep_interval)
        if start == 0:
            return []
    
    @staticmethod
    def _scrape_news(keywords:list[str], num_results=2) -> list[dict]:
        """Calls the search function to scrape news articles from Google Search"""
        news_data = []
        visited_urls = set()  # Keep track of visited URLs to remove duplicates
        for keyword in keywords:
            query = f"{keyword}"

            resp = GoogleSearch.search(term=query, num_results=num_results)
            for article_url_date in list(resp):
                if article_url_date['url'] in visited_urls:
                    continue  # Skip duplicate URLs
                try:
                    # Extract additional information (title and publication date) from the article's URL or source
                    # This part would require specific implementation based on the news source's website structure.

                    # Append the article data to the news_data list
                    news_data.append(article_url_date)

                    # Add the URL to the visited URLs set
                    visited_urls.add(article_url_date['url'])
                except Exception as e:
                    print(f"Error processing {article_url_date}: {str(e)}")

        return news_data

    @classmethod
    def getCategoryUrls(cls, category: str,num_results=5) -> list[Union[str,dict]]:
        """Given a category (Found in the category_keyword dict), return a list of urls from the google search"""

        logger.info(f'Websraping news articles for category: {category}')
        # Check if category is valid
        if category not in CATEGORY_KEYWORD.keys():
            raise ValueError(f"Category: {category} is not a valid category.Can only be one of {CATEGORY_KEYWORD.keys()}")

        keywords = CATEGORY_KEYWORD[category]  # Get keywords for the input category
        news = cls._scrape_news(keywords,num_results=num_results)  # Scrape news for the input category
        logger.info(f"Scraped {len(news)} news articles for category: {category}")
        return news

    @classmethod
    def scrapeFromJson(cls, json_object:dict) -> list[str]:
        """Scrapes the news articles from the json file E.g
        {
            "locations": ["Hong Kong","Bangkok","Sydney","Tokyo","New York","Ho Chi Minh"],
            "disruption": ["Airport Disruptions","Port Disruptions","Natural disasters"]
        }
        Returns a list of keywords for each location and disruption 

        #TODO: Method to be re-organized to somewhere else
        """
        # Extract the locations and disruptions from the json object
        locations = json_object['locations']
        disruptions = json_object['disruption']
        # Create a list of keywords for each location and disruption
        keywords = []
        for location in locations:
            for disruption in disruptions:
                keywords.append(f"{disruption} in {location}")
        return keywords

        
    

    @classmethod
    def availableCategories(cls) -> list[str]:
        """Returns a list of available categories"""
        return list(CATEGORY_KEYWORD.keys())