"""
Тесты для CLI интерфейса
"""
import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
import yaml
import os

from src.cli import cli

@pytest.fixture
def runner():
    """Фикстура для CliRunner"""
    return CliRunner()

@pytest.fixture
def temp_config():
    """Фикстура для временного конфигурационного файла"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config = {
            'backup': {
                'name': 'test-backup',
                'exclude': ['*.tmp', '*.log']
            },
            'storage': {
                'type': 'local',
                'local': {
                    'path': './test-backups'
                }
            },
            'compression': {
                'enabled': True,
                'level': 6
            }
        }
        yaml.dump(config, f)
        config_path = f.name
    
    yield config_path
    
    # Удаление после теста
    if os.path.exists(config_path):
        os.unlink(config_path)

@pytest.fixture
def test_data():
    """Фикстура для тестовых данных"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Создаем тестовые файлы
        data_dir = Path(temp_dir) / 'data'
        data_dir.mkdir()
        
        (data_dir / 'file1.txt').write_text('Test content 1')
        (data_dir / 'file2.txt').write_text('Test content 2')
        (data_dir / 'subdir').mkdir()
        (data_dir / 'subdir' / 'file3.txt').write_text('Test content 3')
        
        yield str(data_dir)

class TestCLI:
    """Тесты CLI команд"""
    
    def test_cli_help(self, runner):
        """Тест команды help"""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Консольная утилита для резервного копирования в облако' in result.output
    
    def test_version(self, runner):
        """Тест команды version"""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert 'Cloud Backup CLI' in result.output
    
    def test_validate_config(self, runner, temp_config):
        """Тест валидации конфигурации"""
        result = runner.invoke(cli, ['--config', temp_config, 'validate'])
        assert result.exit_code == 0
        assert 'Конфигурация валидна' in result.output
    
    def test_validate_invalid_config(self, runner):
        """Тест валидации невалидной конфигурации"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
            f.write('invalid: yaml: content')
            f.flush()
            
            result = runner.invoke(cli, ['--config', f.name, 'validate'])
            assert result.exit_code != 0
    
    def test_backup_command(self, runner, temp_config, test_data):
        """Тест команды backup"""
        result = runner.invoke(cli, [
            '--config', temp_config,
            '--verbose',
            'backup',
            test_data,
            '--name', 'test-backup'
        ])
        
        print(result.output)  # Для отладки
        assert result.exit_code == 0
        assert 'Резервная копия создана успешно' in result.output
    
    def test_backup_with_description(self, runner, temp_config, test_data):
        """Тест команды backup с описанием"""
        result = runner.invoke(cli, [
            '--config', temp_config,
            'backup',
            test_data,
            '--description', 'Test backup description'
        ])
        
        assert result.exit_code == 0
        assert 'Резервная копия создана успешно' in result.output
    
    def test_list_command(self, runner, temp_config):
        """Тест команды list"""
        result = runner.invoke(cli, [
            '--config', temp_config,
            'list',
            '--limit', '5'
        ])
        
        assert result.exit_code == 0
    
    def test_cleanup_dry_run(self, runner, temp_config):
        """Тест команды cleanup с dry-run"""
        result = runner.invoke(cli, [
            '--config', temp_config,
            'cleanup',
            '--dry-run'
        ])
        
        assert result.exit_code == 0
        assert 'Копии, которые будут удалены' in result.output
    
    def test_missing_source(self, runner, temp_config):
        """Тест backup с несуществующим источником"""
        result = runner.invoke(cli, [
            '--config', temp_config,
            'backup',
            '/nonexistent/path'
        ])
        
        assert result.exit_code != 0
        assert 'не найден' in result.output or 'ошибка' in result.output.lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])