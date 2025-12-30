"""
Локальное хранилище (для тестирования)
"""
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .base import BaseStorage

logger = logging.getLogger(__name__)

class LocalStorage(BaseStorage):
    """Локальное хранилище (для тестирования)"""
    
    def _initialize_client(self):
        """Инициализировать локальное хранилище"""
        config = self.config.get('local', {})
        self.base_path = Path(config.get('path', 'backups'))
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Локальное хранилище инициализировано: {self.base_path}")
    
    def upload(self, file_path: str, backup_id: str, metadata: Optional[Dict] = None) -> str:
        """Копировать файл в локальное хранилище"""
        source_path = Path(file_path)
        target_path = self.base_path / f"{backup_id}{source_path.suffix}"
        
        # Копировать файл
        shutil.copy2(file_path, target_path)
        
        # Сохранить метаданные
        if metadata:
            metadata_path = target_path.with_suffix('.meta.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Файл сохранен локально: {target_path}")
        return str(target_path)
    
    def download(self, backup_id: str, target_path: str) -> bool:
        """Копировать файл из локального хранилища"""
        # Поиск файла
        for suffix in ['.zip', '.zip.enc']:
            source_path = self.base_path / f"{backup_id}{suffix}"
            if source_path.exists():
                shutil.copy2(source_path, target_path)
                
                # Попробовать скопировать метаданные
                metadata_path = source_path.with_suffix('.meta.json')
                if metadata_path.exists():
                    target_metadata = Path(target_path).with_suffix('.meta.json')
                    shutil.copy2(metadata_path, target_metadata)
                
                logger.info(f"Файл скопирован из локального хранилища: {source_path}")
                return True
        
        raise FileNotFoundError(f"Резервная копия не найдена: {backup_id}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Получить список резервных копий в локальном хранилище"""
        backups = []
        
        for file_path in self.base_path.glob('*'):
            # Пропустить метаданные
            if file_path.suffix == '.meta.json':
                continue
            
            # Проверить, что это резервная копия
            if file_path.suffix in ['.zip', '.enc']:
                backup_id = file_path.stem
                
                # Попробовать загрузить метаданные
                metadata = None
                metadata_path = file_path.with_suffix('.meta.json')
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                backups.append({
                    'id': backup_id,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'created_at': file_path.stat().st_ctime,
                    'metadata': metadata
                })
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def delete(self, backup_id: str) -> bool:
        """Удалить резервную копию из локального хранилища"""
        deleted = False
        
        # Удалить основной файл
        for suffix in ['.zip', '.zip.enc']:
            file_path = self.base_path / f"{backup_id}{suffix}"
            if file_path.exists():
                file_path.unlink()
                deleted = True
        
        # Удалить метаданные
        metadata_path = self.base_path / f"{backup_id}.meta.json"
        if metadata_path.exists():
            metadata_path.unlink()
        
        if deleted:
            logger.info(f"Резервная копия удалена из локального хранилища: {backup_id}")
        
        return deleted