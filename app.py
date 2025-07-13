import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import random

# Set up Spotify credentials and scope
scope = ("user-library-read user-read-playback-state user-read-currently-playing "
         "playlist-read-private user-modify-playback-state")

# try:
#     sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
#         client_id=st.secrets["SPOTIPY_CLIENT_ID"],
#         client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
#         redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],
#         scope=scope
#     ))
# except Exception as e:
#     st.error("❌ Spotify authentication failed. Check your credentials in Streamlit Secrets.")
#     st.exception(e)
#     st.stop()


st.title("🎵 Shotify 🎵")

st.write("✅ Cloud app rendered")
# Try loading secrets first
try:
    client_id = st.secrets["SPOTIPY_CLIENT_ID"]
    client_secret = st.secrets["SPOTIPY_CLIENT_SECRET"]
    redirect_uri = st.secrets["SPOTIPY_REDIRECT_URI"]
    st.success("✅ Secrets loaded")
except Exception as e:
    st.error("❌ Failed to load secrets.")
    st.exception(e)
    st.stop()

# Try setting up Spotipy
try:
    scope = (
        "user-library-read user-read-playback-state user-read-currently-playing "
        "playlist-read-private user-modify-playback-state"
    )
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope
    ))
    st.success("✅ Spotify client initialized")
except Exception as e:
    st.error("❌ Spotify OAuth failed")
    st.exception(e)
    st.stop()

# Get user devices and show as dropdown
def get_devices():
    device_items = sp.devices()["devices"]
    return [(d["name"], d["id"]) for d in device_items]

# Get user playlists and show as dropdown
def get_playlists():
    playlist_items = sp.current_user_playlists(limit=25)["items"]
    return [(p["name"], p["uri"]) for p in playlist_items]

def powerhour(chosen_uri, chosen_playlist, chosen_random, chosen_offset, chosen_device_id):
    playlist = sp.playlist(playlist_id=chosen_uri, additional_types=('track',))
    num_tracks = len(playlist['tracks']['items'])
    track_list = list(range(num_tracks))
    if chosen_random:
        random.shuffle(track_list)
    offset = 30000 if chosen_offset else 0
    last_song = track_list[-1]

    for i in track_list:
        if i != last_song:
            st.write(f"Playing track #{i + 1} of {num_tracks} from '{chosen_playlist}'")
            sp.start_playback(device_id=chosen_device_id, context_uri=chosen_uri, offset={"position": i}, position_ms=offset)
            for _ in range(60):
                time.sleep(1)
                playback = sp.current_playback()
                if playback and not playback['is_playing']:
                    while not sp.current_playback()['is_playing']:
                        time.sleep(0.1)
        else:
            st.write(f"[LAST TRACK] Playing #{i + 1} of {num_tracks} from '{chosen_playlist}'")
            sp.start_playback(context_uri=chosen_uri, offset={"position": i})

# UI Elements

devices_list = get_devices()
selected_device = st.selectbox("Select a device (if not shown, open Spotify on device and refresh):", devices_list, format_func=lambda x: x[0])

playlists_list = get_playlists()
selected_playlist = st.selectbox("Select a playlist:", playlists_list, format_func=lambda x: x[0])

randomize = st.checkbox("Shuffle track order?", value=False)
offset = st.checkbox("Start each track at 30 seconds?", value=False)

if st.button("Start Powerhour"):
    device_id = selected_device[1]
    playlist_name = selected_playlist[0]
    playlist_uri = selected_playlist[1]
    powerhour(playlist_uri, playlist_name, randomize, offset, device_id)

st.write("✅ App made it to the bottom.")