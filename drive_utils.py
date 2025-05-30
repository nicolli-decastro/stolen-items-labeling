# drive_utils.py

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import pandas as pd
import io
import os

SCOPES = ['https://www.googleapis.com/auth/drive']

# Getting JSON file from Streamlit Secrets
import json
import streamlit as st
from google.oauth2 import service_account

creds_dict = json.loads(st.secrets["GDRIVE_KEY"])

# Set up credentials and drive service
credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# Root folder name (e.g., "LabelingAppData")
ROOT_FOLDER_NAME = 'LabelingAppData'

def get_folder_id_by_name(name, parent_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{name}'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = drive_service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
    folders = results.get('files', [])
    return folders[0]['id'] if folders else None


def list_date_folders():
    root_id = get_folder_id_by_name(ROOT_FOLDER_NAME)
    results = drive_service.files().list(
        q=f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder'",
        spaces='drive', fields="files(id, name)").execute()
    return sorted(results.get('files', []), key=lambda x: x['name'], reverse=True)


def download_csv(file_name, folder_id):
    query = f"name='{file_name}' and '{folder_id}' in parents"
    result = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = result.get('files', [])
    if not items:
        return pd.DataFrame()

    file_id = items[0]['id']
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh)


def upload_csv(df, file_name, folder_id):
    # Check if file exists
    query = f"name='{file_name}' and '{folder_id}' in parents"
    result = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = result.get('files', [])

    # Save locally first
    df.to_csv(file_name, index=False)

    media = MediaFileUpload(file_name, mimetype='text/csv', resumable=True)

    if items:
        file_id = items[0]['id']
        drive_service.files().update(fileId=file_id, media_body=media).execute()
    else:
        drive_service.files().create(
            body={'name': file_name, 'parents': [folder_id]},
            media_body=media
        ).execute()

    os.remove(file_name)  # Clean up local copy


def get_image_file_id(image_name, image_folder_id):
    query = f"name='{image_name}' and '{image_folder_id}' in parents"
    result = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = result.get('files', [])
    return items[0]['id'] if items else None
