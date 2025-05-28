import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime

# --- CONFIG ---
DATASET_PATH = "Abilene_tx_500mi.csv"
IMAGE_FOLDER = "Abilene_tx_500mi_files"
LABEL_FILE = "labels.csv"
USER_FILE = "users.csv"
BATCH_SIZE = 30

# --- Load Users ---
def load_users():
    if not os.path.isfile(USER_FILE):
        return {}
    df = pd.read_csv(USER_FILE)
    return dict(zip(df.username, df.password))

# --- Register User ---
def register_user(username, password):
    if os.path.isfile(USER_FILE):
        df = pd.read_csv(USER_FILE)
        if username in df.username.values:
            return False
        df = pd.concat([df, pd.DataFrame([[username, password]], columns=['username', 'password'])])
    else:
        df = pd.DataFrame([[username, password]], columns=['username', 'password'])
    df.to_csv(USER_FILE, index=False)
    return True

# --- Load Data ---
@st.cache_data
def load_data():
    return pd.read_csv(DATASET_PATH)

# --- Save Label ---
def save_label(data):
    file_exists = os.path.isfile(LABEL_FILE)
    df = pd.DataFrame([data])
    df.to_csv(LABEL_FILE, mode='a', header=not file_exists, index=False)

# --- Load Label History ---
def get_user_progress(username):
    if not os.path.isfile(LABEL_FILE):
        return pd.DataFrame(), 0, 0
    df = pd.read_csv(LABEL_FILE)
    user_labels = df[df['username'] == username]
    batches = user_labels.shape[0] // BATCH_SIZE
    current_batch = user_labels.shape[0] % BATCH_SIZE
    return user_labels, batches, current_batch

# --- Streamlit UI ---
st.set_page_config(page_title="Stolen Item Labeling", layout="centered")

if "user" not in st.session_state:
    st.title("🔐 Retailer Portal")
    mode = st.radio("Choose an option:", ["Login", "Register"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Login":
        if st.button("Login"):
            users = load_users()
            if username in users and users[username] == password:
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        if st.button("Register"):
            success = register_user(username, password)
            if success:
                st.success("Account created! You can now log in.")
            else:
                st.error("Username already exists.")

else:
    st.title("🔍 Item Labeling App")
    st.markdown(f"Welcome, **{st.session_state.user}**")

    df = load_data()
    labeled_df, completed_batches, current_batch_size = get_user_progress(st.session_state.user)

    st.write(f"Progress: {current_batch_size}/30 in current batch")
    st.write(f"Completed batches: {completed_batches}")

    remaining = df[~df['photo_url'].isin(labeled_df['photo_url'])]
    if current_batch_size >= BATCH_SIZE:
        if st.button("✅ Label more images (start new batch)"):
            current_batch_size = 0
    if current_batch_size < BATCH_SIZE:
        sample = remaining.sample(1).iloc[0]
        image_path = os.path.join(IMAGE_FOLDER, os.path.basename(sample['photo_url']))

        if os.path.exists(image_path):
            st.image(image_path, use_column_width=True)
        else:
            st.warning(f"Image not found: {image_path}")

        st.markdown(f"**Title:** {sample['title']}")
        st.markdown(f"**Price:** {sample['price']}")
        st.markdown(f"**Location:** {sample['location']}")
        st.markdown(f"**[View Listing]({sample['listing_url']})**")

        score = st.slider("Suspicion Level (1 = Not suspicious, 5 = Definitely stolen)", 1, 5, 3)
        binary_flag = st.radio("Is this item likely stolen?", ["Yes", "No"])

        if st.button("Submit Label"):
            label = {
                "listing_url": sample['listing_url'],
                "photo_url": sample['photo_url'],
                "price": sample['price'],
                "title": sample['title'],
                "location": sample['location'],
                "origin_city_list": sample['origin_city_list'],
                "username": st.session_state.user,
                "image_file": os.path.basename(sample['photo_url']),
                "score_1_5": score,
                "binary_flag": binary_flag,
                "timestamp": datetime.now().isoformat()
            }
            save_label(label)
            st.success("Label submitted!")
            st.rerun()

    st.markdown("---")
    if st.button("🔓 Logout"):
        del st.session_state.user
        st.rerun()
