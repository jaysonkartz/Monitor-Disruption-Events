import streamlit as st
from streamlit_folium import folium_static
import folium
from utils.Distance import GeoCalculator
from datetime import datetime
from Supabase.Extractor import SupabaseExtractor
from Supabase.Insertor import SupabaseInsertor
from utils.Distance import DisruptionEventRanker, GeoCalculator
from utils.Webscraper import check_nltk_installation
import utils.nltk_download_utils
from googlesearch import GoogleSearch

import os
import sys
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
def load_supabase(SUPABASE_URL, SUPABASE_KEY) -> tuple[SupabaseInsertor,SupabaseExtractor]:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabaseInsertor = SupabaseInsertor(supabase)
    supabaseExtractor = SupabaseExtractor(supabase)

    return supabaseInsertor,supabaseExtractor

supabaseInsertor,supabaseExtractor = load_supabase(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def checkNLTK():
    print('Checking NLTK installation')
    check_nltk_installation()

checkNLTK()

import random
# Setting page title and header
st.markdown("<h3 style='text-align: center;'>Real Time Disruption Monitoring</h3>", unsafe_allow_html=True)
# Last updated date dd/mm/yyyy:
import streamlit as st
import pandas as pd
from folium.plugins import MarkerCluster

def assign_icon_colour(mirxes_suppliers_info:list[dict]) -> list[dict]:
    """Adds a colour to the supplier and it's linked supplier, 
    Logic: Get all the pairing of suppliers and linked suppliers
    for each paring, choose a random hex colour for the pair
    if destination is true, then assigned a darker shade of the same colour
    """

    COLOUR_VALUES = [('red','lightred'),('blue','lightblue'),('green','lightgreen')]
    # Get all the pairing of suppliers and linked suppliers
    supplier_parings: list[tuple[dict, dict]] = []
    for supplier in mirxes_suppliers_info:
        if supplier['Destination']:
            # get the dict of the linked supplier
            linked_supplier = next((item for item in mirxes_suppliers_info if item["BP_Code"] == supplier['link']), None)
            supplier_parings.append((supplier, linked_supplier))
    
    # for each paring, choose a random hex colour for the pair
    for index,(supplier, linked_supplier) in enumerate(supplier_parings):
        # icon_colour:str 
        # darker_shade_icon_colour:str
        # # Generate a random hex colour
        # icon_colour = random.choice(['#'+str(hex(i))[2:] for i in range(256**3)])
        # # Generate a darker shade of the same colour
        # darker_shade_icon_colour = '#'+str(hex(int(icon_colour[1:],16) - 0x222222))[2:]
        # # Assign the colour to the supplier and linked supplier
        # supplier['icon_colour'] = icon_colour
        # linked_supplier['icon_colour'] = darker_shade_icon_colour
        # Assign the colour to the supplier and linked supplier
        supplier['icon_colour'] = COLOUR_VALUES[index][0]
        linked_supplier['icon_colour'] = COLOUR_VALUES[index][1]
    
    return mirxes_suppliers_info

class MapManager:
    """Class for managing the map and its components"""

    @classmethod
    def addAll_mirxes_suppliers(cls, map: folium.Map, mirxes_suppliers_info: list[dict]) -> folium.Map:
        """
        Adds Mirxes suppliers to the map with numbered icons indicating linkages.

        Returns the exact mirxes_suppliers_info with the html colour code for the icon
        """
                
        # Assign a colour to the supplier and it's linked supplier
        mirxes_suppliers_info = assign_icon_colour(mirxes_suppliers_info)


        for supplier in mirxes_suppliers_info:


            # Add marker for the supplier
            folium.Marker(
                [supplier['lat'], supplier['lng']],
                popup={supplier["Name"]},
                icon=folium.Icon(icon_color=supplier['icon_colour'], icon='info-sign')
            ).add_to(map)

        return map
    
    @classmethod
    def addSingle_disruption_event(cls,map: folium.Map, disruption_event:dict) -> folium.Map:
        """
        Adds one disruption event to map
        """
        colour_risk_mapping = {
            'Low': 'orange',
            'Medium': 'orange',
            'High': 'red'
        }
        try:
            folium.Circle(
                [disruption_event['lat'], disruption_event['lng']],
                radius=disruption_event['Radius'],
                color=colour_risk_mapping[disruption_event['risk_score']],
                fill=True,
                fill_color=colour_risk_mapping[disruption_event['risk_score']],
                tooltip=disruption_event['Title'],
                popup=f'Risk Score: {disruption_event["risk_score"]},\n\nSeverity: {disruption_event["Severity"]}'
            ).add_to(map)
        except Exception as e:
            print(f'Error adding disruption event AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA{disruption_event},type: {type(disruption_event)}')
            print(f'Error adding disruption event {disruption_event["id"]}: {e}')
            pass   

        return map
    @classmethod
    def addAll_disruption_event(cls,map: folium.Map, all_disruption_events:list[dict]) -> folium.Map:
        """
        Adds disruption event to map
        """
        for disruption_event in all_disruption_events:
            cls.addSingle_disruption_event(map, disruption_event)
        return map


mirxes_suppliers_info = supabaseExtractor.extractAllPNGSupplierInfo()
all_disruption_events = supabaseExtractor.extractAllArticles()
unique_disruption_types = supabaseExtractor.extractAllUniqueDisruptionType()
unique_disruption_types.append('All')

all_disruption_events_ranked_by_distance = DisruptionEventRanker.rankDisruptionEvents(all_disruption_events,mirxes_suppliers_info)
#print(len(all_disruption_events_ranked_by_distance))



# Display all the disruption events ranked by distance

# Place all withing a container?
# Add input for user to select how many top disruptions to display
col1, col2 = st.columns([0.5,0.5])
#Add dropdown for users to select how many top disruptions to display
top_no_disruptions = col1.selectbox('Select the number of top disruptions to display', [5,10,15,20])
# Add dropdown for users to select how far back to look for disruptions
days_disruption = col2.selectbox('Select the number of days to look back for disruptions', [365,30,7,1])
# select disruption categories
disruption_categories = st.multiselect("Select disruption Type", unique_disruption_types,default='All')
# Button to choose options for transport mode
transport_mode = st.multiselect("Select Transport type", ['Air','Sea','Road'],default=['Air','Sea','Road'])

st.markdown(f"<h2 style='text-align:center;'>🚨 Top Alerts: Disruption Events <Past {days_disruption}days> </h2>", unsafe_allow_html=True)

all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByDate(all_disruption_events_ranked_by_distance,days=days_disruption) # Hard coded 
# Filter by disruption categories
if 'All' not in disruption_categories:
    all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByCategory(all_disruption_events_ranked_by_distance,disruption_categories)

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

                m = folium.Map(location=[article_dict['lat'], article_dict['lng']], zoom_start=12)
                # Add all Mirxes suppliers to map
                m = MapManager.addAll_mirxes_suppliers(m, mirxes_suppliers_info)
                m = MapManager.addSingle_disruption_event(m, article_dict)
                folium_static(m)
                
                col1,col2 = st.columns([0.2,0.7])
                col1.markdown(f"<div><h4 style='text-align:center;'>Event Type:\n\n{article_dict['DisruptionType']}</h4></div>", unsafe_allow_html=True)
                # col1.image(f'./src/earthquake.png', use_column_width=True)
                col2.markdown(f"<h4 style='text-align:center;'>Supply Chain Disruption Potential\n\n{article_dict['risk_score']}</h4>", unsafe_allow_html=True)
                # Display Severity Metrics in a table
                st.markdown(f"<h3 style='text-align:center;'>Severity Metrics</h3>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='text-align:center;'>{article_dict['Severity']}</h4>", unsafe_allow_html=True)
                # Display Potential Suppliers Affected
                st.markdown(f"<h3 style='text-align:center;'>Potential Routes Affected</h3>", unsafe_allow_html=True)
                st.table(article_dict["suppliers"][:10])

                # Display output
                st.markdown(f"<h3 style='text-align: center;'>{article_dict['Title']} 😬</h3>", unsafe_allow_html=True)
                st.write(f'Article Url: {article_dict["Url"]}')
                st.image(f'{article_dict["ImageUrl"]}', use_column_width=True)

st.markdown(f"<h3 style='text-align:center;'>All Disruption Events: Past {days_disruption} days </h3>", unsafe_allow_html=True)
starting_coordinates = [13.5521, 103.8196]

# center on Liberty Bell 
m = folium.Map(location=starting_coordinates, zoom_start=4)

# add Mirxes suppliers 
MapManager.addAll_mirxes_suppliers(m, mirxes_suppliers_info)

# Add All disruption event
MapManager.addAll_disruption_event(m, all_disruption_events_ranked_by_distance)

# call to render Folium map in Streamlit
folium_static(m)