import hashlib
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import random
from streamlit_lottie import st_lottie

# globals for testing
SECONDS = 10

# top/bottom padding
st.markdown(
    """
    <style>
        /* Reduce top padding */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# set up Spotify credentials and scope
scope = ("user-library-read user-read-playback-state user-read-currently-playing "
         "playlist-read-private user-modify-playback-state")

def authenticate_user():

    # ⚠️ Fallback to 'public' if user_id not yet fetched
    user_id = st.session_state.get("user_id", "public")

    # 🔐 Optional: Hash the user ID to obscure it in filenames
    hashed_id = hashlib.sha256(user_id.encode()).hexdigest()
    user_cache = f".cache-{hashed_id}"

    # 🎯 Create the auth manager with per-user cache file
    auth_manager = SpotifyOAuth(
        client_id=st.secrets['SPOTIPY_CLIENT_ID'],
        client_secret=st.secrets['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=st.secrets['SPOTIPY_REDIRECT_URI'],
        scope=scope,
        cache_path=user_cache,
        show_dialog=True
    )

    # 🧠 Try to load a cached token first
    token_info = auth_manager.get_cached_token()

    if not token_info:
        # 🔍 Check for auth code in URL query params
        code = st.query_params.get("code")

        if not code:
            # 🚪 No code or token = show login button
            auth_url = auth_manager.get_authorize_url()
            st.link_button("🎧 Login with Spotify", auth_url)
            st.stop()
        else:
            try:
                # 🔁 Exchange the code for a token
                auth_manager.get_access_token(code)
                st.query_params.clear()

                # 👤 Fetch and store the user ID in session_state
                user_profile = spotipy.Spotify(auth_manager=auth_manager).current_user()
                st.session_state.user_id = user_profile["id"]

                # 💾 Update user_cache with real user ID after auth
                hashed_id = hashlib.sha256(user_profile["id"].encode()).hexdigest()
                st.session_state.user_cache = f".cache-{hashed_id}"

            except Exception as e:
                st.error(f"🚫 Spotify token exchange failed: {e}")
                st.query_params.clear()
                st.stop()

    # 🎵 Return authenticated Spotify client
    try:
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        st.error(f"❌ Final Spotify auth failed: {e}")
        st.query_params.clear()
        st.stop()


st.markdown("<h1 style='text-align: center;'>🎵 Shotify 🎵</h1>", unsafe_allow_html=True)
sp = authenticate_user()  # this will force login

# initialize session state
if 'ph_running' not in st.session_state:
    st.session_state.ph_running = False
if 'ph_started' not in st.session_state:
    st.session_state.ph_started = False


# get user devices and playlists
def get_devices():
    return [(d["name"], d["id"]) for d in sp.devices()["devices"]]

def get_playlists():
    return [(p["name"], p["uri"]) for p in sp.current_user_playlists(limit=25)["items"]]

# load Lottie animation
def load_lottie_file(filepath):
    import json
    with open(filepath, "r") as f:
        return json.load(f)

def powerhour(chosen_uri, chosen_playlist, chosen_random, chosen_offset, chosen_device_id):
    playlist = sp.playlist(playlist_id=chosen_uri, additional_types=('track',))
    track_list = list(range(len(playlist['tracks']['items'])))

    # create placeholders for dynamic info display and progress bar
    info_placeholder = st.empty()
    progress_bar = st.progress(0)

    animation_key = 0 # to create unique animations with Lottie requires

    # shuffle track if random is checked
    if chosen_random:
        random.shuffle(track_list)

    # create 30s offset if offset is checked
    offset = 30000 if chosen_offset else 0
    last_idx = len(track_list) - 1

    # load beer animation
    beer_animation = load_lottie_file("assets/clinking-beer-mugs.json")

    # main loop through playlist, regardless of size
    for i, track_idx in enumerate(track_list):
        if not st.session_state.ph_running:
            st.warning("Powerhour stopped")
            return

        # set flag for last song in playlist
        is_last = (i == last_idx)

        # get the current track's title, name, and artist name
        track_info = playlist['tracks']['items'][track_idx]['track']
        track_name = track_info['name']
        artist_name = track_info['artists'][0]['name']


        # show track info and progress bar for current song
        display_track = (track_name[:37] + "...") if len(track_name) > 40 else track_name
        display_artist = (artist_name[:22] + "...") if len(artist_name) > 25 else artist_name

        # info panel for the progress/current song
        info_placeholder.markdown(
            f"{'[LAST TRACK] ' if is_last else ''}🎵 Now playing: **{display_track}** by **{display_artist}** ({i + 1}/{len(track_list)})"
        )

        # set progress bar to empty at the start of each track
        progress_bar.progress(0)

        # playback instructions to include device, chosen uri, and offset
        sp.start_playback(
            device_id=chosen_device_id,
            context_uri=chosen_uri,
            offset={"position": track_idx},
            position_ms=0 if is_last else offset
        )

        # animation shown once per track
        animation_container = st.empty()
        animation_key += 1

        # this makes the animation key unique for every track
        animation_key += 1

       # start animation outside of playback loop so only 1 instance shows up (avoids 1 showing every second)
        with animation_container:
            st_lottie(beer_animation, height=100, key=f"beer_animation_{animation_key}")

        # playback loop is the same until the last song
        if not is_last:
            for second in range(SECONDS):  # change to 60 for actual use
                if not st.session_state.ph_running:
                    st.warning("Powerhour stopped")
                    return

                # sleep for 1 second increments to catch any user/device side pauses
                time.sleep(1)
                playback = sp.current_playback()

                # stop animation after 5 seconds and then wait for the song to change
                if second > 4:
                    animation_container.empty()

                # update progress bar as track plays
                progress_bar.progress((second + 1) / SECONDS)  # fraction from 0 to 1

                # ff playback paused from device, wait until resumed
                if playback and not playback['is_playing']:
                    while not sp.current_playback()['is_playing']:
                        if not st.session_state.ph_running:
                            st.warning("Powerhour stopped")
                            return
                        time.sleep(0.1) # check rapidly for unpause

    # final celebratory message after last track
    info_placeholder.markdown(
        "<h5 style='text-align: center;'>🎉 Powerhour Complete! Great job! 🎉</h5>",
        unsafe_allow_html=True
    )

    # celebratory balloons
    st.balloons()

    # Pause to let users enjoy the moment
    time.sleep(15)

    # reset state and rerun
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

# setup and structure for play and stop buttons
col1, col2 = st.columns(2, gap="small")
with col1:
    if st.button(
            "Start Powerhour",
            disabled=st.session_state.ph_running or st.session_state.ph_started,
            key="start_btn",
            use_container_width=True
    ):
        st.session_state.ph_running = True
        st.session_state.ph_started = True
        st.rerun()

with col2:
    if st.button(
            "Stop Powerhour",
            disabled=not st.session_state.ph_running,
            key="stop_btn",
            use_container_width=True
    ):
        st.session_state.ph_running = False  #maybe move this inside if statement?
        st.warning("Stopping after current track...")
        st.rerun()

# run powerhour if started
if st.session_state.ph_started and st.session_state.ph_running:
    device_id = selected_device[1]
    playlist_name = selected_playlist[0]
    playlist_uri = selected_playlist[1]
    powerhour(playlist_uri, playlist_name, randomize, offset, device_id)


    #todo 5 - skip local songs if they aren't downloaded, currently locally available songs will play fine, but if the device doesn't have them the app kinda breaks
    #todo 6 - look into playing while phone is locked or browser isn't the active app.  the app might be running for an hour, so the screen might turn off
    #todo 7 - gracefully exit if the device becomes unavailable, like the user closed the spotify desktop app or something