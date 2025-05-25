import streamlit as st
import pandas as pd
import requests
from PIL import Image
import io
import google.generativeai as genai
import snowflake.connector
import plotly.express as px
from datetime import datetime
import pytz
from streamlit_folium import folium_static
import folium
from geopy.geocoders import Nominatim
import random
import json
import os
from faker import Faker
import time
import base64
from io import BytesIO

# --- Configuration ---
class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCQe4jVtHclwO2bEj7jBcrUyBChonDRaW0")
    SNOWFLAKE_CONFIG = {
        'user': os.getenv("SNOWFLAKE_USER","SUBHASHREE"),
        'password': os.getenv("SNOWFLAKE_PASSWORD","071825Subhashree"),
        'account': os.getenv("SNOWFLAKE_ACCOUNT","khqxqzz-kb71059"),
        'warehouse': os.getenv("SNOWFLAKE_WAREHOUSE","COMPUTE_WH"),
        'database': os.getenv("SNOWFLAKE_DATABASE","TOURIST"),
        'schema': os.getenv("SNOWFLAKE_SCHEMA","PUBLIC")
    }
    STATES_DATA = "states_data.json"
    FESTIVALS_DATA = "festivals_data.json"
    DEFAULT_IMAGES = {
        'state': "default.jpg",
        'food': "default.jpg",
        'festival': "default.jpg",
        'spot': "default.jpg",
        'art': "default.jpg"
    }

# --- Utility Functions ---
class Utils:
    
    @staticmethod
    def get_local_art_image(art_name):
        try:
            # Normalize the art name for filename matching
            normalized_name = art_name.lower().replace(" ", "_")
            
            # Define the base path to your images folder
            base_path = "C:/Users/subha/Snowflake/assets/images/"
            
            # Possible image extensions to check
            extensions = ['.jpg', '.jpeg', '.png', '.webp']
            
            # Check for matching files
            for ext in extensions:
                img_path = f"{base_path}{normalized_name}{ext}"
                if os.path.exists(img_path):
                    return img_path
            
            # If no exact match, try partial matches
            for file in os.listdir(base_path):
                if normalized_name in file.lower():
                    return f"{base_path}{file}"
                    
            return None  # Return None if no image found
        except Exception as e:
            print(f"Error searching for local art image: {e}")
            return None



    @staticmethod
    def get_image(path, width=None):
        try:
            if path.startswith('http'):
                response = requests.get(path)
                img = Image.open(BytesIO(response.content))
            else:
                # Try to open the image from local path
                img = Image.open(path)
                
            if width:
                ratio = width / img.width
                height = int(img.height * ratio)
                img = img.resize((width, height))
            return img
        except Exception as e:
            print(f"Error loading image: {e}")
            # Return a default gray image if the specific image isn't found
            return Image.new('RGB', (800, 400), color='gray')

    @staticmethod
    def generate_stats(state):
        return {
            'visitors': random.randint(500000, 5000000),
            'foreign_visitors': random.randint(50000, 500000),
            'popular_months': random.sample(['Jan', 'Feb', 'Mar', 'Oct', 'Nov', 'Dec'], 3),
            'avg_stay': random.randint(2, 7)
        }

    @staticmethod
    def get_weather(city):
        conditions = ["Sunny", "Partly Cloudy", "Rainy", "Humid", "Foggy"]
        return {
            'temp': random.randint(15, 35),
            'condition': random.choice(conditions),
            'icon': "☀️" if "Sunny" in conditions else "🌧️"
        }

# --- AI Services ---
class AIServices:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.fake = Faker()

    def generate_response(self, prompt, context=""):
        try:
            full_prompt = f"""
            You are 'Sanskriti Sangam AI', an expert on Indian culture, heritage, and tourism.
            Context: {context}
            Question: {prompt}
            
            Provide a detailed response with:
            1. Historical context (if applicable)
            2. Cultural significance
            3. Practical visiting information
            4. Local customs/etiquette
            5. Recommendations
            
            Format with:
            - Clear sections
            - Emojis for visual appeal
            - Bold for important info
            - Bullet points when listing items
            
            Keep the tone warm and informative, like a knowledgeable local guide.
            """
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"⚠️ Couldn't generate response. Error: {str(e)}"

    def generate_state_info(self, state):
        prompt = f"""
        Provide comprehensive cultural information about {state}, India including:
        - Traditional art forms
        - Major festivals
        - Local language(s)
        - Famous local foods
        - Traditional dress
        - Folk music
        - Handicrafts
        
        Format as a JSON-style dictionary with these keys:
        'art', 'festivals', 'language', 'food', 'dress', 'music', 'handicrafts'
        """
        response = self.generate_response(prompt)
        try:
            # Extract JSON from response
            json_str = response[response.find("{"):response.rfind("}")+1]
            return json.loads(json_str)
        except:
            # Fallback to plain text response
            return {
                'art': response,
                'festivals': response,
                'language': response,
                'food': response,
                'dress': response,
                'music': response,
                'handicrafts': response
            }

    def generate_tourist_spots(self, state):
        prompt = f"""
        Generate a list of 5-7 major tourist attractions in {state}, India with:
        - Name of each attraction
        - Detailed description
        - What makes it unique or why it's less visited
        - Typical entry fees for Indians and foreigners
        - Approximate travel costs
        - Best months to visit
        - Latitude and longitude coordinates
        - Whether it's a UNESCO heritage site
        
        Format as a JSON list with these keys:
        'TOURIST_SPOTS', 'DESCRIPTION', 'WHY_UNIQUE_AND_LESS_VISITED',
        'ENTRY_FEE_INR', 'ENTRY_FEE_FOREIGN', 'TRAVEL_COST_APPROX',
        'BEST_VISITING_MONTHS', 'LATITUDE', 'LONGITUDE', 'UNESCO_HERITAGE_SITE'
        """
        response = self.generate_response(prompt)
        try:
            # Extract JSON from response
            json_str = response[response.find("["):response.rfind("]")+1]
            spots = json.loads(json_str)
            # Add common fields
            for spot in spots:
                spot['GOOGLE_MAPS_LINK'] = "https://maps.google.com"
                spot['BOOKING_LINK'] = "https://example.com"
            return spots
        except:
            # Fallback to generating individual spots
            spots = []
            for i in range(1, random.randint(4, 8)):
                spot_prompt = f"""
                Describe a tourist attraction in {state} called '{state} Attraction {i}' including:
                - Detailed description
                - What makes it unique
                - Entry fees for Indians and foreigners
                - Approximate travel costs
                - Best months to visit
                - Whether it's a UNESCO heritage site
                """
                spot_desc = self.generate_response(spot_prompt)
                spots.append({
                    'TOURIST_SPOTS': f"{state} Attraction {i}",
                    'DESCRIPTION': spot_desc,
                    'WHY_UNIQUE_AND_LESS_VISITED': self.generate_response(f"What makes {state} Attraction {i} unique?"),
                    'ENTRY_FEE_INR': random.randint(50, 1000),
                    'ENTRY_FEE_FOREIGN': random.randint(10, 50),
                    'TRAVEL_COST_APPROX': random.randint(1000, 10000),
                    'GOOGLE_MAPS_LINK': "https://maps.google.com",
                    'BOOKING_LINK': "https://example.com",
                    'UNESCO_HERITAGE_SITE': random.choice([True, False]),
                    'BEST_VISITING_MONTHS': random.choice(["Oct-Mar", "Nov-Feb", "Year-round"]),
                    'LATITUDE': random.uniform(8.0, 37.0),
                    'LONGITUDE': random.uniform(68.0, 97.0)
                })
            return spots

    def generate_festivals(self):
        prompt = """
        Generate a list of 10 major festivals across different states of India with:
        - Festival name
        - State(s) where it's celebrated
        - Month(s) of celebration
        - Detailed description
        - Cultural significance
        
        Format as a JSON list with these keys:
        'FESTIVAL_NAME', 'STATE', 'MONTH', 'DESCRIPTION', 'SIGNIFICANCE'
        """
        response = self.generate_response(prompt)
        try:
            # Extract JSON from response
            json_str = response[response.find("["):response.rfind("]")+1]
            return json.loads(json_str)
        except:
            # Fallback to basic festivals
            return [
                {
                    "FESTIVAL_NAME": "Diwali",
                    "STATE": "Nationwide",
                    "MONTH": "October/November",
                    "DESCRIPTION": "Festival of lights celebrating the victory of good over evil",
                    "SIGNIFICANCE": "One of India's most important festivals"
                },
                {
                    "FESTIVAL_NAME": "Holi",
                    "STATE": "Nationwide",
                    "MONTH": "March",
                    "DESCRIPTION": "Festival of colors celebrating spring and love",
                    "SIGNIFICANCE": "Marks the arrival of spring and victory of good"
                }
            ]

    def generate_itinerary(self, place, days=3):
        prompt = f"""
        Create a {days}-day cultural itinerary for {place} including:
        - Morning, afternoon, evening activities each day
        - Must-visit cultural sites
        - Local food experiences
        - Cultural performances/shows
        - Transportation tips
        - Budget estimates (₹500-₹2000, ₹2000-₹5000, ₹5000+)
        
        Format as a markdown table with emojis.
        """
        return self.generate_response(prompt)

# --- Database Services ---
class Database:
    def __init__(self):
        self.conn = None
        self.ai = AIServices()
        
    def connect(self):
        try:
            self.conn = snowflake.connector.connect(**Config.SNOWFLAKE_CONFIG)
            return True
        except:
            return False

    def get_states(self):
        if self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT DISTINCT STATE FROM TOURISM_PLACES_CLEAN ORDER BY STATE")
                return [row[0] for row in cursor.fetchall()]
            except:
                pass
        
        # Fallback to AI-generated list of Indian states
        response = self.ai.generate_response("List all Indian states and union territories")
        states = [line.split('-')[0].strip() for line in response.split('\n') if line.strip()]
        return states if states else ["Rajasthan", "Kerala", "Tamil Nadu", "Himachal Pradesh", "Goa"]

    def get_state_info(self, state):
        if self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute(f"""
                    SELECT ART, FESTIVALS, LOCAL_LANGUAGE, FAMOUS_LOCAL_FOOD
                    FROM TOURISM_PLACES_CLEAN 
                    WHERE STATE = '{state}' 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                if result:
                    return {
                        'art': result[0],
                        'festivals': result[1],
                        'language': result[2],
                        'food': result[3]
                    }
            except:
                pass
        
        # Fallback to AI-generated state info
        return self.ai.generate_state_info(state)

    def get_tourist_spots(self, state):
        if self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute(f"""
                    SELECT TOURIST_SPOTS, DESCRIPTION, WHY_UNIQUE_AND_LESS_VISITED,
                           ENTRY_FEE_INR, ENTRY_FEE_FOREIGN, TRAVEL_COST_APPROX,
                           GOOGLE_MAPS_LINK, BOOKING_LINK, UNESCO_HERITAGE_SITE,
                           BEST_VISITING_MONTHS, LATITUDE, LONGITUDE
                    FROM TOURISM_PLACES_CLEAN 
                    WHERE STATE = '{state}'
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            except:
                pass
        
        # Fallback to AI-generated tourist spots
        return self.ai.generate_tourist_spots(state)

    def get_festivals(self):
        if self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT FESTIVAL_NAME, STATE, MONTH, DESCRIPTION, SIGNIFICANCE
                    FROM FESTIVALS
                    ORDER BY MONTH
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            except:
                pass
        
        # Fallback to AI-generated festivals
        return self.ai.generate_festivals()

    def get_art_info(self, state):
        try:
            cursor = self.conn.cursor()
            # Sanitize the state value to prevent SQL injection
            safe_state = state.replace("'", "''")

            query = f"""
                SELECT STATE, ART_NAME, ART_DESC
                FROM INDIAN_TRADITIONAL_ARTS
                WHERE LOWER(STATE) = LOWER('{safe_state}')
            """

            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            print(f"Error fetching art info: {e}")
            return []

    def fetch_tourism_data(self):
        query = """
        SELECT STATE, CAPITAL, POPULATION_M, AREA_KM2, OFFICIAL_LANGUAGE,
               TOURIST_VISITORS_PER_YEAR, FOREIGN_VISITORS, AVERAGE_STAY_DURATION, TOP_ATTRACTION
        FROM TOURISM_STATS
        """
        if not self.conn:
            st.error("❌ Snowflake database is not connected.")
            return pd.DataFrame()  # return empty DataFrame to avoid crash

        cs = self.conn.cursor()
        try:
            cs.execute(query)
            rows = cs.fetchall()
            columns = [col[0] for col in cs.description]
            import pandas as pd
            return pd.DataFrame(rows, columns=columns)
        finally:
            cs.close()

# --- UI Components ---
class UIComponents:
    @staticmethod
    def setup_page():
        st.set_page_config(
            page_title="Sanskriti Sangam",
            page_icon="🇮🇳",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': 'https://github.com/yourusername/bharat-darshan',
                'Report a bug': "https://github.com/yourusername/bharat-darshan/issues",
                'About': """
                # Sanskriti Sangam\n
                Where Traditions Unite – A Journey Through India’s Heritage\n
                Developed with ❤️ for Incredible India
                """
            }
        )
        
        # Inject custom CSS
        st.markdown("""
        <style>
            .state-card {
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
                transition: 0.3s;
                background-color: #ffffff;
            }
            .state-card:hover {
                box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
                transform: translateY(-5px);
            }
            .spot-card {
                border-left: 4px solid #4CAF50;
                padding: 12px;
                margin: 8px 0;
                background-color: #f9f9f9;
                transition: all 0.3s ease;
            }
            .less-visited {
                border-left: 4px solid #FF5722;
            }
            .price-tag {
                background-color: #4CAF50;
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                display: inline-block;
                margin: 2px;
            }
            .heritage-badge {
                background-color: #FFC107;
                color: #000;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: bold;
                display: inline-block;
            }
            .fade-in {
                animation: fadeIn 1s ease-in;
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            .st-emotion-cache-1v0mbdj {
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def create_navigation():
        if 'page' not in st.session_state:
            st.session_state.page = "🏠 Home"
            
        with st.sidebar:
            try:
                st.image("default.jpg", width=250)
            except:
                st.image(Image.new('RGB', (250, 250), color='gray'), width=250)
            st.title("Explore India")
            
            pages = [
                "🏠 Home", "🗺️ Interactive Map", "🏛️ States", 
                "🌟 Hidden Gems", "📅 Festivals", "💬 AI Guide", 
                "📊 Insights", "🧳 Trip Planner"
            ]
            
            st.session_state.page = st.radio(
                "Navigate",
                pages,
                index=pages.index(st.session_state.page))
            
            st.markdown("---")
            st.markdown("### Current Weather in India")
            weather = Utils.get_weather("Delhi")
            st.markdown(f"""
                <div style='font-size: 1.2em;'>
                    {weather['icon']} {weather['temp']}°C, {weather['condition']}
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            if st.button("🔄 Reset App"):
                st.session_state.clear()
                st.rerun()

# --- Main App Pages ---
class AppPages:
    def __init__(self):
        self.db = Database()
        self.db.connect()
        self.ai = AIServices()
        
    def home_page(self):
     
        with open("assets/images/banner.png", "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode()

        st.markdown(f"""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari&family=Playfair+Display:wght@700&display=swap');

                .banner-container {{
                    position: relative;
                    width: 100%;
                    height: 280px;
                    background: linear-gradient(rgba(255, 255, 255, 0.45), rgba(255, 255, 255, 0.45)),
                                url("data:image/png;base64,{encoded_image}") no-repeat center center;
                    background-size: cover;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    border-radius: 16px;
                    margin-bottom: 2rem;
                    animation: fadeIn 1.5s ease-in-out;
                    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
                }}

                .hindi-title {{
                    font-family: 'Noto Sans Devanagari', sans-serif;
                    color: #001a57;
                    font-size: 3rem;
                    font-weight: 900;
                    margin: 0;
                }}

                .english-title {{
                    font-family: 'Playfair Display', serif;
                    color: #001a57;
                    font-size: 1.6rem;
                    font-weight: 700;
                    margin-top: 0.3rem;
                    margin-bottom: 0.3rem;
                }}

                .subtitle {{
                    font-family: 'Playfair Display', serif;
                    color: #1a1a1a;
                    font-size: 1.5rem;
                    font-weight: 600;
                    max-width: 80%;
                    margin: auto;
                }}

                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: translateY(20px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
            </style>

            <div class="banner-container">
                <div class="hindi-title">संस्कृति संगम</div>
                <div class="english-title">Sanskriti Sangam</div>
                <p class="subtitle">A Digital Pilgrimage Through India’s Heritage</p>
            </div>
        """, unsafe_allow_html=True)

        st.header("✨ Discover Incredible India ✨")
        st.write("Explore the diverse culture, art, festivals, and hidden gems across Indian states. Scroll down to begin your journey!")




        
        # Featured states
        st.subheader("✨ Featured States")
        featured = ["Rajasthan", "Kerala", "Tamil Nadu", "Himachal Pradesh", "Goa"]
        cols = st.columns(5)
        for i, state in enumerate(featured):
            with cols[i]:
                # Try to load state-specific image, fallback to default
                img_path = f"C:\\Users\\subha\\Snowflake\\assets\\images\\{state.lower().replace(' ', '_')}.jpg"
                try:
                    img = Utils.get_image(img_path)
                except:
                    img = Utils.get_image(Config.DEFAULT_IMAGES['state'])
                st.image(img, use_column_width=True, caption=state)
                if st.button(f"Explore {state}", key=f"featured_{state}"):
                    st.session_state['selected_state'] = state
                    st.session_state.page = "🏛️ States"
                    st.rerun()
        
        # All states grid
        st.markdown("---")
        st.subheader("All States & Union Territories")
        states = self.db.get_states()
        
        cols = st.columns(4)
        for i, state in enumerate(states):
            with cols[i % 4]:
                with st.container():
                    # Try to load state-specific image, fallback to default
                    img_path = f"C:\\Users\\subha\\Snowflake\\assets\\images\\{state.lower().replace(' ', '_')}.jpg"
                    try:
                        img = Utils.get_image(img_path)
                    except:
                        img = Utils.get_image(Config.DEFAULT_IMAGES['state'])
                    st.image(img, use_column_width=True, caption=state)
                    
                    if st.button(f"Explore {state}", key=f"btn_{state}"):
                        st.session_state['selected_state'] = state
                        st.session_state.page = "🏛️ States"
                        st.rerun()

    def state_page(self):
        if 'selected_state' not in st.session_state:
            st.warning("Please select a state from the Home page")
            return

        state = st.session_state['selected_state']
        st.title(f"{state} Cultural Exploration")

        # Header
        col1, col2 = st.columns([1, 2])
        with col1:
            # Try to load state-specific image, fallback to default
            img_path = f"C:\\Users\\subha\\Snowflake\\assets\\images\\{state.lower().replace(' ', '_')}.jpg"



            try:
                img = Utils.get_image(img_path)
            except:
                img = Utils.get_image(Config.DEFAULT_IMAGES['state'])
            st.image(img, use_column_width=True)

        with col2:
            stats = Utils.generate_stats(state)
            st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; color: black'>
                    <h3 style='color:black'>Quick Facts</h3>
                    <p><b>Annual Visitors:</b> {stats['visitors']:,}</p>
                    <p><b>Foreign Visitors:</b> {stats['foreign_visitors']:,}</p>
                    <p><b>Best Months:</b> {', '.join(stats['popular_months'])}</p>
                    <p><b>Avg Stay Duration:</b> {stats['avg_stay']} days</p>
                </div>
            """, unsafe_allow_html=True)

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["🎨 Art", "🎭 Culture", "🏞️ Places", "🍽️ Cuisine"])

        # 🎨 ART TAB
        with tab1:
            st.markdown(
                f"<h2 style='font-weight: bold; margin-bottom: 20px;'>🎨 Traditional Art Forms of {state}</h2>",
                unsafe_allow_html=True
            )

            art_entries = self.db.get_art_info(state)

            if not art_entries:
                st.warning("No art information found for this state.")
                ai_art_info = self.ai.generate_response(
                    f"List 3 traditional art forms from {state}, India with brief descriptions"
                )
                st.markdown(
                    f"<div class='state-card' style='color: black; padding: 15px; border-radius: 10px;'>{ai_art_info}</div>",
                    unsafe_allow_html=True
                )
            else:
                for i, art in enumerate(art_entries):
                    art_name = art['art_name']

                    with st.expander(f"🎨 {art_name}", expanded=(i == 0)):
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            # First try local assets folder
                            local_img_path = Utils.get_local_art_image(art_name)
                            
                            # Then try Wikipedia if local image not found
                            
                            image_url = local_img_path
                            
                            # Fallback to default image
                            if not image_url:
                                image_url = Config.DEFAULT_IMAGES.get('art')
                            
                            st.image(
                                image_url,
                                use_column_width=True,
                                caption=f"{art_name} from {state}"
                            )

                        with col2:
                            detailed_info = self.ai.generate_response(
                                f"Provide a comprehensive cultural overview of '{art_name}' from {state} covering:\n"
                                "1. Historical origins and evolution timeline\n"
                                "2. Detailed description of the art form\n"
                                "3. Materials and techniques used (with specific local terms)\n"
                                "4. Notable artists and their contributions\n"
                                "5. Where to experience authentic pieces (specific locations)\n"
                                "6. Cultural and religious significance\n"
                                "7. Current preservation efforts\n\n"
                                "Format with clear sections in black color text and use emojis for visual appeal only 100 words"
                            )

                            st.markdown(
                                f"<div class='state-card fade-in' style='color: black;'>{detailed_info}</div>",
                                unsafe_allow_html=True
                            )

                    if i < len(art_entries) - 1:
                        st.markdown("<hr style='margin: 20px 0; border-color: #f0f2f6'>", unsafe_allow_html=True)



        # 🎭 CULTURE TAB
        with tab2:
            info = self.db.get_state_info(state)
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🎉 Festivals")
                st.markdown(f"<div class='state-card fade-in' style='color: black;'>{info.get('festivals', 'Data not available')}</div>", unsafe_allow_html=True)


               

            with col2:
                st.subheader("🗣️ Local Language")
                st.markdown(f"<div class='state-card fade-in' style='color: black;'>{info.get('language', 'Data not available')}</div>", unsafe_allow_html=True)

               

        # 🏞️ PLACES TAB
        with tab3:
            st.header("Tourist Destinations")
            spots = self.db.get_tourist_spots(state)

            for spot in spots:
                with st.expander(spot['TOURIST_SPOTS'], expanded=False):
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.image(Utils.get_image(Config.DEFAULT_IMAGES['spot']), use_column_width=True)
                        if spot['UNESCO_HERITAGE_SITE']:
                            st.markdown("<div class='heritage-badge'>UNESCO World Heritage Site</div>", unsafe_allow_html=True)

                    with col2:
                        st.write(spot['DESCRIPTION'])
                        st.markdown(f"**Why visit?** {spot['WHY_UNIQUE_AND_LESS_VISITED']}")
                        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

                        cols = st.columns(3)
                        cols[0].markdown(f"<div class='price-tag'>₹{spot['ENTRY_FEE_INR']} (Indian)</div>", unsafe_allow_html=True)
                        cols[1].markdown(f"<div class='price-tag'>${spot['ENTRY_FEE_FOREIGN']} (Foreign)</div>", unsafe_allow_html=True)
                        cols[2].markdown(f"<div class='price-tag'>Best: {spot['BEST_VISITING_MONTHS']}</div>", unsafe_allow_html=True)

                        if st.button("📍 View on Map", key=f"map_{spot['TOURIST_SPOTS']}"):
                            m = folium.Map(location=[spot['LATITUDE'], spot['LONGITUDE']], zoom_start=12)
                            folium.Marker(
                                [spot['LATITUDE'], spot['LONGITUDE']],
                                popup=spot['TOURIST_SPOTS'],
                                icon=folium.Icon(color='blue')
                            ).add_to(m)
                            folium_static(m, width=700, height=400)

        # 🍽️ CUISINE TAB
        with tab4:
            st.header("🍽️ Culinary Delights")
            info = self.db.get_state_info(state)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Signature Dishes")
                st.markdown(f"<div class='state-card' style='color: black;'>{info.get('food', 'Data not available')}</div>", unsafe_allow_html=True)

                st.subheader("Food Recommendation")
                itinerary = self.ai.generate_itinerary(state, days=2)
                st.markdown(itinerary)

            with col2:
                st.image(Utils.get_image(Config.DEFAULT_IMAGES['food']), use_column_width=True, caption=f"{state} Cuisine")

    def chatbot_page(self):
        st.title("💬 Sanskriti Sangam AI Guide")
        st.markdown("Ask me anything about Indian culture, heritage, or travel tips!")
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "content": "Namaste! I'm your AI guide to India's cultural heritage. How can I help you explore today?"}
            ]
        
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask about Indian culture..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Researching Indian cultural insights..."):
                    response = self.ai.generate_response(prompt)
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        if st.button("Clear Conversation"):
            st.session_state.chat_history = [
                {"role": "assistant", "content": "Namaste! I'm your AI guide to India's cultural heritage. How can I help you explore today?"}
            ]
            st.rerun()



    def interactive_map_page(self):
            st.title("🗺️ Interactive India Map")
            st.markdown("Explore cultural landmarks across India")

            # Base map
            m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)

            # Example landmarks
            landmarks = [
                {"name": "Taj Mahal", "location": [27.1751, 78.0421], "type": "UNESCO"},
                {"name": "Hampi", "location": [15.3350, 76.4600], "type": "UNESCO"},
                {"name": "Kerala Backwaters", "location": [9.4981, 76.3388], "type": "Nature"},
                {"name": "Brihadeeswara Temple, Mahabalipuram", "location": [10.7867, 79.1378], "type": "Cultural"},
        {"name": "Tirupati, Lepakshi, Araku Valley", "location": [15.9129, 79.74], "type": "Cultural"},
        {"name": "Tawang Monastery, Ziro Valley, Namdapha Park", "location": [27.1004, 93.6167], "type": "Cultural"},
        {"name": "Kaziranga, Majuli Island, Kamakhya Temple", "location": [26.2006, 92.9376], "type": "Cultural"},
        {"name": "Mahabodhi Temple, Nalanda, Vikramshila", "location": [25.0961, 85.3131], "type": "Cultural"},
        {"name": "Chitrakote Falls, Kanger Valley, Bastar", "location": [21.2787, 81.8661], "type": "Cultural"},
        {"name": "Basilica of Bom Jesus, Fort Aguada, Palolem Beach", "location": [15.2993, 74.124], "type": "Cultural"},
        {"name": "Rann of Kutch, Somnath Temple, Champaner-Pavagadh", "location": [22.2587, 71.1924], "type": "Cultural"},
        {"name": "Kurukshetra, Pinjore, Morni Hills", "location": [29.0588, 76.0856], "type": "Cultural"},
        {"name": "Shimla, Manali, Dharamshala, Spiti", "location": [31.1048, 77.1734], "type": "Cultural"},
        {"name": "Betla Park, Netarhat, Amadubi", "location": [23.6102, 85.2799], "type": "Cultural"},
        {"name": "Hampi, Coorg, Chikmagalur, Mysore Palace", "location": [15.3173, 75.7139], "type": "Cultural"},
        {"name": "Munnar, Alleppey, Sabarimala, Guruvayur", "location": [10.8505, 76.2711], "type": "Cultural"},
        {"name": "Khajuraho Temples, Sanchi Stupa, Bandhavgarh, Bhimbetka", "location": [22.9734, 78.6569], "type": "Cultural"},
        {"name": "Ajanta & Ellora Caves, Elephanta Caves, Raigad Fort", "location": [19.7515, 75.7139], "type": "Cultural"},
        {"name": "Loktak Lake, Kangla Fort, Ukhrul", "location": [24.6637, 93.9063], "type": "Cultural"},
        {"name": "Shillong, Cherrapunji, Living Root Bridges", "location": [25.467, 91.3662], "type": "Cultural"},
        {"name": "Aizawl, Phawngpui, Vantawng Falls", "location": [23.1645, 92.9376], "type": "Cultural"},
        {"name": "Kohima, Dzukou Valley, Mokokchung", "location": [26.1584, 94.5624], "type": "Cultural"},
        {"name": "Konark, Puri, Chilika Lake", "location": [20.9517, 85.0985], "type": "Cultural"},
        {"name": "Golden Temple, Wagah Border, Anandpur Sahib", "location": [31.1471, 75.3412], "type": "Cultural"},
        {"name": "Jaipur, Udaipur, Jaisalmer Fort, Chittorgarh Fort", "location": [27.0238, 74.2179], "type": "Cultural"},
        {"name": "Nathula Pass, Yumthang Valley, Rumtek Monastery", "location": [27.533, 88.5122], "type": "Cultural"},
        {"name": "Charminar, Golconda, Ramappa Temple", "location": [17.1232, 79.2088], "type": "Cultural"},
        {"name": "Ujjayanta Palace, Neermahal, Unakoti", "location": [23.9408, 91.9882], "type": "Cultural"},
        {"name": "Varanasi, Agra, Lucknow, Mathura", "location": [26.8467, 80.9462], "type": "Cultural"},
        {"name": "Rishikesh, Nainital, Valley of Flowers", "location": [30.0668, 79.0193], "type": "Cultural"},
        {"name": "Sundarbans, Darjeeling, Bishnupur Terracotta Temples", "location": [22.9868, 87.855], "type": "Cultural"}
            ]

            for landmark in landmarks:
                icon = folium.Icon(
                    color="gold" if landmark["type"] == "UNESCO" else "blue",
                    icon="star" if landmark["type"] == "UNESCO" else "info-sign"
                )
                folium.Marker(
                    location=landmark["location"],
                    popup=landmark["name"],
                    icon=icon
                ).add_to(m)

            folium_static(m, width=1000, height=600)

            # Search feature
            st.subheader("Search Locations")
            search_query = st.text_input("Enter a place name:")

            if search_query:
                with st.spinner(f"Searching for {search_query}..."):
                    query_prompt = (
                        f"Give location details for '{search_query}' in India "
                        f"in this JSON format only:\n"
                        f'{{"name": "...", "latitude": ..., "longitude": ..., "description": "..."}}'
                    )
                    response = self.ai.generate_response(query_prompt)

                    try:
                        import re
                        import json

                        # Extract the first JSON object from the response
                        match = re.search(r'\{.*?\}', response, re.DOTALL)
                        if not match:
                            raise ValueError("No JSON object found in the response.")

                        json_text = match.group(0)
                        location_data = json.loads(json_text)

                        lat = float(location_data["latitude"])
                        lon = float(location_data["longitude"])
                        description = location_data.get("description", "No description available.")

                        # Display result
                        m2 = folium.Map(location=[lat, lon], zoom_start=12)
                        folium.Marker(
                            location=[lat, lon],
                            popup=search_query,
                            icon=folium.Icon(color="red")
                        ).add_to(m2)

                        st.success(f"Showing results for: {location_data['name']}")
                        st.markdown(description)
                        folium_static(m2, width=1000, height=400)

                    except Exception as e:
                        st.warning(f"Could not parse location from response. Error: {e}")
                        st.markdown(response)

    def festivals_page(self):
        st.title("📅 Indian Festivals Calendar")
        st.markdown("Plan your visit around India's vibrant festivals")
        
        festivals = self.db.get_festivals()
        
        for festival in festivals:
            with st.expander(f"{festival['FESTIVAL_NAME']} - {festival['STATE']} ({festival['MONTH']})"):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image("https://via.placeholder.com/150", use_column_width=True)
                with col2:
                    st.markdown(f"**When:** {festival['MONTH']}")
                    st.markdown(f"**Where:** {festival['STATE']}")
                    st.markdown(f"**Significance:** {festival['SIGNIFICANCE']}")
                    st.write(festival['DESCRIPTION'])
                    
                    if st.button(f"🎉 Get AI Celebration Tips for {festival['FESTIVAL_NAME']}"):
                        tips = self.ai.generate_response(
                            f"Provide celebration tips for {festival['FESTIVAL_NAME']} in {festival['STATE']} including: "
                            "1. Best places to experience it "
                            "2. Traditional rituals to observe "
                            "3. Special foods to try "
                            "4. Cultural etiquette "
                            "5. Photography tips"
                        )
                        st.markdown(tips)

    def hidden_gems_page(self):
        st.title("🌟 Hidden Gems of India")
        st.markdown("Discover off-the-beaten-path destinations")
        
        # Get hidden gems from AI
        with st.spinner("Finding unique hidden gems..."):
            response = self.ai.generate_response(
                "List 6 hidden gem destinations in India with: "
                "1. Name and state "
                "2. Brief description (50 words) "
                "3. Why it's special "
                "Format as a JSON list with keys: 'name', 'state', 'description', 'reason'"
            )
            
            try:
                gems = json.loads(response[response.find("["):response.rfind("]")+1])
            except:
                gems = [
                    {
                        "name": "Chettinad Mansions",
                        "state": "Tamil Nadu",
                        "description": "Grand mansions with unique architecture in the Chettinad region",
                        "reason": "Lesser-known architectural marvels"
                    },
                    {
                        "name": "Majuli Island",
                        "state": "Assam",
                        "description": "World's largest river island with unique Vaishnavite culture",
                        "reason": "Unique cultural preservation"
                    }
                ]
        
        cols = st.columns(3)
        for i, gem in enumerate(gems):
            with cols[i % 3]:
                with st.container():
                    st.subheader(gem["name"])
                    st.caption(gem["state"])
                    st.image(Utils.get_image(Config.DEFAULT_IMAGES['spot']), 
                            use_column_width=True)
                    st.write(gem["description"])
                    
                    if st.button("Explore", key=f"gem_{gem['name']}"):
                        st.session_state['selected_gem'] = gem
                        st.rerun()

    def fetch_tourism_data(self):
        query = """
            SELECT STATE, CAPITAL, POPULATION_M, AREA_KM2, OFFICIAL_LANGUAGE,
                TOURIST_VISITORS_PER_YEAR, FOREIGN_VISITORS, AVERAGE_STAY_DURATION, TOP_ATTRACTION
            FROM STATE_STATS
        """
        if not self.db.conn:
            st.error("❌ Snowflake database is not connected.")
            return pd.DataFrame()  # return empty DataFrame to avoid crash

        cs = self.db.conn.cursor()
        try:
            cs.execute(query)
            rows = cs.fetchall()
            columns = [col[0] for col in cs.description]
            import pandas as pd
            return pd.DataFrame(rows, columns=columns)
        finally:
            cs.close()

    def insights_page(self):
        import pandas as pd
        import plotly.express as px
        import streamlit as st

        st.title("📊 Tourism Insights")
        st.markdown("Data-driven insights about Indian tourism")

        # ✅ This line must be inside the method
        df = self.fetch_tourism_data()

        # Bar chart: Top states by visitors
        fig1 = px.bar(
            df,
            x="STATE",
            y="TOURIST_VISITORS_PER_YEAR",
            color="STATE",
            title="Top States by Annual Tourist Visitors",
            labels={"TOURIST_VISITORS_PER_YEAR": "Total Visitors"}
        )
        st.plotly_chart(fig1, use_container_width=True)

        # Foreign visitors
        fig2 = px.bar(
            df,
            x="STATE",
            y="FOREIGN_VISITORS",
            color="STATE",
            title="Foreign Tourist Visitors per State",
            labels={"FOREIGN_VISITORS": "Foreign Visitors"}
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Stay duration
        fig3 = px.line(
            df,
            x="STATE",
            y="AVERAGE_STAY_DURATION",
            markers=True,
            title="Average Stay Duration per Tourist (in days)",
            labels={"AVERAGE_STAY_DURATION": "Stay Duration (days)"}
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Bubble chart: Population vs. Visitors
        fig4 = px.scatter(
            df,
            x="POPULATION_M",
            y="TOURIST_VISITORS_PER_YEAR",
            size="AVERAGE_STAY_DURATION",
            color="STATE",
            hover_name="TOP_ATTRACTION",
            title="Population vs Tourist Visitors (Bubble = Stay Duration)",
            labels={
                "POPULATION_M": "Population (millions)",
                "TOURIST_VISITORS_PER_YEAR": "Total Visitors"
            }
        )
        st.plotly_chart(fig4, use_container_width=True)

        # Show raw data
        with st.expander("📋 View Raw Data"):
            st.dataframe(df)

        # AI insight
        with st.expander("🧠 AI Cultural Analysis"):
            analysis = self.ai.generate_response(
                "Analyze current trends in Indian cultural tourism including: "
                "1. Emerging destinations "
                "2. Changing traveler preferences "
                "3. Impact on local communities "
                "4. Future predictions"
            )
            st.markdown(analysis)


    def trip_planner_page(self):
        st.title("🧳 Personalized Trip Planner")
        st.markdown("Get AI-powered recommendations for your Indian adventure")
        
        with st.form("trip_planner_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                interests = st.multiselect(
                    "Your Interests",
                    ["Heritage Sites", "Nature", "Food", "Adventure", "Spiritual", "Art & Culture"]
                )
                budget = st.selectbox(
                    "Budget Level",
                    ["Budget (₹500-₹2000/day)", "Mid-range (₹2000-₹5000/day)", "Luxury (₹5000+/day)"]
                )
            
            with col2:
                duration = st.slider("Trip Duration (days)", 3, 21, 7)
                travel_style = st.selectbox(
                    "Travel Style",
                    ["Solo", "Couple", "Family", "Group"]
                )
            
            if st.form_submit_button("Plan My Trip"):
                with st.spinner("Creating your personalized itinerary..."):
                    prompt = f"""
                    Create a {duration}-day trip plan for India based on:
                    - Interests: {', '.join(interests)}
                    - Budget: {budget}
                    - Travel style: {travel_style}
                    
                    Include:
                    1. Daily itinerary with activities
                    2. Recommended destinations
                    3. Estimated costs
                    4. Travel tips
                    5. Cultural etiquette notes
                    
                    Format with clear headings and emojis.
                    """
                    itinerary = self.ai.generate_response(prompt)
                    st.markdown(itinerary)
                    st.success("Here's your personalized trip plan!")

# --- Main App ---
def main():
    UIComponents.setup_page()
    UIComponents.create_navigation()
    
    app = AppPages()
    
    if st.session_state.page == "🏠 Home":
        app.home_page()
    elif st.session_state.page == "🗺️ Interactive Map":
        app.interactive_map_page()
    elif st.session_state.page == "🏛️ States":
        app.state_page()
    elif st.session_state.page == "🌟 Hidden Gems":
        app.hidden_gems_page()
    elif st.session_state.page == "📅 Festivals":
        app.festivals_page()
    elif st.session_state.page == "💬 AI Guide":
        app.chatbot_page()
    elif st.session_state.page == "📊 Insights":
        app.insights_page()
    elif st.session_state.page == "🧳 Trip Planner":
        app.trip_planner_page()

if __name__ == "__main__":
    main()
