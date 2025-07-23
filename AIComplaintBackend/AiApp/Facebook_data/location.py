import streamlit as st
import requests
from urllib.parse import quote
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Location Finder", layout="centered")

st.title("📍 Location Finder from Text")

text_input = st.text_area(
    "Enter text that contains a location:",
    "There is a traffic jam near MG Marg, Gangtok.",
)

if st.button("Find Location"):

    if not text_input.strip():
        st.warning("Please enter some text.")
    else:
        st.info("Extracting location...")

        # Use Nominatim Geocoding
        url = f"https://nominatim.openstreetmap.org/search/{quote(text_input)}?format=json&limit=1"

        headers = {"User-Agent": "LocationFinderApp/1.0 (your_email@example.com)"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if data:
                place = data[0]
                lat = float(place["lat"])
                lon = float(place["lon"])
                display_name = place["display_name"]

                st.success(f"📍 Location Found: {display_name}")

                # Display map
                m = folium.Map(location=[lat, lon], zoom_start=15)
                folium.Marker([lat, lon], popup=display_name).add_to(m)

                st_folium(m, width=700, height=500)

            else:
                st.error("⚠️ No location found in the text.")
        else:
            st.error("Error contacting Nominatim API.")
