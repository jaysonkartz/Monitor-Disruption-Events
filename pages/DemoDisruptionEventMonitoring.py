import streamlit as st
from streamlit_folium import folium_static
import folium
from utils.Distance import GeoCalculator
from utils.Webscraper import check_nltk_installation
from datetime import datetime
from Supabase.Extractor import SupabaseExtractor
from Supabase.Insertor import SupabaseInsertor
from utils.Distance import DisruptionEventRanker, GeoCalculator
from googlesearch import GoogleSearch
import os
import sys
import logging
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from supabase import create_client, Client
# Get the absolute path to the directory containing this script (app.py)
current_directory = os.path.dirname(os.path.realpath(__file__))

# Add the 'modules' directory to sys.path
LLM_directory = os.path.join(current_directory, 'llm')
Supabase_directory = os.path.join(current_directory, 'Supabase')
utils_directory = os.path.join(current_directory, 'utils')
googlesearch_directory = os.path.join(current_directory, 'googlesearch')
sys.path.append(Supabase_directory)
sys.path.append(LLM_directory)
sys.path.append(utils_directory)
from llm.agent_main import AgentMain
from newspaper import Article
# Get the OpenAI API key 
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
LANGCHAIN_TRACING_V2 = st.secrets["LANGCHAIN_TRACING_V2"]
LANGCHAIN_ENDPOINT = st.secrets["LANGCHAIN_ENDPOINT"]
LANGCHAIN_API_KEY = st.secrets["LANGCHAIN_API_KEY"]
LANGCHAIN_PROJECT = st.secrets["LANGCHAIN_PROJECT"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

@st.cache_resource
def load_supabase(SUPABASE_URL, SUPABASE_KEY):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabaseInsertor = SupabaseInsertor(supabase)
    supabaseExtractor = SupabaseExtractor(supabase)
    return supabaseInsertor,supabaseExtractor

supabaseInsertor,supabaseExtractor = load_supabase(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def checkNLTK():
    check_nltk_installation()
checkNLTK()
# @contextmanager
# def st_capture(output_func):
#     with StringIO() as stdout, redirect_stdout(stdout):
#         old_write = stdout.write

#         def new_write(string):
#             ret = old_write(string)
#             output_func(stdout.getvalue())
#             return ret

#         stdout.write = new_write
#         yield
@contextmanager
def st_capture(output_func):
    with StringIO() as stdout, redirect_stdout(stdout):
        old_write = stdout.write

        def new_write(string):
            ret = old_write(string)
            output_func(string)  # Pass the new output directly
            return ret

        stdout.write = new_write
        yield

@contextmanager
def st_capture_and_log(output_func):
    # Capture print statements
    with st_capture(output_func):
        # Capture logger information
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers
        original_level = root_logger.level
        root_logger.handlers = [StreamlitLogHandler(output_func)]

        try:
            yield
        finally:
            root_logger.handlers = original_handlers
            root_logger.setLevel(original_level)

class StreamlitLogHandler(logging.Handler):
    def __init__(self, output_func):
        super().__init__()
        self.output_func = output_func

    def emit(self, record):
        log_message = self.format(record)
        self.output_func(log_message)

# Setting page title and header
st.markdown("<h1 style='text-align: center;'>Demo Disruption Event Mointoring System</h1>", unsafe_allow_html=True)
# Last updated date dd/mm/yyyy:
import streamlit as st
import pandas as pd


googleSearch_category = GoogleSearch.availableCategories()

# Ability to select multiple categories at once
categories = st.multiselect("Select categories to monitor disruptions", googleSearch_category)

if len(categories) > 0:
    submit_button = st.button("Run Mointoring System")
    if submit_button:
        # Display the logs
        placeholder_logs = st.empty()
        with st.spinner(f"Running Web Scraping + LLM Structed Task Based Chaining on {categories}"):
            with st.expander(f"🧾 Logs...",expanded=True):
                with st_capture(st.markdown):
                        try:
                            for category in categories:
                                urls = GoogleSearch.getCategoryUrls(category) 
                                st.write(f'🔍 Found {len(urls)} potential news urls for {categories}')
                        except Exception as e:
                            st.write(f'Error: {e}')
                            sys.exit(1)

                        # Testing on 3 urls only
                        
                        for url in urls:
                            try:
                                article = AgentMain.processUrl(url)
                            except Exception as e:
                                st.markdown(f'Error: {e}')
                                sys.exit(1)

                            if isinstance(article, Article):
                                # Insert into Supabase
                                try:
                                    article_dict = supabaseInsertor.addArticleData(article)
                                    st.markdown(f':green[SUCESSFULLY ADDED ARTICLE TO SUPABASE]: {article_dict["Title"]}')
                                except Exception as e:
                                    st.markdown(f':red[ERROR]: {e}')
                                    pass
                            elif isinstance(article, str):
                                st.markdown(f':blue[Skipping article...]')


output_break = st.markdown("---")

# if article_dict:

#     article_dict = DisruptionEventRanker.addSupplierMapping(article_dict)
#     article_dict = DisruptionEventRanker.addRiskScore(article_dict)
#     # Add the Map, starting at disruption event coords
#     st.markdown(f"<h3 style='text-align:center;'>Estimated Radius of Impact</h3>", unsafe_allow_html=True)

#     m = folium.Map(location=[article_dict['lat'], article_dict['lng']], zoom_start=12)
#     # Add all Mirxes suppliers to map
#     m = MapManager.addAll_mirxes_suppliers(m, mirxes_suppliers_info)
#     m = MapManager.addSingle_disruption_event(m, article_dict)
#     folium_static(m)
    
#     col1,col2 = st.columns([0.2,0.7])
#     col1.markdown(f"<div><h4 style='text-align:center;'>Event Type:\n\n{article_dict['DisruptionType']}</h4></div>", unsafe_allow_html=True)
#     # col1.image(f'./src/earthquake.png', use_column_width=True)
#     st.markdown(f"<h3 style='text-align:center;'>Severity Metrics</h3>", unsafe_allow_html=True)
#     st.markdown(f"<h4 style='text-align:center;'>{article_dict['Severity']}</h4>", unsafe_allow_html=True)
#     # Display Potential Suppliers Affected
#     st.markdown(f"<h3 style='text-align:center;'>Potential Suppliers Affected</h3>", unsafe_allow_html=True)
#     st.table(article_dict['suppliers'][:10])

#     # Display output
#     st.markdown(f"<h3 style='text-align: center;'>{article_dict['Title']} 😬</h3>", unsafe_allow_html=True)
#     st.write(f'Article Url: {article_dict["Url"]}')
#     st.image(f'{article_dict["ImageUrl"]}', use_column_width=True)