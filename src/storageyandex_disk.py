"""
Хранилище Yandex Disk
"""
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from urllib.parse import urljoin

from .base import BaseStorage

logger = logging.getLogger(__name__)

class YandexDiskStorage(BaseStorage):
    """Хранилище Yandex Disk"""
    
    BASE_URL = "https://cloud-api.yandex.net/v1/disk/"
    
    def _initialize_client(self):
        """Инициализировать клиент Yandex Disk"""
        self.token = self.config['yandex_disk']['token']
        self.folder = self.config['yandex_disk'].get('folder', '/Backups')
        self.headers = {
            'Authorization': f'OAuth {self.token}',
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Выполнить HTTP запрос к API Yandex Disk"""
        url = urljoin(self.BASE_URL, endpoint)
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response
    
    def _ensure_folder_exists(self, folder_path: str) -> bool:
        """Убедиться, что папка существует"""
        try:
            self._make_request('GET', f'resources?path={folder_path}')
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Папка не существует, создаем
                self._make_request('PUT', f'resources?path={folder_path}')
                return True
            raise
    
    def upload(self, file_path: str, backup_id: str, metadata: Optional[Dict] = None) -> str:
        """Загрузить файл на Yandex Disk"""
        # Убедиться, что папка существует
        self._ensure_folder_exists(self.folder)
        
        # Получить URL для загрузки
        remote_path = f"{self.folder}/{backup_id}"
        upload_response = self._make_request(
            'GET',
            f'resources/upload?path={remote_path}&overwrite=true'
        )
        upload_url = upload_response.json()['href']
        
        # Загрузить файл
        with open(file_path, 'rb') as f:
            upload_response = requests.put(upload_url, files={'file': f})
            upload_response.raise_for_status()
        
        # Сохранить метаданные
        if metadata:
            metadata_path = f"{remote_path}.meta.json"
            metadata_response = self._make_request(
                'GET',
                f'resources/upload?path={metadata_path}&overwrite=true'
            )
            metadata_url = metadata_response.json()['href']
            
            requests.put(metadata_url, data=json.dumps(metadata))
        
        logger.info(f"Файл загружен на Yandex Disk: {remote_path}")
        return remote_path
    
    def download(self, backup_id: str, target_path: str) -> bool:
        """Скачать файл с Yandex Disk"""
        remote_path = f"{self.folder}/{backup_id}"
        
        # Получить URL для скачивания
        download_response = self._make_request(
            'GET',
            f'resources/download?path={remote_path}'
        )
        download_url = download_response.json()['href']
        
        # Скачать файл
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Попробовать скачать метаданные
        try:
            metadata_path = f"{remote_path}.meta.json"
            metadata_response = self._make_request(
                'GET',
                f'resources/download?path={metadata_path}'
            )
            metadata_url = metadata_response.json()['href']
            
            metadata_response = requests.get(metadata_url)
            if metadata_response.status_code == 200:
                # Сохранить метаданные рядом с файлом
                metadata_file = Path(target_path).with_suffix('.meta.json')
                with open(metadata_file, 'w') as f:
                    json.dump(metadata_response.json(), f)
        except:
            pass
        
        logger.info(f"Файл скачан с Yandex Disk: {remote_path}")
        return True
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Получить список резервных копий"""
        try:
            response = self._make_request('GET', f'resources?path={self.folder}&limit=1000')
            items = response.json().get('_embedded', {}).get('items', [])
            
            backups = []
            for item in items:
                if item['type'] == 'file' and not item['name'].endswith('.meta.json'):
                    backup_id = item['name']
                    
                    # Попробовать получить метаданные
                    metadata = None
                    try:
                        metadata_path = f"{self.folder}/{backup_id}.meta.json"
                        metadata_response = self._make_request(
                            'GET',
                            f'resources?path={metadata_path}'
                        )
                        if metadata_response.status_code == 200:
                            metadata = metadata_response.json()
                    except:
                        pass
                    
                    backups.append({
                        'id': backup_id,
                        'name': backup_id,
                        'size': item.get('size', 0),
                        'created_at': item.get('created', ''),
                        'modified_at': item.get('modified', ''),
                        'path': item.get('path', ''),
                        'metadata': metadata
                    })
            
            return backups
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Папка не существует
                return []
            raise
    
    def delete(self, backup_id: str) -> bool:
        """Удалить резервную копию"""
        try:
            # Удалить основной файл
            file_path = f"{self.folder}/{backup_id}"
            self._make_request('DELETE', f'resources?path={file_path}&permanently=true')
            
            # Удалить метаданные
            metadata_path = f"{file_path}.meta.json"
            try:
                self._make_request('DELETE', f'resources?path={metadata_path}&permanently=true')
            except:
                pass
            
            logger.info(f"Резервная копия удалена: {backup_id}")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Резервная копия не найдена: {backup_id}")
                return False
            raise