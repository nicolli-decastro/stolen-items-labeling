# app.py

import streamlit as st
import pandas as pd
from datetime import datetime
import drive_utils as du

# Set up page
st.set_page_config(page_title="Stolen Items Labeling App", layout="centered")

# --- Globals ---
ROOT_FOLDER_NAME = 'LabelingAppData'
LABELS_CSV = 'labels.csv'
USERS_CSV = 'users.csv'
COMPANIES_CSV = 'companies.csv'

# --- Select latest dataset folder ---
date_folders = du.list_date_folders()
latest_folder = date_folders[0] if date_folders else None
if latest_folder:
    date_folder_id = latest_folder['id']
    dataset_csv = du.download_csv("Abilene_tx_500mi.csv", date_folder_id)
    image_folder_id = du.get_folder_id_by_name("Abilene_tx_500mi_files", parent_id=date_folder_id)
else:
    st.error("No dataset folders found in Drive")
    st.stop()

# --- Load config files ---
users_df = du.download_csv(USERS_CSV, du.get_folder_id_by_name(ROOT_FOLDER_NAME))
companies_df = du.download_csv(COMPANIES_CSV, du.get_folder_id_by_name(ROOT_FOLDER_NAME))
labels_df = du.download_csv(LABELS_CSV, du.get_folder_id_by_name(ROOT_FOLDER_NAME))
company_list = companies_df['company'].dropna().unique().tolist() if not companies_df.empty else []


# --- Login/Register ---
if "user_email" not in st.session_state:
    st.title("🔐 Retailer Access Portal")
    mode = st.radio("Choose an option:", ["Login", "Register"])

    if mode == "Register":
        with st.form("register_form"):
            st.subheader("Register")
            first = st.text_input("First Name")
            last = st.text_input("Last Name")
            email = st.text_input("Email")
            company = st.selectbox("Select Your Company", company_list)
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Register")

            if submit:
                if email in users_df['email'].values:
                    st.warning("Email already registered.")
                else:
                    new_user = pd.DataFrame([[first, last, email, company, password]],
                                             columns=['first_name','last_name','email','company','password'])
                    users_df = pd.concat([users_df, new_user], ignore_index=True)
                    du.upload_csv(users_df, USERS_CSV, du.get_folder_id_by_name(ROOT_FOLDER_NAME))
                    st.success("Account created! Please login.")
                    st.rerun()

    else:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            match = users_df[(users_df['email'] == email) & (users_df['password'] == password)]
            if not match.empty:
                st.session_state.user_email = email
                st.session_state.user_company = match.iloc[0]['company']
                st.rerun()
            else:
                st.error("Invalid credentials")

else:
    st.title("📸 Label Marketplace Listings")
    st.write(f"Logged in as: **{st.session_state.user_email}** from **{st.session_state.user_company}**")

    user_labels = labels_df[labels_df['email'] == st.session_state.user_email] if not labels_df.empty else pd.DataFrame()
    batch_count = user_labels.shape[0] // 30
    current_batch = user_labels.shape[0] % 30
    st.write(f"Progress: {current_batch}/30 in current batch")
    st.write(f"Completed batches: {batch_count}")

    remaining = dataset_csv[~dataset_csv['photo_url'].isin(user_labels['photo_url'] if not user_labels.empty else [])]
    if current_batch >= 30:
        if st.button("✅ Start new batch"):
            current_batch = 0
            st.rerun()

    if current_batch < 30 and not remaining.empty:
        row = remaining.sample(1).iloc[0]
        image_name = row['photo_url'].split('/')[-1]
        file_id = du.get_image_file_id(image_name, image_folder_id)
        if file_id:
            image_url = f"https://drive.google.com/uc?export=view&id={file_id}"
            st.image(image_url, use_column_width=True)

        st.markdown(f"**Title:** {row['title']}")
        st.markdown(f"**Price:** {row['price']}")
        st.markdown(f"**Location:** {row['location']}")
        st.markdown(f"**[View Listing]({row['listing_url']})**")

        score = st.slider("Suspicion Score (1 = Not suspicious, 5 = Definitely stolen)", 1, 5, 3)
        binary_flag = st.radio("Is this item likely stolen?", ["Yes", "No"])

        if st.button("Submit Label"):
            new_label = pd.DataFrame([[row['listing_url'], row['photo_url'], row['price'], row['title'], row['location'],
                                       row['origin_city_list'], st.session_state.user_email,
                                       st.session_state.user_company, image_name, score, binary_flag, datetime.now().isoformat()]],
                                     columns=labels_df.columns)
            labels_df = pd.concat([labels_df, new_label], ignore_index=True)
            du.upload_csv(labels_df, LABELS_CSV, du.get_folder_id_by_name(ROOT_FOLDER_NAME))
            st.success("Label submitted!")
            st.rerun()

    st.divider()
    if st.button("🔒 Logout"):
        del st.session_state.user_email
        del st.session_state.user_company
        st.rerun()

# --- Manager portal ---
if st.sidebar.checkbox("Manager Portal"):
    st.sidebar.title("🛠 Manager Tools")

    if users_df.empty:
        st.sidebar.info("No users registered yet.")
    else:
        st.sidebar.subheader("Registered Users")
        st.sidebar.dataframe(users_df[['first_name','last_name','email','company']])

    st.sidebar.subheader("Manage Companies")
    new_company = st.sidebar.text_input("Add New Company")
    if st.sidebar.button("Add Company"):
        if new_company not in company_list:
            companies_df = pd.concat([companies_df, pd.DataFrame([[new_company]], columns=['company'])], ignore_index=True)
            du.upload_csv(companies_df, COMPANIES_CSV, du.get_folder_id_by_name(ROOT_FOLDER_NAME))
            st.sidebar.success(f"Added {new_company}")
        else:
            st.sidebar.warning("Company already exists")
