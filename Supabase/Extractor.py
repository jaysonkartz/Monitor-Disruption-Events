import pandas as pd
from dotenv import load_dotenv
import os

import postgrest
from postgrest.exceptions import APIError
from tqdm import tqdm
# Supabase
from supabase import create_client, Client
import newspaper
from newspaper import Config, Article, Source

class SupabaseExtractor:
    """
    TLDR: "Fancy INSERT INTO statement for the supabase" (Need to migrate over)
    Already initilized with the supabase client
    Methods:
        * addDisruptionEvent(self, DisruptionEvent: dict)
        * addEventDataRelation
    """
    def __init__(self,supabase_client:Client) -> None:
        self.supabase: Client = supabase_client
        self.articleColumns = ['id','created_at','Title', 'Text', 'Location', 'lat', 'lng', 'DisruptionType', 'Severity', 'SourceName', 'Url', 'ImageUrl', 'PublishedDate', 'Radius']

    
    def extractSources(self) -> list[dict]:
        """Extracts all the sources from the Supabase database.
        Default source_name is ['straitstimes'].
        Example ouput:
        [{'Name': 'straitstimes', 'domain_url': 'https://www.straitstimes.com/', 'created_at': '2023-09-04T07:24:24.143487+00:00'}, {'Name': 'scmp', 'domain_url': 'https://www.scmp.com/', 'created_at': '2023-09-04T08:38:51.475122+00:00'}, {'Name': 'reuters', 'domain_url': 'https://www.reuters.com/', 'created_at': '2023-09-04T08:39:49.793189+00:00'}]"""
        # Check if each source name is valid
        sources = self.supabase.table("Source").select("*").execute()
        return sources.data
    
    
    @staticmethod
    def convertArticleDataType(article:dict) -> dict:
        """Formats the article data type to be the cooresponding data type in the Supabase database."""
        article['lat'] = float(article['lat'])
        article['lng'] = float(article['lng'])
        article['Radius'] = float(article['Radius'])
        article['PublishedDate'] = pd.to_datetime(article['PublishedDate'])
        article['created_at'] = pd.to_datetime(article['created_at'])
        return article
        
    def extractAllArticles(self) -> list[dict]:
        """Extract all articles from the Article table in Supabase."""
        all_articles = self.supabase.table("Article").select("*").execute()
        all_articles.data = [self.convertArticleDataType(article) for article in all_articles.data]
        return all_articles.data
    
    
    def extractIdArticle(self,id) -> dict:
        """wah"""
        try:
            article = self.supabase.table("Article").select("*").eq('id',id).execute()
            return article.data[0]
        except Exception as e:
            print(e)
            return None

    
    
    def extractAllArticleUrl(self) -> list[str]:
        """Extract all urls from the Article table in Supabase."""
        all_articles = self.supabase.table("Article").select("Url").execute()
        return [article['Url'] for article in all_articles.data]

    
    def extractAllSupplierInfo(self) -> list[dict]:
        """Extract all supplier info from the Supplier table in Supabase."""
        all_suppliers = self.supabase.table("Supplier").select("*").execute()
        return all_suppliers.data
    
    def extractAllPNGSupplierInfo(self) -> list[dict]:
        """Extract all supplier info from the PNG Supplier table in Supabase."""
        all_suppliers = self.supabase.table("PNG_Supplier").select("*").execute()

        return all_suppliers.data
    
    def extractAllUniqueDisruptionType(self) -> list[str]:
        """Extracts all the unique disruption types from the Supabase database."""
        uniqueDisruptionTypes = self.supabase.table("Article").select("DisruptionType").execute()
        return list(set([article['DisruptionType'] for article in uniqueDisruptionTypes.data]))
    

# # Test for now
# if __name__ == "__main__":

#     sources = SupabaseExtractor.extractSources()
#     print(f'Sources: {sources}, type: {type(sources)}')
#     article_url = SupabaseExtractor.extractAllArticleUrl()
#     print(f'Article url: {article_url}, type: {type(article_url)}')
    
