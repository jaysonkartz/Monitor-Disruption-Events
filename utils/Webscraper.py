# Newspaper3k
from newspaper import Config, Article, Source
# Webscraping
import newspaper
from newspaper import Article
from time import sleep,time
from newspaper import news_pool
from typing import Union,NamedTuple
import logging
logger = logging.getLogger(__name__)
import os

logger = logging.getLogger(__name__)
def check_nltk_installation():
    try:
        import nltk
        import nltk.data

        if not nltk.data.path:
            logger.warning("NLTK punkt not found. Downloading... NTLK")
            nltk.download('punkt')
    except Exception as e:
        logger.warning(f'Error: NLTK punkt not installed\n Downloading nltk punkt...')
        nltk.download('punkt')
        logger.info('NLTK punkt downloaded successfully')

class Webscraper:
    """
    Purpose: This class is used to scrape news articles from the web using the newspaper3k library
    Methods:
    """

    def __init__(self):
        check_nltk_installation()

    @staticmethod
    def _filter(article: Article):
        """
        Purpose: Filter out articles that are not valid news articles
            1. Check if Text/Title is empty
            2. Check if article is in English
            3. Check if article.publish_date is not None

        Parameters:
            > article: Article object
        Returns:
            >  True if article is a valid news article
            > False if article is not a valid news article (or if there is an error in webscraping)
        """
        if article.text == '' or article.title == '':
            logger.warning(f'Article text/title is empty: {article.url}')
            return False
        # Check if article text is shorter than 100 characters
        if len(article.text) < 100:
            logger.warning(f'Article text is too short. Text: {article.text} {article.url}')
            return False
        if article.meta_lang != 'en':
            logger.warning(f'Article is not in English: {article.url}')
            return False

        return True

    @staticmethod
    def process_text_title(text):
        """
        Remove trailing whitespace and newlines from text or title
        """
        return text.strip().replace('\n', ' ')

    @classmethod
    def _scrape(cls, url, **kwargs) -> Article:
        """
        Purpose: Given a url, scrape the article and return the article object
        + some data processing for datetime etc
        Handles invalid urls + invalid articles
        BY
            1. Title/Text non-existent OR too short
            2. No Article publish date
            3. Article is not in English
            4. Invalid url

        Params:
            > url: str
                Url of the article to be scraped
            > kwargs: dict
        Raises Exception for anything else --> Exception

        Returns: article object
        """
        try:
            article = Article(url)
        except Exception as e:
            raise Exception(f'Error: Invalid Url: {url}')

        try:
            article = cls._processArticle(article)
        except Exception as e:
            raise Exception(f'Unable to Process article. See error:\n\n{str(e)}')

        # Check that article is article Object
        if isinstance(article, Article):
            return article
        else:
            raise Exception(f'Error: Article is not a disruption event article: {article}')

    @classmethod
    def scrape(cls, url_or_dict: Union[str, dict], **kwargs) -> Article:
        """
        Purpose: calls main _scrape function, handles either url or NamedTuple "article_url_date" that contains url and date
        Params:
            > url_or_NamedTuple: Union[str,NamedTuple]
                Example of NamedTuple:
                    article_url_date(url='https://www.channelnewsasia.com/commentary/libya-flood-natural-disaster-human-climate-change-3796761', date=datetime.datetime(2023, 9, 26, 10, 16, 1, 893883))

                Either a url or NamedTuple "article_url_date" that contains url and date
            > kwargs: dict

        Validates if article
        """
        def validateArticleDict(dict: dict) -> bool:
            """Validates Article object if have all the relevant keys and values"""
            REQUIRED_KEYS = ["url", "published_date"]
            for key in REQUIRED_KEYS:
                if key not in dict.keys():
                    return False
            return True
        
        try:
            if isinstance(url_or_dict, str):
                return cls._scrape(url_or_dict, **kwargs)
            elif isinstance(url_or_dict, dict):
                if not validateArticleDict(url_or_dict):
                    raise Exception(f'Error: Parse article dict with keys "url" and "date" {url_or_dict}')
                    
                article = cls._scrape(url_or_dict['url'], **kwargs)
                # Check if article.publish_date is not None
                if article.publish_date is None:
                    # Set the article.publish_date to the date in the NamedTuple
                    article.publish_date = url_or_dict['published_date']
                return article
            else:
                raise Exception(f'Error: Invalid url_or_dict: {url_or_dict}')
        except Exception as e:
            raise

    @classmethod
    def _processArticle(cls, article: Article) -> Article:
        """Call parse() and nlp() on the article object and do internal filtering and processing"""
        try:
            if article.html == '':
                article.download()
            article.parse()
        except Exception as e:
            raise Exception("Error: Article is not a disruption event article: " + str(e))

        if not cls._filter(article):
            raise Exception(f'Article is not valid: {article.url}')

        article.nlp()
        article.title = cls.process_text_title(article.title)
        article.text = cls.process_text_title(article.text)

        title = article.title
        text = article.text

        text_body = title + ' ' + text

        # Add text_body to article object
        article.additional_data["text_body"] = text_body

        return article

    @classmethod
    def downloadAllSources(cls, base_urls: list[str]) -> list[Source]:
        """
        Main Function to scrape live news article from the pre-determined sources in supabase
        Takes roughly one min to run per source

        Logs:
            > Number of articles scraped from each source
            > Time taken to build all source objects
        """
        # Build all the source objects
        logger.info(f'Building: {len(base_urls)} number of sources, this will take ~1.5min per source')
        current_time = time()
        sources_objects = [newspaper.build(base_url, memoize_articles=False) for base_url in base_urls]

        news_pool.set(sources_objects, threads_per_source=2)
        news_pool.join()
        logger.info(f'Time taken to build all source objects: {time() - current_time} seconds')
        # Log the number of articles scraped from each source
        for source in sources_objects:
            logger.info(f'Number of articles scraped from {source.url}: {len(source.articles)}')

        return sources_objects

    @classmethod
    def parseNlpAllArticles(cls, articles: list[Article]) -> list[Article]:
        """Call parse() and nlp() on all the articles in the list,return back the list of articles
        Articles that failed the processing will be skipped and not returned
        """
        logger.info(f'Nlp processing {len(articles)} articles...')
        current_time = time()
        for article in articles:
            try:
                article = cls._processArticle(article)
            except Exception as e:
                logger.info(f'Article:{article.title} is not a disruption event article: {str(e)}')
                # Remove the article from the list
                articles.remove(article)

        logger.info(f'Number of articles successfully NLPprocessed and filtered: {len(articles)}')
        logger.info(f'Time taken to parse and nlp articles {time() - current_time} seconds')
        # Return Number of articles that were successfully processed out of the total number of articles
        return articles

    @classmethod
    def validateArticle(cls, article: Article) -> bool:
        """Validates Article object if have all the relevant keys and values"""
        REQUIRED_KEYS = ["title", "text", "url", "top_image", "publish_date"]