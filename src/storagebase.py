"""
Базовый класс для облачных хранилищ
"""
import abc
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class BaseStorage(abc.ABC):
    """Абстрактный базовый класс для облачных хранилищ"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self._initialize_client()
    
    @abc.abstractmethod
    def _initialize_client(self):
        """Инициализировать клиент хранилища"""
        pass
    
    @abc.abstractmethod
    def upload(self, file_path: str, backup_id: str, metadata: Optional[Dict] = None) -> str:
        """
        Загрузить файл в хранилище
        
        Args:
            file_path: Локальный путь к файлу
            backup_id: Уникальный идентификатор резервной копии
            metadata: Метаданные резервной копии
        
        Returns:
            str: Путь к файлу в хранилище
        """
        pass
    
    @abc.abstractmethod
    def download(self, backup_id: str, target_path: str) -> bool:
        """
        Скачать файл из хранилища
        
        Args:
            backup_id: Идентификатор резервной копии
            target_path: Локальный путь для сохранения
        
        Returns:
            bool: True если успешно
        """
        pass
    
    @abc.abstractmethod
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Получить список резервных копий
        
        Returns:
            List[Dict]: Список резервных копий с метаданными
        """
        pass
    
    @abc.abstractmethod
    def delete(self, backup_id: str) -> bool:
        """
        Удалить резервную копию
        
        Args:
            backup_id: Идентификатор резервной копии
        
        Returns:
            bool: True если успешно
        """
        pass
    
    def test_connection(self) -> bool:
        """
        Проверить подключение к хранилищу
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            # Попробовать получить список копий
            self.list_backups()
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к хранилищу: {e}")
            return False
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о конкретной резервной копии
        
        Args:
            backup_id: Идентификатор резервной копии
        
        Returns:
            Optional[Dict]: Информация о резервной копии или None
        """
        backups = self.list_backups()
        for backup in backups:
            if backup.get('id') == backup_id:
                return backup
        return None