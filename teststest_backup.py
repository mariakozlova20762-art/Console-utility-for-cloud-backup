"""
Тесты для модуля резервного копирования
"""
import pytest
from pathlib import Path
import tempfile
import zipfile
import json
from datetime import datetime

from src.backup import BackupManager
from src.config import get_default_config

@pytest.fixture
def test_backup_manager():
    """Фикстура для BackupManager с локальным хранилищем"""
    config = get_default_config()
    config['storage'] = {
        'type': 'local',
        'local': {
            'path': './test-backups'
        }
    }
    
    manager = BackupManager(config)
    yield manager
    
    # Очистка после теста
    backup_dir = Path('./test-backups')
    if backup_dir.exists():
        import shutil
        shutil.rmtree(backup_dir)

@pytest.fixture
def test_data_structure():
    """Фикстура для тестовой структуры данных"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Создаем тестовую структуру
        (temp_path / 'file1.txt').write_text('Content 1')
        (temp_path / 'file2.txt').write_text('Content 2')
        
        subdir = temp_path / 'subdir'
        subdir.mkdir()
        (subdir / 'file3.txt').write_text('Content 3')
        
        yield temp_path

class TestBackupManager:
    """Тесты BackupManager"""
    
    def test_initialization(self, test_backup_manager):
        """Тест инициализации BackupManager"""
        assert test_backup_manager.config is not None
        assert test_backup_manager.storage is not None
        assert test_backup_manager.encryptor is None
    
    def test_generate_backup_id(self, test_backup_manager):
        """Тест генерации ID резервной копии"""
        backup_id = test_backup_manager._generate_backup_id()
        assert backup_id.startswith('default-backup_')
        assert len(backup_id) > 20
    
    def test_scan_files(self, test_backup_manager, test_data_structure):
        """Тест сканирования файлов"""
        files = test_backup_manager._scan_files(test_data_structure)
        
        assert len(files) == 3
        file_names = {f.name for f in files}
        assert 'file1.txt' in file_names
        assert 'file2.txt' in file_names
        assert 'file3.txt' in file_names
    
    def test_scan_files_with_exclude(self, test_backup_manager, test_data_structure):
        """Тест сканирования файлов с исключениями"""
        # Добавляем исключение
        test_backup_manager.config['backup']['exclude'] = ['file2.txt']
        
        files = test_backup_manager._scan_files(test_data_structure)
        file_names = {f.name for f in files}
        
        assert 'file1.txt' in file_names
        assert 'file2.txt' not in file_names
        assert 'file3.txt' in file_names
    
    def test_should_exclude(self, test_backup_manager):
        """Тест проверки исключения файлов"""
        patterns = ['*.log', 'temp/*', 'backup_*.tmp']
        
        # Тест различных паттернов
        assert test_backup_manager._should_exclude(
            Path('/path/to/file.log'),
            patterns
        )
        
        assert test_backup_manager._should_exclude(
            Path('/path/to/temp/file.txt'),
            patterns
        )
        
        assert test_backup_manager._should_exclude(
            Path('/path/to/backup_123.tmp'),
            patterns
        )
        
        # Файл не должен быть исключен
        assert not test_backup_manager._should_exclude(
            Path('/path/to/normal.txt'),
            patterns
        )
    
    def test_create_backup(self, test_backup_manager, test_data_structure):
        """Тест создания резервной копии"""
        result = test_backup_manager.create_backup(
            str(test_data_structure),
            description='Test backup'
        )
        
        assert result['success'] is True
        assert 'backup_id' in result
        assert result['file_count'] == 3
        assert result['total_size'] > 0
        assert 'duration' in result
    
    def test_create_backup_nonexistent_source(self, test_backup_manager):
        """Тест создания резервной копии с несуществующим источником"""
        with pytest.raises(FileNotFoundError):
            test_backup_manager.create_backup('/nonexistent/path')
    
    def test_create_archive(self, test_backup_manager, test_data_structure, tmp_path):
        """Тест создания архива"""
        files = test_backup_manager._scan_files(test_data_structure)
        archive_path = tmp_path / 'test.zip'
        
        test_backup_manager._create_archive(
            test_data_structure,
            files,
            archive_path
        )
        
        # Проверяем, что архив создан
        assert archive_path.exists()
        
        # Проверяем содержимое архива
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            namelist = zipf.namelist()
            assert 'file1.txt' in namelist
            assert 'file2.txt' in namelist
            assert 'subdir/file3.txt' in namelist
    
    def test_extract_archive(self, test_backup_manager, test_data_structure, tmp_path):
        """Тест извлечения архива"""
        # Создаем архив
        files = test_backup_manager._scan_files(test_data_structure)
        archive_path = tmp_path / 'test.zip'
        
        test_backup_manager._create_archive(
            test_data_structure,
            files,
            archive_path
        )
        
        # Извлекаем архив
        extract_path = tmp_path / 'extracted'
        extracted_files = test_backup_manager._extract_archive(
            archive_path,
            extract_path
        )
        
        # Проверяем извлеченные файлы
        assert len(extracted_files) == 3
        assert (extract_path / 'file1.txt').exists()
        assert (extract_path / 'file2.txt').exists()
        assert (extract_path / 'subdir' / 'file3.txt').exists()
        
        # Проверяем содержимое файлов
        assert (extract_path / 'file1.txt').read_text() == 'Content 1'
        assert (extract_path / 'file2.txt').read_text() == 'Content 2'
        assert (extract_path / 'subdir' / 'file3.txt').read_text() == 'Content 3'
    
    def test_cleanup_old_backups(self, test_backup_manager):
        """Тест очистки старых резервных копий"""
        # Устанавливаем политику хранения
        test_backup_manager.config['retention'] = {
            'keep_last': 2
        }
        
        # Создаем несколько резервных копий
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / 'test.txt').write_text('test')
            
            # Создаем 3 резервные копии
            for i in range(3):
                test_backup_manager.create_backup(str(temp_path))
        
        # Запускаем очистку в режиме dry-run
        result = test_backup_manager.cleanup_old_backups(dry_run=True)
        
        # Должна быть удалена 1 копия
        assert len(result['to_delete']) == 1
    
    def test_backup_with_encryption(self, test_data_structure):
        """Тест резервного копирования с шифрованием"""
        config = get_default_config()
        config['storage'] = {
            'type': 'local',
            'local': {'path': './test-backups'}
        }
        config['encryption'] = {
            'enabled': True,
            'password': 'test-password',
            'algorithm': 'Fernet'
        }
        
        manager = BackupManager(config)
        result = manager.create_backup(str(test_data_structure))
        
        assert result['success'] is True
        assert result['encrypted'] is True
        
        # Очистка
        import shutil
        shutil.rmtree('./test-backups', ignore_errors=True)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])