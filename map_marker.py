import requests
import json
import folium

def find_nearby_medical_places(latitude, longitude, radius):
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:{radius},{latitude},{longitude});
      way["amenity"="hospital"](around:{radius},{latitude},{longitude});
      relation["amenity"="hospital"](around:{radius},{latitude},{longitude});

      node["amenity"="clinic"](around:{radius},{latitude},{longitude});
      way["amenity"="clinic"](around:{radius},{latitude},{longitude});
      relation["amenity"="clinic"](around:{radius},{latitude},{longitude});
    );
    out center;
    """

    # Make the Overpass API request
    overpass_url = "http://overpass-api.de/api/interpreter"
    response = requests.get(overpass_url, params={'data': overpass_query})

    # Parse the JSON response
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error: Unable to fetch data. Status code: {response.status_code}")
        return None

def gen_map(latitude, longitude):
    result = find_nearby_medical_places(latitude, longitude, radius=1000)

    if result:
        # Create a folium map centered at the specified latitude and longitude
        map_center = [latitude, longitude]
        my_map = folium.Map(location=map_center, zoom_start=16)

        # Add markers for each medical place
        for item in result.get("elements", []):
            lat = item.get("lat")
            lon = item.get("lon")
            name = item.get("tags", {}).get("name", "Unknown")

            # Check if both lat and lon are present
            if lat is not None and lon is not None:
                # Create a popup for the marker
                popup = folium.Popup(f"Medical Place: {name}", parse_html=True)

                # Add the marker to the map
                folium.Marker([lat, lon], popup=popup).add_to(my_map)

        # Save the map to an HTML file
        map_filename = "static/medical_places_map.html"
        my_map.save(map_filename)

        # Return the filename as JSON
        