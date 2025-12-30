"""
S3-совместимое хранилище (Yandex Object Storage, AWS S3, MinIO и т.д.)
"""
import boto3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from botocore.exceptions import ClientError

from .base import BaseStorage

logger = logging.getLogger(__name__)

class S3Storage(BaseStorage):
    """S3-совместимое хранилище"""
    
    def _initialize_client(self):
        """Инициализировать клиент S3"""
        config = self.config['s3']
        
        self.client = boto3.client(
            's3',
            endpoint_url=config.get('endpoint_url'),
            aws_access_key_id=config['access_key'],
            aws_secret_access_key=config['secret_key'],
            region_name=config.get('region', 'us-east-1')
        )
        
        self.bucket = config['bucket']
        self.prefix = config.get('prefix', 'backups/')
        
        # Убедиться, что бакет существует
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Убедиться, что бакет существует"""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"Бакет существует: {self.bucket}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Бакет не существует, создаем
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                    logger.info(f"Бакет создан: {self.bucket}")
                except ClientError as create_error:
                    raise Exception(f"Не удалось создать бакет: {create_error}")
            else:
                raise
    
    def upload(self, file_path: str, backup_id: str, metadata: Optional[Dict] = None) -> str:
        """Загрузить файл в S3 хранилище"""
        try:
            key = f"{self.prefix}{backup_id}.zip"
            
            # Загрузить основной файл
            self.client.upload_file(
                file_path,
                self.bucket,
                key,
                ExtraArgs={
                    'Metadata': {
                        'backup_id': backup_id,
                        'description': metadata.get('description', '') if metadata else ''
                    }
                }
            )
            
            # Загрузить метаданные
            if metadata:
                metadata_key = f"{self.prefix}{backup_id}.meta.json"
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=metadata_key,
                    Body=json.dumps(metadata),
                    ContentType='application/json'
                )
            
            logger.info(f"Файл загружен в S3: {key}")
            return key
            
        except ClientError as e:
            logger.error(f"Ошибка при загрузке в S3: {e}")
            raise
    
    def download(self, backup_id: str, target_path: str) -> bool:
        """Скачать файл из S3 хранилища"""
        try:
            key = f"{self.prefix}{backup_id}.zip"
            
            # Скачать основной файл
            self.client.download_file(self.bucket, key, target_path)
            
            # Попробовать скачать метаданные
            try:
                metadata_key = f"{self.prefix}{backup_id}.meta.json"
                metadata_path = Path(target_path).with_suffix('.meta.json')
                self.client.download_file(self.bucket, metadata_key, str(metadata_path))
            except:
                pass
            
            logger.info(f"Файл скачан из S3: {key}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"Резервная копия не найдена: {backup_id}")
            logger.error(f"Ошибка при скачивании из S3: {e}")
            raise
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Получить список резервных копий"""
        try:
            backups = []
            
            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    
                    # Пропустить метаданные
                    if key.endswith('.meta.json'):
                        continue
                    
                    # Извлечь backup_id из ключа
                    if key.endswith('.zip'):
                        backup_id = Path(key).stem
                        
                        # Попробовать получить метаданные
                        metadata = None
                        try:
                            metadata_key = f"{self.prefix}{backup_id}.meta.json"
                            metadata_obj = self.client.get_object(Bucket=self.bucket, Key=metadata_key)
                            metadata = json.loads(metadata_obj['Body'].read().decode())
                        except:
                            pass
                        
                        backups.append({
                            'id': backup_id,
                            'key': key,
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'metadata': metadata
                        })
            
            return backups
            
        except ClientError as e:
            logger.error(f"Ошибка при получении списка объектов: {e}")
            raise
    
    def delete(self, backup_id: str) -> bool:
        """Удалить резервную копию"""
        try:
            # Удалить основной файл
            file_key = f"{self.prefix}{backup_id}.zip"
            self.client.delete_object(Bucket=self.bucket, Key=file_key)
            
            # Удалить метаданные
            try:
                metadata_key = f"{self.prefix}{backup_id}.meta.json"
                self.client.delete_object(Bucket=self.bucket, Key=metadata_key)
            except:
                pass
            
            logger.info(f"Резервная копия удалена из S3: {backup_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Ошибка при удалении из S3: {e}")
            return False