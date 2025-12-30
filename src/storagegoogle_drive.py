"""
Хранилище Google Drive
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io

from .base import BaseStorage

logger = logging.getLogger(__name__)

class GoogleDriveStorage(BaseStorage):
    """Хранилище Google Drive"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def _initialize_client(self):
        """Инициализировать клиент Google Drive"""
        config = self.config['google_drive']
        
        if 'credentials_file' in config:
            # Использовать файл с учетными данными
            credentials_file = config['credentials_file']
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=self.SCOPES
            )
        elif 'credentials_json' in config:
            # Использовать JSON строку
            credentials_info = json.loads(config['credentials_json'])
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=self.SCOPES
            )
        else:
            raise ValueError("Не указаны учетные данные Google Drive")
        
        self.service = build('drive', 'v3', credentials=credentials)
        self.folder_id = config.get('folder_id')
        
        # Если folder_id не указан, создать или найти папку
        if not self.folder_id:
            self.folder_id = self._get_or_create_folder('CloudBackups')
    
    def _get_or_create_folder(self, folder_name: str) -> str:
        """Найти или создать папку в Google Drive"""
        try:
            # Поиск существующей папки
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            
            # Создание новой папки
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            return folder['id']
            
        except HttpError as error:
            logger.error(f"Ошибка при работе с Google Drive: {error}")
            raise
    
    def _upload_file(self, file_path: str, file_name: str, parent_id: Optional[str] = None) -> str:
        """Загрузить файл в Google Drive"""
        file_metadata = {
            'name': file_name,
            'parents': [parent_id] if parent_id else []
        }
        
        media = MediaFileUpload(
            file_path,
            mimetype='application/octet-stream',
            resumable=True
        )
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, size'
        ).execute()
        
        return file['id']
    
    def upload(self, file_path: str, backup_id: str, metadata: Optional[Dict] = None) -> str:
        """Загрузить файл в Google Drive"""
        try:
            # Загрузить основной файл
            file_name = f"{backup_id}.zip"
            file_id = self._upload_file(file_path, file_name, self.folder_id)
            
            # Загрузить метаданные
            if metadata:
                # Сохранить метаданные во временный файл
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(metadata, f)
                    metadata_file = f.name
                
                try:
                    metadata_name = f"{backup_id}.meta.json"
                    self._upload_file(metadata_file, metadata_name, self.folder_id)
                finally:
                    os.unlink(metadata_file)
            
            logger.info(f"Файл загружен в Google Drive: {file_id}")
            return file_id
            
        except HttpError as error:
            logger.error(f"Ошибка при загрузке в Google Drive: {error}")
            raise
    
    def _download_file(self, file_id: str, target_path: str) -> None:
        """Скачать файл из Google Drive"""
        request = self.service.files().get_media(fileId=file_id)
        
        with io.FileIO(target_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Скачано {int(status.progress() * 100)}%")
    
    def download(self, backup_id: str, target_path: str) -> bool:
        """Скачать файл из Google Drive"""
        try:
            # Найти файл по имени
            query = f"name='{backup_id}.zip' and '{self.folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            if not files:
                raise FileNotFoundError(f"Резервная копия не найдена: {backup_id}")
            
            file_id = files[0]['id']
            
            # Скачать файл
            self._download_file(file_id, target_path)
            
            # Попробовать скачать метаданные
            try:
                metadata_query = f"name='{backup_id}.meta.json' and '{self.folder_id}' in parents and trashed=false"
                metadata_results = self.service.files().list(
                    q=metadata_query,
                    spaces='drive',
                    fields='files(id)'
                ).execute()
                
                metadata_files = metadata_results.get('files', [])
                if metadata_files:
                    metadata_id = metadata_files[0]['id']
                    metadata_path = Path(target_path).with_suffix('.meta.json')
                    self._download_file(metadata_id, str(metadata_path))
            except:
                pass
            
            logger.info(f"Файл скачан из Google Drive: {backup_id}")
            return True
            
        except HttpError as error:
            logger.error(f"Ошибка при скачивании из Google Drive: {error}")
            raise
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Получить список резервных копий"""
        try:
            # Получить все файлы в папке
            query = f"'{self.folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, size, createdTime, modifiedTime)',
                pageSize=1000
            ).execute()
            
            backups = []
            for file in results.get('files', []):
                if file['name'].endswith('.zip') and not file['name'].endswith('.meta.json'):
                    backup_id = file['name'].replace('.zip', '')
                    
                    # Попробовать получить метаданные
                    metadata = None
                    try:
                        metadata_query = f"name='{backup_id}.meta.json' and '{self.folder_id}' in parents"
                        metadata_results = self.service.files().list(
                            q=metadata_query,
                            spaces='drive',
                            fields='files(id)'
                        ).execute()
                        
                        if metadata_results.get('files'):
                            metadata_file_id = metadata_results['files'][0]['id']
                            request = self.service.files().get_media(fileId=metadata_file_id)
                            metadata_content = io.BytesIO()
                            downloader = MediaIoBaseDownload(metadata_content, request)
                            done = False
                            while not done:
                                status, done = downloader.next_chunk()
                            
                            metadata = json.loads(metadata_content.getvalue().decode())
                    except:
                        pass
                    
                    backups.append({
                        'id': backup_id,
                        'file_id': file['id'],
                        'name': backup_id,
                        'size': int(file.get('size', 0)),
                        'created_at': file.get('createdTime', ''),
                        'modified_at': file.get('modifiedTime', ''),
                        'metadata': metadata
                    })
            
            return backups
            
        except HttpError as error:
            logger.error(f"Ошибка при получении списка файлов: {error}")
            raise
    
    def delete(self, backup_id: str) -> bool:
        """Удалить резервную копию"""
        try:
            # Найти и удалить основной файл
            query = f"name='{backup_id}.zip' and '{self.folder_id}' in parents"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)'
            ).execute()
            
            files = results.get('files', [])
            if files:
                self.service.files().delete(fileId=files[0]['id']).execute()
            
            # Найти и удалить метаданные
            metadata_query = f"name='{backup_id}.meta.json' and '{self.folder_id}' in parents"
            metadata_results = self.service.files().list(
                q=metadata_query,
                spaces='drive',
                fields='files(id)'
            ).execute()
            
            metadata_files = metadata_results.get('files', [])
            if metadata_files:
                self.service.files().delete(fileId=metadata_files[0]['id']).execute()
            
            logger.info(f"Резервная копия удалена из Google Drive: {backup_id}")
            return True
            
        except HttpError as error:
            logger.error(f"Ошибка при удалении файла: {error}")
            return False