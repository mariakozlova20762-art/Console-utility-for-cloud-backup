"""
Тесты для модулей хранилищ
"""
import pytest
from pathlib import Path
import tempfile
import json

from src.storage import get_storage
from src.storage.local_storage import LocalStorage
from src.storage.yandex_disk import YandexDiskStorage

@pytest.fixture
def local_storage_config():
    """Конфигурация для локального хранилища"""
    return {
        'type': 'local',
        'local': {
            'path': './test-storage'
        }
    }

@pytest.fixture
def local_storage(local_storage_config):
    """Фикстура для локального хранилища"""
    storage = LocalStorage(local_storage_config)
    yield storage
    
    # Очистка после теста
    import shutil
    storage_path = Path('./test-storage')
    if storage_path.exists():
        shutil.rmtree(storage_path)

@pytest.fixture
def test_file():
    """Фикстура для тестового файла"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('Test content for storage operations')
        file_path = f.name
    
    yield file_path
    
    # Удаление после теста
    if Path(file_path).exists():
        Path(file_path).unlink()

class TestLocalStorage:
    """Тесты локального хранилища"""
    
    def test_initialization(self, local_storage):
        """Тест инициализации"""
        assert local_storage.config is not None
        assert local_storage.base_path.exists()
    
    def test_upload(self, local_storage, test_file):
        """Тест загрузки файла"""
        backup_id = 'test-backup-123'
        metadata = {'description': 'Test backup'}
        
        result = local_storage.upload(test_file, backup_id, metadata)
        
        # Проверяем, что файл создан
        assert Path(result).exists()
        assert Path(result).name == 'test-backup-123.txt'
        
        # Проверяем метаданные
        metadata_path = Path(result).with_suffix('.meta.json')
        assert metadata_path.exists()
        
        with open(metadata_path, 'r') as f:
            loaded_metadata = json.load(f)
        assert loaded_metadata['description'] == 'Test backup'
    
    def test_download(self, local_storage, test_file):
        """Тест скачивания файла"""
        # Сначала загружаем файл
        backup_id = 'test-download'
        local_storage.upload(test_file, backup_id)
        
        # Скачиваем в новое место
        with tempfile.NamedTemporaryFile(delete=False) as f:
            target_path = f.name
        
        try:
            success = local_storage.download(backup_id, target_path)
            
            assert success is True
            assert Path(target_path).exists()
            
            # Проверяем содержимое
            with open(target_path, 'r') as f:
                content = f.read()
            assert content == 'Test content for storage operations'
        finally:
            if Path(target_path).exists():
                Path(target_path).unlink()
    
    def test_download_nonexistent(self, local_storage):
        """Тест скачивания несуществующего файла"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            target_path = f.name
        
        try:
            with pytest.raises(FileNotFoundError):
                local_storage.download('nonexistent-backup', target_path)
        finally:
            if Path(target_path).exists():
                Path(target_path).unlink()
    
    def test_list_backups(self, local_storage, test_file):
        """Тест получения списка резервных копий"""
        # Загружаем несколько файлов
        for i in range(3):
            backup_id = f'test-backup-{i}'
            metadata = {'index': i}
            local_storage.upload(test_file, backup_id, metadata)
        
        # Получаем список
        backups = local_storage.list_backups()
        
        assert len(backups) == 3
        
        # Проверяем структуру данных
        for backup in backups:
            assert 'id' in backup
            assert 'path' in backup
            assert 'size' in backup
            assert 'created_at' in backup
            assert 'metadata' in backup
        
        # Проверяем порядок (новые первыми)
        backup_ids = [b['id'] for b in backups]
        assert backup_ids == ['test-backup-2', 'test-backup-1', 'test-backup-0']
    
    def test_delete(self, local_storage, test_file):
        """Тест удаления резервной копии"""
        backup_id = 'test-delete'
        
        # Загружаем файл
        local_storage.upload(test_file, backup_id)
        
        # Проверяем, что файл существует
        backups = local_storage.list_backups()
        assert len(backups) == 1
        
        # Удаляем
        success = local_storage.delete(backup_id)
        
        assert success is True
        
        # Проверяем, что файл удален
        backups = local_storage.list_backups()
        assert len(backups) == 0
    
    def test_delete_nonexistent(self, local_storage):
        """Тест удаления несуществующей резервной копии"""
        success = local_storage.delete('nonexistent-backup')
        assert success is False
    
    def test_test_connection(self, local_storage):
        """Тест проверки подключения"""
        success = local_storage.test_connection()
        assert success is True
    
    def test_get_backup_info(self, local_storage, test_file):
        """Тест получения информации о резервной копии"""
        backup_id = 'test-info'
        metadata = {'test': 'data'}
        
        local_storage.upload(test_file, backup_id, metadata)
        
        info = local_storage.get_backup_info(backup_id)
        
        assert info is not None
        assert info['id'] == backup_id
        assert info['metadata']['test'] == 'data'
    
    def test_get_backup_info_nonexistent(self, local_storage):
        """Тест получения информации о несуществующей резервной копии"""
        info = local_storage.get_backup_info('nonexistent')
        assert info is None

class TestStorageFactory:
    """Тесты фабрики хранилищ"""
    
    def test_get_local_storage(self, local_storage_config):
        """Тест получения локального хранилища"""
        storage = get_storage(local_storage_config)
        assert isinstance(storage, LocalStorage)
    
    def test_get_invalid_storage_type(self):
        """Тест получения невалидного типа хранилища"""
        config = {'type': 'invalid_storage'}
        
        with pytest.raises(ValueError) as excinfo:
            get_storage(config)
        
        assert 'Неподдерживаемый тип хранилища' in str(excinfo.value)
    
    def test_storage_config_validation(self):
        """Тест валидации конфигурации хранилища"""
        # Конфигурация без типа
        config = {}
        
        with pytest.raises(KeyError):
            get_storage(config)
    
    def test_yandex_disk_storage_initialization(self):
        """Тест инициализации Yandex Disk хранилища"""
        config = {
            'type': 'yandex_disk',
            'yandex_disk': {
                'token': 'test-token',
                'folder': '/TestBackups'
            }
        }
        
        storage = get_storage(config)
        assert isinstance(storage, YandexDiskStorage)
        assert storage.token == 'test-token'
        assert storage.folder == '/TestBackups'

class TestStorageIntegration:
    """Интеграционные тесты хранилищ"""
    
    def test_upload_download_cycle(self, local_storage, test_file):
        """Полный цикл загрузки и скачивания"""
        backup_id = 'integration-test'
        original_content = Path(test_file).read_text()
        
        # Загружаем
        upload_path = local_storage.upload(test_file, backup_id)
        assert Path(upload_path).exists()
        
        # Проверяем список
        backups = local_storage.list_backups()
        assert len(backups) == 1
        assert backups[0]['id'] == backup_id
        
        # Скачиваем
        with tempfile.NamedTemporaryFile(delete=False) as f:
            download_path = f.name
        
        try:
            success = local_storage.download(backup_id, download_path)
            assert success is True
            
            downloaded_content = Path(download_path).read_text()
            assert downloaded_content == original_content
        finally:
            if Path(download_path).exists():
                Path(download_path).unlink()
        
        # Удаляем
        success = local_storage.delete(backup_id)
        assert success is True
        
        # Проверяем, что удалено
        backups = local_storage.list_backups()
        assert len(backups) == 0
    
    def test_multiple_backups_management(self, local_storage, test_file):
        """Управление несколькими резервными копиями"""
        # Создаем несколько резервных копий
        for i in range(5):
            backup_id = f'backup-{i:02d}'
            local_storage.upload(test_file, backup_id)
        
        # Проверяем количество
        backups = local_storage.list_backups()
        assert len(backups) == 5
        
        # Удаляем некоторые
        local_storage.delete('backup-01')
        local_storage.delete('backup-03')
        
        # Проверяем оставшиеся
        backups = local_storage.list_backups()
        assert len(backups) == 3
        
        backup_ids = {b['id'] for b in backups}
        assert backup_ids == {'backup-00', 'backup-02', 'backup-04'}

if __name__ == '__main__':
    pytest.main([__file__, '-v'])