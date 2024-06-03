import os
import sys

# Get the absolute path to the directory containing this script
root_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print(os.path.join(root_directory, 'llm'))

# Add the required directories to sys.path
sys.path.append(os.path.join(root_directory, 'llm'))
sys.path.append(os.path.join(root_directory, 'Supabase'))
sys.path.append(os.path.join(root_directory, 'utils'))
sys.path.append(os.path.join(root_directory, 'googlesearch'))

from llm.agent_main import AgentMain
from googlesearch import GoogleSearch
from newspaper import Article
from dotenv import load_dotenv
from Supabase.Insertor import SupabaseInsertor
from Supabase.Extractor import SupabaseExtractor
# Load variables from the .env file
load_dotenv(os.path.join(root_directory, '.env'))
from supabase import create_client, Client

# Access the variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
supabaseInsertor = SupabaseInsertor(supabase_client =supabase)
supabaseExtractor = SupabaseExtractor(supabase_client =supabase)

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

def scrapeFromJson(json_object:dict) -> list[str]:
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

def getAllsearchTerms(dict:dict) -> list[dict]:
    """Get all the search terms from the dictionary"""
    all_search_terms = []
    for key in dict:
        for term in dict[key]:
            all_search_terms.append(term)

    return all_search_terms

google_search_keywords = getAllsearchTerms(CATEGORY_KEYWORD)
# google_search_keywords = scrapeFromJson(terms)
print('google_search_keywords: ', google_search_keywords)

urls = GoogleSearch._scrape_news(keywords=google_search_keywords,num_results=10)

for url in urls:
    # Check if the url is already in the database
    all_article_urls = supabaseExtractor.extractAllArticleUrl()
    if url in all_article_urls:
        print(f':blue[Skipping article...]')
        continue
    else:
        print(f':green[Processing article...]')

        try:
            article = AgentMain.processUrl(url)
        except Exception as e:
            sys.exit(1)
        if isinstance(article, Article):
            # Insert into Supabase
            try:
                article_dict = supabaseInsertor.addArticleData(article)
                print(f':green[SUCESSFULLY ADDED ARTICLE TO SUPABASE]: {article_dict["Title"]}')
            except Exception as e:
                print(f':red[ERROR]: {e}')
                pass
        elif isinstance(article, str):
            print(f':blue[Skipping article...]')