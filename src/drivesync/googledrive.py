import io
import pathlib
from typing import Self, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from .common import Common

MIMETYPE_FOLDER = 'application/vnd.google-apps.folder'

class GDrive:
    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self, service_account_file):
        credentials = service_account.Credentials.from_service_account_file(service_account_file, scopes=GDrive.SCOPES)
        self.drive_service = build('drive', 'v3', credentials=credentials)

    def create_folder(self, folder_name, parent_folder_id=None):
        folder_metadata = {
            'name': folder_name,
            'mimeType': "application/vnd.google-apps.folder",
            'parents': [parent_folder_id] if parent_folder_id else []
        }

        created_folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = created_folder["id"]
        return folder_id
    
    def grant_user_permissions(self, file_id, user_email):
        permission = { 'type': 'user', 'role': 'writer', 'emailAddress': user_email }
        self.drive_service.permissions().create(fileId=file_id, body=permission, sendNotificationEmail=False).execute()

    def list_folder(self, parent_folder_id=None):
        results = self.drive_service.files().list(
            q=f"'{parent_folder_id}' in parents and trashed=false" if parent_folder_id else None,
            pageSize=1000,
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        items = results.get('files', [])
        return [] if not items else items

    def delete_files(self, file_or_folder_id):
        try:
            self.drive_service.files().delete(fileId=file_or_folder_id).execute()
        except Exception as e:
            print(f"Error deleting file/folder with ID: {file_or_folder_id}: {str(e)}")

    def download_file(self, file_id, destination_path):
        request = self.drive_service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination_path, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()

    def upload_file(self, folder_id, file_name, local_file_path):
        try:
            file_metadata = { "name": file_name, "parents": [folder_id] }
            media = MediaFileUpload(local_file_path)
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()
            return file["id"]
        except HttpError as error:
            print(f"An error occurred while uploading {file_name}: {error}")
            return None
    
    def upload_existing_file(self, file_id, local_file_path):
        try:
            media = MediaFileUpload(local_file_path)
            # createMethod.<locals>.method() takes 1 positional argument but 2 were given ???
            self.drive_service.files().update(
                file_id,
                media_body=media,
                fields="id"
            ).execute()
        except HttpError as error:
            print(f"An error occurred while uploading {file_id}: {error}")

class GDriveFile:
    def __init__(self, gdrive, name, id, parent, is_directory=True):
        self.gdrive = gdrive
        self.name = name
        self.id = id
        self.parent = parent
        self.is_directory = is_directory
        self.children = None

    @staticmethod
    def get_root(gdrive):
        return GDriveFile(gdrive, None, None, None, True)

    def get_path(self):
        return "/" if not self.parent else f"{self.parent.get_path()}{self.name}{"" if not self.is_directory else "/"}"

    def get_child(self, child_name):
        self.explore_self()
        for f in self.children:
            if f.name == child_name:
                return f
        return None
    
    def get_deep(self, path, mkdir_if_missing=False) -> Tuple[Self, Self]:
        parent, file = None, self
        parts = pathlib.Path(path).parts
        for part in parts[:-1]:
            file, parent = file.get_child(part), file
            if file is None:
                if mkdir_if_missing:
                    file = parent.mkdir(part)
                else:
                    return (None, None)
        file, parent = file.get_child(parts[-1]), file
        return (parent, file)
    
    def get_children(self):
        self.explore_self()
        return self.children
    
    def mkdir(self, child_name):
        child = self.get_child(child_name)
        if child is None:
            folder_id = self.gdrive.create_folder(child_name, self.id)
            child = GDriveFile(self.gdrive, child_name, folder_id, self, True)
            self.children.append(child)
        if not child.is_directory:
            raise Exception(child.get_path() + " is not a directory")
        return child
    
    def explore_self(self):
        if self.children is not None:
            return
        if not self.is_directory:
            raise Exception(f"{self.get_path()} is not a directory")
        self.children = [
            GDriveFile(self.gdrive, f['name'], f['id'], self, f['mimeType'] == MIMETYPE_FOLDER)
            for f in self.gdrive.list_folder(self.id)
        ]
        print(f"Explored {self.get_path()}, got {[f.name for f in self.children]}")

    def remove(self):
        self.gdrive.delete_files(self.id)
        if self.parent is not None:
            self.parent.children = [f for f in self.parent.children if f != self]

    def upload_file(self, file_name, local_file):
        if not self.is_directory:
            raise Exception(f"{self.get_path()} is not a directory")
        existing = self.get_child(file_name)
        if existing is not None:
            existing.remove()
            #self.gdrive.upload_existing_file(existing.id, local_file)
            #return
        file_id = self.gdrive.upload_file(self.id, file_name, local_file)
        if file_id is not None and self.children is not None:
            self.children.append(GDriveFile(self.gdrive, file_name, file_id, self, False))
    
    def download(self) -> pathlib.Path:
        temp_file = Common.get_temp_file("txt")
        self.gdrive.download_file(self.id, temp_file)
        return temp_file
