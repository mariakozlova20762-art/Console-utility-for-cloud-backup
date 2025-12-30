"""
Тесты для модуля конфигурации
"""
import pytest
import yaml
import os
from pathlib import Path
import tempfile

from src.config import load_config, save_config, get_default_config, _replace_env_vars

@pytest.fixture
def sample_config():
    """Фикстура с примером конфигурации"""
    return {
        'backup': {
            'name': 'test-backup',
            'exclude': ['*.log', '*.tmp']
        },
        'storage': {
            'type': 'yandex_disk',
            'yandex_disk': {
                'token': '${TEST_TOKEN}',
                'folder': '/Backups'
            }
        }
    }

@pytest.fixture
def config_file(sample_config):
    """Фикстура для временного конфигурационного файла"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_config, f)
        config_path = f.name
    
    yield config_path
    
    # Удаление после теста
    if os.path.exists(config_path):
        os.unlink(config_path)

class TestConfig:
    """Тесты модуля конфигурации"""
    
    def test_get_default_config(self):
        """Тест получения конфигурации по умолчанию"""
        config = get_default_config()
        
        assert 'backup' in config
        assert 'storage' in config
        assert 'compression' in config
        assert 'retention' in config
        
        assert config['backup']['name'] == 'default-backup'
        assert config['storage']['type'] == 'yandex_disk'
    
    def test_load_config(self, config_file):
        """Тест загрузки конфигурации из файла"""
        # Устанавливаем переменную окружения
        os.environ['TEST_TOKEN'] = 'test-token-123'
        
        try:
            config = load_config(config_file)
            
            assert config['backup']['name'] == 'test-backup'
            assert config['storage']['type'] == 'yandex_disk'
            assert config['storage']['yandex_disk']['token'] == 'test-token-123'
        finally:
            # Очищаем переменную окружения
            if 'TEST_TOKEN' in os.environ:
                del os.environ['TEST_TOKEN']
    
    def test_load_config_nonexistent_file(self):
        """Тест загрузки несуществующего конфигурационного файла"""
        with pytest.raises(FileNotFoundError):
            load_config('/nonexistent/path/config.yaml')
    
    def test_load_config_invalid_yaml(self, tmp_path):
        """Тест загрузки невалидного YAML файла"""
        config_file = tmp_path / 'invalid.yaml'
        config_file.write_text('invalid: yaml: [content: here')
        
        with pytest.raises(Exception):
            load_config(str(config_file))
    
    def test_load_config_missing_required_sections(self, tmp_path):
        """Тест загрузки конфигурации без обязательных секций"""
        config_file = tmp_path / 'incomplete.yaml'
        config_file.write_text('some_section: value')
        
        with pytest.raises(ValueError) as excinfo:
            load_config(str(config_file))
        
        assert 'Отсутствует обязательная секция' in str(excinfo.value)
    
    def test_load_config_invalid_storage_type(self, tmp_path):
        """Тест загрузки конфигурации с невалидным типом хранилища"""
        config = {
            'backup': {'name': 'test'},
            'storage': {'type': 'invalid_storage'}
        }
        
        config_file = tmp_path / 'invalid_storage.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        with pytest.raises(ValueError) as excinfo:
            load_config(str(config_file))
        
        assert 'Неподдерживаемый тип хранилища' in str(excinfo.value)
    
    def test_save_config(self, tmp_path, sample_config):
        """Тест сохранения конфигурации в файл"""
        config_file = tmp_path / 'saved_config.yaml'
        
        save_config(sample_config, str(config_file))
        
        # Проверяем, что файл создан
        assert config_file.exists()
        
        # Загружаем и проверяем содержимое
        with open(config_file, 'r') as f:
            loaded_config = yaml.safe_load(f)
        
        assert loaded_config['backup']['name'] == sample_config['backup']['name']
        assert loaded_config['storage']['type'] == sample_config['storage']['type']
    
    def test_replace_env_vars(self):
        """Тест замены переменных окружения"""
        os.environ['TEST_VAR'] = 'test-value'
        os.environ['ANOTHER_VAR'] = 'another-value'
        
        try:
            config = {
                'token': '${TEST_VAR}',
                'nested': {
                    'value': '${ANOTHER_VAR}'
                },
                'list': ['${TEST_VAR}', 'static'],
                'static': 'no-replacement'
            }
            
            result = _replace_env_vars(config)
            
            assert result['token'] == 'test-value'
            assert result['nested']['value'] == 'another-value'
            assert result['list'] == ['test-value', 'static']
            assert result['static'] == 'no-replacement'
        finally:
            # Очищаем переменные окружения
            if 'TEST_VAR' in os.environ:
                del os.environ['TEST_VAR']
            if 'ANOTHER_VAR' in os.environ:
                del os.environ['ANOTHER_VAR']
    
    def test_replace_env_vars_missing(self):
        """Тест замены отсутствующих переменных окружения"""
        config = {
            'token': '${MISSING_VAR}'
        }
        
        with pytest.raises(ValueError) as excinfo:
            _replace_env_vars(config)
        
        assert 'Переменная окружения не найдена' in str(excinfo.value)
    
    def test_config_validation_complete(self, tmp_path):
        """Тест полной валидации конфигурации"""
        config = {
            'backup': {
                'name': 'complete-backup',
                'description': 'Test description',
                'exclude': ['*.log', '*.tmp']
            },
            'storage': {
                'type': 'yandex_disk',
                'yandex_disk': {
                    'token': 'test-token',
                    'folder': '/Backups'
                }
            },
            'compression': {
                'enabled': True,
                'level': 6
            },
            'encryption': {
                'enabled': False
            },
            'retention': {
                'keep_last': 30
            }
        }
        
        config_file = tmp_path / 'complete.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Должно загрузиться без ошибок
        loaded_config = load_config(str(config_file))
        assert loaded_config['backup']['name'] == 'complete-backup'
    
    def test_config_with_s3_storage(self, tmp_path):
        """Тест конфигурации с S3 хранилищем"""
        config = {
            'backup': {'name': 's3-backup'},
            'storage': {
                'type': 's3',
                's3': {
                    'access_key': '${S3_ACCESS_KEY}',
                    'secret_key': '${S3_SECRET_KEY}',
                    'bucket': 'my-backups',
                    'endpoint_url': 'https://storage.example.com'
                }
            }
        }
        
        # Устанавливаем переменные окружения
        os.environ['S3_ACCESS_KEY'] = 'access-key'
        os.environ['S3_SECRET_KEY'] = 'secret-key'
        
        try:
            config_file = tmp_path / 's3_config.yaml'
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            loaded_config = load_config(str(config_file))
            
            assert loaded_config['storage']['type'] == 's3'
            assert loaded_config['storage']['s3']['access_key'] == 'access-key'
            assert loaded_config['storage']['s3']['secret_key'] == 'secret-key'
        finally:
            # Очищаем переменные окружения
            if 'S3_ACCESS_KEY' in os.environ:
                del os.environ['S3_ACCESS_KEY']
            if 'S3_SECRET_KEY' in os.environ:
                del os.environ['S3_SECRET_KEY']
    
    def test_config_with_google_drive(self, tmp_path):
        """Тест конфигурации с Google Drive"""
        config = {
            'backup': {'name': 'gdrive-backup'},
            'storage': {
                'type': 'google_drive',
                'google_drive': {
                    'credentials_file': '/path/to/credentials.json',
                    'folder_id': 'folder123'
                }
            }
        }
        
        config_file = tmp_path / 'gdrive_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        loaded_config = load_config(str(config_file))
        
        assert loaded_config['storage']['type'] == 'google_drive'
        assert loaded_config['storage']['google_drive']['credentials_file'] == '/path/to/credentials.json'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])