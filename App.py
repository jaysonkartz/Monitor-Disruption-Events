import streamlit as st
from streamlit_folium import folium_static
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import requests
import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime
from utils.Distance import DisruptionEventRanker, GeoCalculator
from utils.Webscraper import check_nltk_installation
import utils.nltk_download_utils
from Supabase.Extractor import SupabaseExtractor
from SQL.Extractor import SQLExtractor
from googlesearch import GoogleSearch

import pyodbc
from dotenv import load_dotenv
from streamlit_folium import st_folium

# Add necessary directories to sys.path
current_directory = os.path.dirname(os.path.realpath(__file__))
LLM_directory = os.path.join(current_directory, 'llm')
Supabase_directory = os.path.join(current_directory, 'Supabase')
utils_directory = os.path.join(current_directory, 'utils')
sys.path.append(Supabase_directory)
sys.path.append(LLM_directory)
sys.path.append(utils_directory)

# Set up Streamlit page configuration
st.set_page_config(page_title="Disruption Monitoring", page_icon=":airplane:", layout="wide")

# Hide default Streamlit formatting
hide_default_format = """
       <style>
       #MainMenu {visibility: hidden; }
       footer {visibility: hidden;}
       </style>
       """
st.markdown(hide_default_format, unsafe_allow_html=True)

# Remove whitespace from the top of the page and sidebar
st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)

# Load environment variables from .env file
load_dotenv()

# Access environment variables
# SQL_SERVER = os.getenv("SQL_SERVER")
# SQL_DATABASE = os.getenv("SQL_DATABASE")
# SQL_TRUSTED_CONNECTION = os.getenv("SQL_TRUSTED_CONNECTION")
# DRIVER = os.getenv("DRIVER")

# Define connection parameters
SQL_SERVER = 'localhost\\SQLEXPRESS'
SQL_DATABASE = 'DisruptionMonitoring'
SQL_TRUSTED_CONNECTION = 'yes' 
DRIVER = '{ODBC Driver 17 for SQL Server}'

# Construct connection string
conn_str = f'DRIVER={DRIVER};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};Trusted_Connection={SQL_TRUSTED_CONNECTION};'

try:
    # Establish connection
    conn = pyodbc.connect(conn_str)

    # Check if the connection is open
    if conn:
        #print("Connection to SQL Server database established successfully!")

    # Close connection
        conn.close()
except pyodbc.Error as e:
    print("Error connecting to SQL Server database:", e)

# Retrieve environment variables for database connection
# server = st.secrets["SQL_SERVER"]
# database = st.secrets["SQL_DATABASE"]
# # driver = st.secrets["DRIVER"]
# trusted_connection = st.secrets["SQL_TRUSTED_CONNECTION"]

# # Construct connection string
# connection_string = f'mssql+pyodbc://{server}/{database}?Trusted_Connection={trusted_connection}'

# Define function to fetch data from the database
@st.cache_data
def fetch_data(query):
    try:
        # Establish connection
        conn = pyodbc.connect(conn_str)

        # Execute query and fetch data
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        # Convert fetched data to DataFrame
        columns = [column[0] for column in cursor.description]
        data = pd.DataFrame.from_records(rows, columns=columns)

        # Close connection
        conn.close()

        return data
    except pyodbc.Error as e:
        print("Error fetching data from SQL Server:", e)
        return None


# Define function to check NLTK installation
@st.cache_resource
def checkNLTK():
    print('Checking NLTK installation')
    check_nltk_installation()

checkNLTK()

@st.cache_data
def fetch_cities(query):
    try:
        # Establish connection
        conn = pyodbc.connect(conn_str)

        # Execute query and fetch data
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        # Convert fetched data to DataFrame
        columns = [column[0] for column in cursor.description]
        data = pd.DataFrame.from_records(rows, columns=columns)

        # Close connection
        conn.close()

        return data
    except pyodbc.Error as e:
        print("Error fetching data from SQL Server:", e)
        return None

# Example query to fetch data
queryCities = "Select * from cities "
dfCities = fetch_cities(queryCities)

# Define function to retrieve location data from API
# @st.cache_data
# def retrieve_location_data():
#     try:
#         response = requests.get("http://localhost:8081/api/get-locations")
#         response.raise_for_status()  # Raise HTTPError for bad responses
#         data = response.json()
#         return data["location"]
#     except requests.exceptions.RequestException as e:
#         st.error(f"Error retrieving location data: {e}")
#         return []

# parsed_data = retrieve_location_data()

# Setting page title and header
st.markdown("<h3 style='text-align: center;'>Real Time Disruption Monitoring</h3>", unsafe_allow_html=True)

# Define MapManager class to manage map and its components
class MapManager: 
    @classmethod
    def addAll_mirxes_suppliers(cls, map: folium.Map, mirxes_suppliers_info: list[dict]) -> folium.Map:
        marker_cluster = MarkerCluster().add_to(map)
        for supplier in mirxes_suppliers_info:
            folium.Marker(
                [supplier['lat'], supplier['lng']], 
                popup=supplier['Name'], 
            ).add_to(marker_cluster)
        return map
    
    @classmethod
    def addSingle_disruption_event(cls, map: folium.Map, disruption_event: dict) -> folium.Map:
        colour_risk_mapping = {
            'Low': 'orange',
            'Medium': 'orange',
            'High': 'red'
        }
        def format_popContent():
            popContent = (
                "<div style='text-align: center; font-size: 20px; font-weight: bold;'>Disruption Event Details</div>"
                "<br><b>Event Type: </b>" + str(disruption_event["DisruptionType"]) +
                "<br><b>Supply Chain Disruption Potential: </b>" + str(disruption_event["risk_score"]) +
                "<br><b>Severity Metrics: </b>" + str(disruption_event["Severity"]) +
                "<br><table border='1' style='border-collapse: collapse; width: 100%;'>"
                "<tr><th>Supplier Name</th><th>Distance (KM)</th></tr>"
            )
            for supplier in disruption_event["suppliers"][:10]:
                popContent += "<tr><td>" + str(supplier["Name"]) + "</td><td>" + str(round(supplier["distance"], 2)) + "</td></tr>"
            popContent += "</table><br><b>" + str(disruption_event["Title"]) + "😬</b><br>Article Url: <a href='" + str(disruption_event["Url"]) + "' target='_blank'>" + str(disruption_event["Url"]) + "</a>"
            return popContent

        popContent = format_popContent()
        iframe = folium.IFrame(popContent, width=350, height=350)
        popup1 = folium.Popup(iframe, min_width=350, max_width=350)
        try:
            folium.Circle(
                [disruption_event['lat'], disruption_event['lng']],
                radius=disruption_event['Radius'],
                color=colour_risk_mapping[disruption_event['risk_score']],
                fill=True,
                fill_color=colour_risk_mapping[disruption_event['risk_score']],
                tooltip=disruption_event['Title'],
                popup=popup1
            ).add_to(map)
        except Exception as e:
            print(f'Error adding disruption event {disruption_event["id"]}: {e}')
            pass   
        return map
    
    @classmethod
    def addAll_disruption_event(cls, map: folium.Map, all_disruption_events: list[dict]) -> folium.Map:
        for disruption_event in all_disruption_events:
            cls.addSingle_disruption_event(map, disruption_event)
        return map

# Extract data from SQL Server
sql_extractor = SQLExtractor()
mirxes_suppliers_info = sql_extractor.extract_all_supplier_info()
all_disruption_events = sql_extractor.extract_all_articles()
unique_disruption_types = sql_extractor.extract_all_unique_disruption_types()


# Rank disruption events by distance
all_disruption_events_ranked_by_distance = DisruptionEventRanker.rankDisruptionEvents(all_disruption_events, mirxes_suppliers_info)

# Sidebar filters and options
left, right = st.columns((8, 3))
with right:
    today = datetime.now()
    selection_option = st.radio(
        "Choose an option for time period selection",
        ["Number of days to look back", "Select a certain period"],
        index=0
    )
    days_disruption = None
    time_period = None
    if selection_option == "Number of days to look back":
        days_disruption = st.selectbox('Select the number of days to look back for disruptions', [30, 7, 1, 365])
        time_period = st.date_input(
            "Select a period of time to detect disruptions",
            (datetime(today.year - 1, today.month, today.day), today),
            disabled=True
        )
    else:
        days_disruption = st.selectbox('Select the number of days to look back for disruptions', [30, 7, 1, 365], disabled=True)
        time_period = st.date_input(
            "Select a period of time to detect disruptions",
            (datetime(today.year - 1, today.month, today.day), today),
            disabled=False
        )
        start_date, end_date = time_period
        days_disruption = (end_date - start_date).days

    all_city_list = dfCities['city'].tolist()
    all_city_list.append('All')
    selected_city_filter = st.multiselect('Filter by cities', all_city_list, default="All")
    
    unique_disruption_types.append('All')
    disruption_categories = st.multiselect("Select disruption type", unique_disruption_types, default='All')
    distance_threshold_filter = st.slider('Average distance filter disruption events ( KM )', 0, 1000, 1000)

if selection_option == "Number of days to look back":
    all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByDate(all_disruption_events_ranked_by_distance, days_disruption)
else:
    #all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByDateRange(all_disruption_events_ranked_by_distance, start_date, end_date)
    all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByAvgDistance(all_disruption_events_ranked_by_distance, distance_threshold_filter)

if 'All' not in disruption_categories:
    all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByType(all_disruption_events_ranked_by_distance, disruption_categories)

if 'All' not in selected_city_filter:
    selected_city_filter_geoCodes = [{'lat': dfCities[dfCities['city'] == selected_city]['latitude'].values[0], 'lng': dfCities[dfCities['city'] == selected_city]['longitude'].values[0]} for selected_city in selected_city_filter]
    all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByCity(all_disruption_events_ranked_by_distance, selected_city_filter_geoCodes, 500)

with left:
    map = folium.Map(location=[1.3521, 103.8198], zoom_start=2)
    map = MapManager.addAll_mirxes_suppliers(map, mirxes_suppliers_info)
    map = MapManager.addAll_disruption_event(map, all_disruption_events_ranked_by_distance)
    folium_static(map)

st.markdown(f"<h2 style='text-align:center;'>🚨 Top Alerts: Disruption Events <Past {days_disruption}days> </h2>", unsafe_allow_html=True)
top_no_disruptions = st.selectbox('Select the number of top disruptions to display', [5,10,15,20])

if len(all_disruption_events_ranked_by_distance) == 0:
    st.markdown(f"<h3 style='text-align:center;'>❌ No Disruption Event identified in the past {days_disruption} days</h3>", unsafe_allow_html=True)
else:
    # Add input for user to select how many top disruptions to display
    for article_dict in all_disruption_events_ranked_by_distance[:top_no_disruptions]:
        # Check if the disruption event is in the selected disruption categories
            with st.expander(f"**{article_dict['Severity']}, RISK Alert: {article_dict['risk_score']}, {article_dict['Location']}**"):
                # Add the Map, starting at disruption event coords
                Radius_impact_col,published_date_col = st.columns([0.7,0.3])
                # Bold the Estimated Radius of Impact
                Radius_impact_col.markdown(f'<h3 style="font-weight:bold;text-align:center;">Estimated Radius of Impact:</h3>', unsafe_allow_html=True)
                published_date_col.markdown(f'<h5 style="text-align:right;">Date of Disruption:\n\n{article_dict["PublishedDate"].strftime("%A, %B %d, %Y %I:%M %p")}</h5>', unsafe_allow_html=True)#Convert datetime to only yyyy-mm-dd

                # st.markdown(f"<h3 style='text-align:center;'>Estimated Radius of Impact</h3>", unsafe_allow_html=True)

                m = folium.Map(location=[article_dict['lat'], article_dict['lng']],width=725, height=400, zoom_start=12)
                # Add all Mirxes suppliers to map
                m = MapManager.addAll_mirxes_suppliers(m, mirxes_suppliers_info)
                m = MapManager.addSingle_disruption_event(m, article_dict)
                folium_static(m, width=725)
                st_data_loop = st_folium(m, height=400) # , width=725
                col1,col2 = st.columns([0.2,0.7])
                col1.markdown(f"<div><h4 style='text-align:center;'>Event Type:\n\n{article_dict['DisruptionType']}</h4></div>", unsafe_allow_html=True)
                # col1.image(f'./src/earthquake.png', use_column_width=True)
                col2.markdown(f"<h4 style='text-align:center;'>Supply Chain Disruption Potential\n\n{article_dict['risk_score']}</h4>", unsafe_allow_html=True)
                # Display Severity Metrics in a table
                st.markdown(f"<h3 style='text-align:center;'>Severity Metrics</h3>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='text-align:center;'>{article_dict['Severity']}</h4>", unsafe_allow_html=True)
                # Display Potential Suppliers Affected
                st.markdown(f"<h3 style='text-align:center;'>Potential Suppliers Affected</h3>", unsafe_allow_html=True)
                st.table(article_dict["suppliers"][:10])
                # Display output
                st.markdown(f"<h3 style='text-align: center;'>{article_dict['Title']} 😬</h3>", unsafe_allow_html=True)
                st.write(f'Article Url: {article_dict["Url"]}')
                st.image(f'{article_dict["ImageUrl"]}', use_column_width=True)

# Footer with logo and backlink
# left_co, cent_co, right_co = st.columns(3)
# with cent_co:
#     st.image("mirxes_logo.png", width=100)
# with right_co:
#     st.markdown("[Back to Home](https://www.mirxes.com)", unsafe_allow_html=True)
