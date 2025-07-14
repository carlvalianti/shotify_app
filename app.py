import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import random

# Set up Spotify credentials and scope
scope = ("user-library-read user-read-playback-state user-read-currently-playing "
         "playlist-read-private user-modify-playback-state")

def authenticate_user():

    # Create the auth manager with a cache file for public use
    auth_manager = SpotifyOAuth(
        client_id=st.secrets['SPOTIPY_CLIENT_ID'],
        client_secret=st.secrets['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=st.secrets['SPOTIPY_REDIRECT_URI'],
        scope=scope,
        cache_path=".cache-public",
        show_dialog=True
    )

    # Check for cached token first
    token_info = auth_manager.get_cached_token()

    # If no cached token, check for code in query params
    if not token_info:
        code = st.query_params.get("code")

        if not code:
            # No token and no code = show login button
            auth_url = auth_manager.get_authorize_url()
            st.link_button("🎧 Login with Spotify", auth_url)
            st.stop()
        else:
            try:
                # Exchange the code for a token (let Spotipy manage format)
                auth_manager.get_access_token(code)
                st.query_params.clear()  # Clear URL params once used
            except Exception as e:
                st.error(f"🚫 Spotify token exchange failed: {e}")
                st.query_params.clear()
                st.stop()

    # Try using the token (either from cache or fresh)
    try:
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        st.error(f"❌ Final Spotify auth failed: {e}")
        st.query_params.clear()
        st.stop()


st.title("🎵 Shotify 🎵")
sp = authenticate_user()  # This will force login

# Initialize session state
if 'ph_running' not in st.session_state:
    st.session_state.ph_running = False
if 'ph_started' not in st.session_state:
    st.session_state.ph_started = False


# Get user devices and playlists
def get_devices():
    return [(d["name"], d["id"]) for d in sp.devices()["devices"]]


def get_playlists():
    return [(p["name"], p["uri"]) for p in sp.current_user_playlists(limit=25)["items"]]


def powerhour(chosen_uri, chosen_playlist, chosen_random, chosen_offset, chosen_device_id):
    playlist = sp.playlist(playlist_id=chosen_uri, additional_types=('track',))
    track_list = list(range(len(playlist['tracks']['items'])))
    if chosen_random:
        random.shuffle(track_list)

    offset = 30000 if chosen_offset else 0
    last_idx = len(track_list) - 1

    for i, track_idx in enumerate(track_list):
        if not st.session_state.ph_running:
            st.warning("Powerhour stopped")
            return

        is_last = (i == last_idx)
        st.write(
            f"{'[LAST TRACK] ' if is_last else ''}Playing track #{i + 1} of {len(track_list)} from '{chosen_playlist}'")

        sp.start_playback(
            device_id=chosen_device_id,
            context_uri=chosen_uri,
            offset={"position": track_idx},
            position_ms=0 if is_last else offset
        )

        if not is_last:
            for _ in range(10):
                if not st.session_state.ph_running:
                    st.warning("Powerhour stopped")
                    return

                time.sleep(1)
                playback = sp.current_playback()
                if playback and not playback['is_playing']:
                    while not sp.current_playback()['is_playing']:
                        if not st.session_state.ph_running:
                            st.warning("Powerhour stopped")
                            return
                        time.sleep(0.1)

    st.session_state.ph_running = False
    st.session_state.ph_started = False
    st.rerun()


# UI Elements
devices_list = get_devices()
selected_device = st.selectbox(
    "Select a device (if not shown, open Spotify on device and refresh):",
    devices_list,
    format_func=lambda x: x[0]
)

playlists_list = get_playlists()
selected_playlist = st.selectbox(
    "Select a playlist:",
    playlists_list,
    format_func=lambda x: x[0]
)

randomize = st.checkbox("Shuffle track order?", value=False)
offset = st.checkbox("Start each track at 30 seconds?", value=False)

col1, col2 = st.columns(2)
with col1:
    if st.button(
            "Start Powerhour",
            disabled=st.session_state.ph_running or st.session_state.ph_started,
            key="start_btn"
    ):
        st.session_state.ph_running = True
        st.session_state.ph_started = True
        st.rerun()

with col2:
    if st.button(
            "Stop Powerhour",
            disabled=not st.session_state.ph_running,
            key="stop_btn"
    ):
        st.session_state.ph_running = False  #maybe move this inside if statement?
        st.warning("Stopping after current track...")
        st.rerun()

# Run powerhour if started
if st.session_state.ph_started and st.session_state.ph_running:
    device_id = selected_device[1]
    playlist_name = selected_playlist[0]
    playlist_uri = selected_playlist[1]
    powerhour(playlist_uri, playlist_name, randomize, offset, device_id)