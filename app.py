import streamlit as st
import pydeck as pdk
import geopandas as gpd
import numpy as np
import pandas as pd
import os
import time

# Function to format city names properly
def format_city_name(filename):
    """Convert file names to readable city names."""
    base_name = filename.replace("_clean.geojson", "").replace("_", " ")
    
    # Correct known city names
    city_name_corrections = {
        "sg": "Singapore",
        "nyc": "New York City",
        "par": "Paris",
    }
    return city_name_corrections.get(base_name.lower(), base_name.title())

# Function to load all available city data dynamically
def load_city_data():
    """Automatically detects available city files and loads them into a dictionary."""
    city_files = [f for f in os.listdir() if f.endswith("_clean.geojson")]
    city_data = {}

    for file in city_files:
        city_name = format_city_name(file)  # Get properly formatted city name

        gdf = gpd.read_file(file)
        gdf["start_date"] = pd.to_numeric(gdf["start_date"], errors="coerce")

        # Normalize elevation
        min_year, max_year = 1850, 2025
        gdf["elevation"] = ((gdf["start_date"] - min_year) / (max_year - min_year)) * 100

        # Assign color gradient
        def assign_color(year):
            if np.isnan(year):
                return [200, 200, 200]  # Gray for missing values
            normalized = (year - min_year) / (max_year - min_year)
            return [0, 0, int(255 * (1 - normalized))]  # Dark blue for old, light blue for new

        gdf["color"] = gdf["start_date"].apply(assign_color)
        gdf["lat"] = gdf.geometry.centroid.y
        gdf["lon"] = gdf.geometry.centroid.x

        # Estimate city center for proper map positioning
        city_lat, city_lon = gdf["lat"].mean(), gdf["lon"].mean()
        city_data[city_name] = (gdf, city_lat, city_lon)

    return city_data

# Load all available cities
city_options = load_city_data()

# Streamlit Sidebar UI
st.sidebar.markdown("## 🏙 Urban Growth Visualization")
st.sidebar.markdown("Explore the evolution of buildings over time.")
st.sidebar.markdown("---")

# Dynamic City Selection (Dropdown)
st.sidebar.markdown("#### 🌍 Select City")
selected_city = st.sidebar.selectbox("", list(city_options.keys()))
st.sidebar.markdown("---")

# Get selected city's data and coordinates
city_data, city_lat, city_lon = city_options[selected_city]

# Map Style Selector
st.sidebar.markdown("#### 🗺 Map Style")
map_styles = {
    "Light": "mapbox://styles/mapbox/light-v10",
    "Dark": "mapbox://styles/mapbox/dark-v10",
    "Satellite": "mapbox://styles/mapbox/satellite-v9",
    "Outdoors": "mapbox://styles/mapbox/outdoors-v11",
}
selected_style = st.sidebar.radio("", list(map_styles.keys()), horizontal=True)
st.sidebar.markdown("---")

# Animation Speed
st.sidebar.markdown("#### ⏳ Animation Speed")
speed_dict = {"Slow": 0.7, "Normal": 0.3, "Fast": 0.1}
selected_speed = st.sidebar.radio("", ["Slow", "Normal", "Fast"], horizontal=True)
st.sidebar.markdown("---")

# Initialize session state for animation
if "year" not in st.session_state:
    st.session_state.year = 1850  # Start year

if "animation_running" not in st.session_state:
    st.session_state.animation_running = False  # Track animation state

# Year Selection (Now fully interactive!)
st.sidebar.markdown("#### 📅 Construction Year")
selected_year = st.sidebar.slider(
    "", 1850, 2025, st.session_state.year, key="year_slider"
)
st.sidebar.markdown("---")

# Update year state only if animation is not running
if not st.session_state.animation_running:
    st.session_state.year = selected_year

# Toggle Heatmap
show_heatmap = st.sidebar.checkbox("🔥 Heatmap", True)
st.sidebar.markdown("---")

# Create empty containers for dynamic updates
year_display = st.empty()
map_container = st.empty()

# Function to update map dynamically
def update_map():
    filtered_data = city_data[city_data["start_date"].notna() & (city_data["start_date"] <= st.session_state.year)]

    # Update year display
    year_display.subheader(f"Construction Year: {st.session_state.year}")

    # Create Pydeck Layers
    city_layer = pdk.Layer(
        "GeoJsonLayer",
        filtered_data,
        get_fill_color="color",
        extruded=True,
        get_elevation="elevation",
        pickable=True,
        opacity=0.7,
    )

    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        filtered_data,
        get_position=["lon", "lat"],
        get_weight="start_date",
        radius_pixels=40,
        opacity=0.4,
        intensity=1,
        threshold=0.3,
        color_range=[
            [0, 0, 255, 100],   # Blue (low density)
            [0, 255, 255, 150], # Cyan
            [0, 255, 0, 200],   # Green
            [255, 255, 0, 200], # Yellow
            [255, 0, 0, 255],   # Red (high density)
        ],
    ) if show_heatmap else None

    # Define View State
    view = pdk.ViewState(latitude=city_lat, longitude=city_lon, zoom=11, pitch=45)

    # Tooltip
    tooltip = {"html": "Construction Year: {start_date}", "style": {"backgroundColor": "black", "color": "white"}}

    # Render Map
    layers = [city_layer]
    if show_heatmap:
        layers.append(heatmap_layer)

    map_container.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_style=map_styles[selected_style], tooltip=tooltip))

# Play Animation Button (Automatically updates the map)
if st.sidebar.button("▶ Play Animation"):
    st.session_state.animation_running = True  # Start animation flag
    for year in range(st.session_state.year, 2026, 5):
        if not st.session_state.animation_running:
            break  # Stop animation if user clicks "Stop"
        st.session_state.year = year  # Update year dynamically
        update_map()  # Refresh the map dynamically
        time.sleep(speed_dict[selected_speed])  # Delay for smooth animation
    st.session_state.animation_running = False  # Stop animation properly

# Stop Animation Button
if st.sidebar.button("⏹ Stop Animation"):
    st.session_state.animation_running = False

# Always update map
update_map()
