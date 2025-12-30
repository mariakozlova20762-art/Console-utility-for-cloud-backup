"""
Основная логика резервного копирования
"""
import os
import shutil
import tempfile
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import zipfile
from concurrent.futures import ThreadPoolExecutor

from src.storage import get_storage
from src.encryption import Encryptor
from src.utils import format_size, format_duration, calculate_hash

logger = logging.getLogger(__name__)

class BackupManager:
    """Менеджер резервного копирования"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage = get_storage(config['storage'])
        self.encryptor = None
        
        if config.get('encryption', {}).get('enabled', False):
            self.encryptor = Encryptor(
                password=config['encryption']['password'],
                algorithm=config['encryption'].get('algorithm', 'AES-256-GCM')
            )
    
    def create_backup(self, source: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Создать резервную копию
        """
        start_time = time.time()
        source_path = Path(source)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Источник не найден: {source}")
        
        # Создание временного каталога
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Генерация имени файла резервной копии
            backup_id = self._generate_backup_id()
            backup_filename = f"{backup_id}.zip"
            
            logger.info(f"Создание резервной копии: {backup_id}")
            logger.info(f"Источник: {source_path}")
            logger.info(f"Описание: {description or 'Нет описания'}")
            
            # Сканирование файлов
            files_to_backup = self._scan_files(source_path)
            total_size = sum(f.stat().st_size for f in files_to_backup)
            
            logger.info(f"Найдено файлов: {len(files_to_backup)}")
            logger.info(f"Общий размер: {format_size(total_size)}")
            
            # Создание архива
            archive_path = temp_path / backup_filename
            self._create_archive(source_path, files_to_backup, archive_path)
            
            # Шифрование (если включено)
            if self.encryptor:
                logger.info("Шифрование архива...")
                encrypted_path = archive_path.with_suffix('.zip.enc')
                self.encryptor.encrypt_file(archive_path, encrypted_path)
                archive_path = encrypted_path
            
            # Загрузка в облачное хранилище
            logger.info(f"Загрузка в {self.storage.__class__.__name__}...")
            remote_path = self.storage.upload(
                str(archive_path),
                backup_id,
                metadata={
                    'description': description,
                    'source': str(source_path),
                    'file_count': len(files_to_backup),
                    'total_size': total_size,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            # Расчет статистики
            duration = time.time() - start_time
            archive_size = archive_path.stat().st_size
            
            result = {
                'success': True,
                'backup_id': backup_id,
                'source': str(source_path),
                'file_count': len(files_to_backup),
                'total_size': total_size,
                'size_human': format_size(total_size),
                'archive_size': archive_size,
                'archive_size_human': format_size(archive_size),
                'compression_ratio': round(archive_size / total_size * 100, 2) if total_size > 0 else 0,
                'duration': format_duration(duration),
                'storage_info': remote_path,
                'encrypted': self.encryptor is not None
            }
            
            logger.info(f"Резервная копия создана: {backup_id}")
            return result
    
    def restore_backup(self, backup_id: str, target: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Восстановить резервную копию
        """
        start_time = time.time()
        target_path = Path(target)
        
        if target_path.exists() and not overwrite:
            if any(target_path.iterdir()):
                raise FileExistsError(f"Целевая директория не пуста. Используйте --overwrite")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Скачивание из облачного хранилища
            logger.info(f"Скачивание резервной копии {backup_id}...")
            archive_path = temp_path / f"{backup_id}.zip"
            self.storage.download(backup_id, str(archive_path))
            
            # Дешифрование (если нужно)
            if archive_path.suffix == '.enc':
                if not self.encryptor:
                    raise ValueError("Резервная копия зашифрована, но шифрование не настроено")
                
                logger.info("Дешифрование архива...")
                decrypted_path = archive_path.with_suffix('')
                self.encryptor.decrypt_file(archive_path, decrypted_path)
                archive_path = decrypted_path
            
            # Восстановление файлов
            logger.info(f"Восстановление в {target_path}...")
            restored_files = self._extract_archive(archive_path, target_path)
            
            duration = time.time() - start_time
            
            result = {
                'success': True,
                'backup_id': backup_id,
                'target': str(target_path),
                'file_count': len(restored_files),
                'duration': format_duration(duration)
            }
            
            logger.info(f"Восстановление завершено: {backup_id}")
            return result
    
    def cleanup_old_backups(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Удалить старые резервные копии по политике хранения
        """
        retention = self.config.get('retention', {})
        backups = self.storage.list_backups()
        
        if not backups:
            return {'deleted_count': 0, 'freed_space': 0, 'to_delete': []}
        
        # Сортировка по дате (самые старые первыми)
        backups.sort(key=lambda x: x.get('created_at', ''))
        
        # Применение политики хранения
        to_keep = retention.get('keep_last', 30)
        to_delete = backups[:-to_keep] if len(backups) > to_keep else []
        
        if dry_run:
            return {
                'to_delete': to_delete,
                'total_backups': len(backups),
                'will_keep': len(backups) - len(to_delete)
            }
        
        # Удаление старых копий
        deleted_count = 0
        freed_space = 0
        
        for backup in to_delete:
            try:
                backup_id = backup['id']
                size = backup.get('size', 0)
                
                if self.storage.delete(backup_id):
                    deleted_count += 1
                    freed_space += size
                    logger.info(f"Удалена резервная копия: {backup_id}")
            except Exception as e:
                logger.error(f"Ошибка при удалении {backup.get('id')}: {e}")
        
        return {
            'deleted_count': deleted_count,
            'freed_space': freed_space,
            'freed_space_human': format_size(freed_space),
            'to_delete': to_delete
        }
    
    def _scan_files(self, source_path: Path) -> List[Path]:
        """
        Сканировать файлы для резервного копирования
        """
        exclude_patterns = self.config['backup'].get('exclude', [])
        files = []
        
        for item in source_path.rglob('*'):
            if item.is_file():
                # Проверка исключений
                if self._should_exclude(item, exclude_patterns):
                    continue
                files.append(item)
        
        return files
    
    def _should_exclude(self, file_path: Path, patterns: List[str]) -> bool:
        """
        Проверить, нужно ли исключить файл
        """
        from fnmatch import fnmatch
        
        for pattern in patterns:
            if fnmatch(str(file_path), pattern) or fnmatch(file_path.name, pattern):
                return True
        return False
    
    def _create_archive(self, source_path: Path, files: List[Path], archive_path: Path):
        """
        Создать ZIP архив
        """
        compression_level = self.config.get('compression', {}).get('level', 6)
        
        with zipfile.ZipFile(
            archive_path, 
            'w', 
            zipfile.ZIP_DEFLATED, 
            compresslevel=compression_level
        ) as zipf:
            
            for file in files:
                # Сохраняем относительный путь
                rel_path = file.relative_to(source_path)
                zipf.write(file, rel_path)
                logger.debug(f"Добавлен в архив: {rel_path}")
    
    def _extract_archive(self, archive_path: Path, target_path: Path) -> List[Path]:
        """
        Извлечь файлы из архива
        """
        target_path.mkdir(parents=True, exist_ok=True)
        extracted_files = []
        
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            for member in zipf.namelist():
                # Извлекаем файл
                extracted_path = zipf.extract(member, target_path)
                extracted_files.append(Path(extracted_path))
                logger.debug(f"Извлечен: {member}")
        
        return extracted_files
    
    def _generate_backup_id(self) -> str:
        """
        Сгенерировать уникальный ID для резервной копии
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        name = self.config['backup'].get('name', 'backup')
        return f"{name}_{timestamp}"