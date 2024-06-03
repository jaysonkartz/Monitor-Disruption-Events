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
from folium.plugins import MarkerCluster
# new
from streamlit_folium import st_folium
import jinja2
import pandas as pd
import datetime
import requests

import os
import sys
from supabase import create_client, Client
# Get the absolute path to the directory containing this script (app.py)
current_directory = os.path.dirname(os.path.realpath(__file__))

# Add the 'modules' directory to sys.path
LLM_directory = os.path.join(current_directory, 'llm')
Supabase_directory = os.path.join(current_directory, 'Supabase')
utils_directory = os.path.join(current_directory, 'utils')
sys.path.append(Supabase_directory)
sys.path.append(LLM_directory)
sys.path.append(utils_directory)

# The following keys should be typed in the "secret" fucntion in Streamlit deployment
# Reference: .env.sample
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

# Label at the top
# *new (origin: robot_face)
st.set_page_config(page_title="Disruption Monitoring", page_icon=":airplane:", layout="wide")


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

@st.cache_resource # Load data in Supabase
def load_supabase(SUPABASE_URL, SUPABASE_KEY) -> tuple[SupabaseInsertor,SupabaseExtractor]:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabaseInsertor = SupabaseInsertor(supabase)
    supabaseExtractor = SupabaseExtractor(supabase)
    return supabaseInsertor,supabaseExtractor

supabaseInsertor,supabaseExtractor = load_supabase(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource # Check NLTK installation
def checkNLTK():
    print('Checking NLTK installation')
    check_nltk_installation()

checkNLTK()

@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    return df
df_coor= load_data('https://raw.githubusercontent.com/LauraYu0918/ethical-test/main/worldcities.csv')


def retrieve_location_data():
    try:
        response = requests.get("http://localhost:8081/api/get-locations")
        if response.status_code == 200:
            data = response.json()
            parsed_data = data["location"]
            return parsed_data
            #print(parsed_data)
            #parsed_data = json.loads(data) # Extract the coordinates
            #coordinates = parsed_data["location"]
            #print(coordinates)
        else:
            print("Failed to retrieve location data from server")
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving location data: {e}")
 
# Call the function to retrieve location data
parsed_data = retrieve_location_data()

# Setting page title and header
st.markdown("<h3 style='text-align: center;'>Real Time Disruption Monitoring</h3>", unsafe_allow_html=True)
# Last updated date dd/mm/yyyy:

class MapManager: 
    """Class for managing the map and its components"""
    @classmethod
    def addAll_mirxes_suppliers(cls,map: folium.Map, mirxes_suppliers_info:list[dict]) -> folium.Map:
        """
        Adds Mirxes suppliers to map
        """
        # Optional: Use MarkerCluster for better visualization when there are many markers
        marker_cluster = MarkerCluster().add_to(map)

        for supplier in mirxes_suppliers_info:
            # Add marker for the supplier
            folium.Marker(
                [supplier['lat'], supplier['lng']], 
                popup=supplier['Name'], 
                # icon=folium.Icon(color=marker_color)
            ).add_to(marker_cluster)
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
        def format_popContent():
            popContent = (
            "<div style='text-align: center; font-size: 20px; font-weight: bold;'>Disruption Event Details</div>"
            + "<br>"
            + "<b>"
            + "Event Type: "
            + "</b>"
            + str(disruption_event["DisruptionType"])
            + "<br>"
            + "<b>"
            + "Supply Chain Disruption Potential: "
            + "</b>"
            + str(disruption_event["risk_score"])
            + "<br>"
            + "<b>"
            + "Severity Metrics: "
            + "</b>"
            + str(disruption_event["Severity"])
            + "<br>"
            + "<table border='1' style='border-collapse: collapse; width: 100%;'>"
            + "<tr><th>Supplier Name</th><th>Distance (KM)</th></tr>"
            )
            # Add rows to the table for each supplier
            for supplier in disruption_event["suppliers"][:10]:
                popContent += "<tr><td>" + str(supplier["Name"]) + "</td><td>" + str(round(supplier["distance"],2)) + "</td></tr>"
            popContent += "</table>"  # Close the table
            # Add remaining information to the popup content
            popContent += (
            "<br>"
            + "<b>"
            + str(disruption_event["Title"])
            + "😬"
            + "</b>"
            + "<br>"
            + "Article Url: "
            + "<a href='" + str(disruption_event["Url"]) + "' target='_blank'>" + str(disruption_event["Url"]) + "</a>"
            )
            return popContent
        popContent = format_popContent()

        iframe = folium.IFrame(popContent, width=350, height=350)
        popup1 = folium.Popup(iframe,min_width=350,max_width=350)
        try:
            folium.Circle(
                [disruption_event['lat'], disruption_event['lng']],
                radius=disruption_event['Radius'],
                color=colour_risk_mapping[disruption_event['risk_score']],
                fill=True,
                fill_color=colour_risk_mapping[disruption_event['risk_score']],
                tooltip=disruption_event['Title'],
                popup = popup1
                #popup=f'Risk Score: {disruption_event["risk_score"]},\n\nSeverity: {disruption_event["Severity"]}'
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


#@st.cache_resource
#def get_supabase_data():
#    mirxes_suppliers_info = supabaseExtractor.extractAllSupplierInfo()
#    all_disruption_events = supabaseExtractor.extractAllArticles()
#    unique_disruption_types = supabaseExtractor.extractAllUniqueDisruptionType()
#    unique_disruption_types.append('All')
#    return mirxes_suppliers_info,all_disruption_events,unique_disruption_types

#mirxes_suppliers_info,all_disruption_events,unique_disruption_types = get_supabase_data()

mirxes_suppliers_info = supabaseExtractor.extractAllSupplierInfo()
all_disruption_events = supabaseExtractor.extractAllArticles()
unique_disruption_types = supabaseExtractor.extractAllUniqueDisruptionType()

#unique_disruption_types.append('All')

all_disruption_events_ranked_by_distance = DisruptionEventRanker.rankDisruptionEvents(all_disruption_events,mirxes_suppliers_info)

left, right = st.columns((5,3))   
with right:
    # Display all the disruption events ranked by distance

    # Place all withing a container?
    # Add input for user to select how many top disruptions to display
    #col1, col2 = st.columns([0.5,0.5])
    #Add dropdown for users to select how many top disruptions to display
    
    # Radio buttons
    today = datetime.datetime.now()
    selection_option = st.radio(
        "Choose an option for time period selection",
        ["Number of days to look back", "Select a certain period"],
        index=0
    )
    days_disruption = None
    time_period = None
    if selection_option == "Number of days to look back":
        days_disruption = st.selectbox('Select the number of days to look back for disruptions', [30,7,1,365], disabled=False)
        time_period = st.date_input(
        "Select a period of time to detect disruptions",
        (datetime.date(today.year - 1, today.month, today.day), today),
        min_value=None,
        max_value=today,
        format="YYYY.MM.DD",
        disabled=True
        )
    else:
        days_disruption = st.selectbox('Select the number of days to look back for disruptions', [30,7,1,365], disabled=True)
        time_period = st.date_input(
        "Select a period of time to detect disruptions",
        (datetime.date(today.year - 1, today.month, today.day), today),
        min_value=None,
        max_value=today,
        format="YYYY.MM.DD",
        disabled=False
        )
        start_date, end_date = time_period
        days_disruption = (end_date - start_date).days

    # Select places to filter
    all_city_list = df_coor['city'].tolist()
    all_city_list.append('All')
    selected_city_filter = st.multiselect('Filter by cities',all_city_list,default="All") # Return a list with the option

    # Add dropdown for users to select how far back to look for disruptions
    #days_disruption = col2.selectbox('Select the number of days to look back for disruptions', [30,7,1,365])
    #today_month = today.strftime('%Y-%m')




    # select disruption categories
    unique_disruption_types.append('All')
    disruption_categories = st.multiselect("Select disruption type", unique_disruption_types,default='All')
    distance_threshold_filter = st.slider('Average distance filter disruption events ( KM )', 0, 1000, 1000)




#st.caption('Please enter coordinates shown on the map')
#cor1, cor2 = st.columns([0.5,0.5])
#input_cor1 = cor1.text_input('Longitude', '1.3521').strip()
#input_cor2 = cor2.text_input('Latitude', '103.8196').strip()




if selection_option == "Number of days to look back":
    all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByDate(all_disruption_events_ranked_by_distance,days_disruption)
else:
   # all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByDateRange(all_disruption_events_ranked_by_distance,start_date,end_date) # New function
    all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByAvgDistance(all_disruption_events_ranked_by_distance,distance_threshold_filter)

# Filter by disruption categories
if 'All' not in disruption_categories:
    all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByCategory(all_disruption_events_ranked_by_distance,disruption_categories)
# Filter by city
if 'All' not in selected_city_filter:
      all_disruption_events_ranked_by_distance = DisruptionEventRanker.filterDisruptionEventByCity(all_disruption_events_ranked_by_distance,selected_city_filter)

with left: 
    
    st.markdown(f"<h3 style='text-align:center;'>All Disruption Events: Past {days_disruption} days </h3>", unsafe_allow_html=True)
    
    selected_city = st.selectbox('Select a city to show on the map', df_coor['city'], index=89)
    selected_city_data = df_coor[df_coor['city'] == selected_city]
    selected_latitude = selected_city_data['lat'].values[0]
    selected_longitude = selected_city_data['lng'].values[0]
    if selected_latitude !='' and selected_longitude != '':
        input_longitude = selected_longitude
        input_latitude = selected_latitude
    else:
        input_latitude = 1.3521
        input_longitude = 103.8196

    input_coordinates = [input_latitude,input_longitude]

    #singapore_coordinates = [1.3521, 103.8196]
    #bioplasticBV_coordinates = [50.9085488, 6.0422086]
    

    # center on Liberty Bell
    if parsed_data:
        m = folium.Map(location=parsed_data,zoom_start=12)
    else:
        m = folium.Map(location=input_coordinates, zoom_start=12)

    # add Mirxes suppliers
    MapManager.addAll_mirxes_suppliers(m, mirxes_suppliers_info)

    # Add All disruption event
    MapManager.addAll_disruption_event(m, all_disruption_events_ranked_by_distance)
    # call to render Folium map in Streamlit
    st_data = st_folium(m, width=725, height=400)
    #folium_static(m, width=725)



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
                #folium_static(m, width=725)
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


