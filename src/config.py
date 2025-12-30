"""
Загрузка и валидация конфигурации
"""
import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Загрузить конфигурацию из YAML файла
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Заменяем переменные окружения
    config = _replace_env_vars(config)
    
    # Валидация конфигурации
    _validate_config(config)
    
    logger.info(f"Конфигурация загружена из {config_path}")
    return config

def _replace_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Заменить переменные окружения в конфигурации
    """
    def replace(obj):
        if isinstance(obj, dict):
            return {k: replace(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            value = os.getenv(env_var)
            if value is None:
                raise ValueError(f"Переменная окружения не найдена: {env_var}")
            return value
        else:
            return obj
    
    return replace(config)

def _validate_config(config: Dict[str, Any]):
    """
    Проверить валидность конфигурации
    """
    required_sections = ['backup', 'storage']
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Отсутствует обязательная секция: {section}")
    
    # Проверка секции backup
    backup = config['backup']
    if 'name' not in backup:
        raise ValueError("В секции backup отсутствует поле 'name'")
    
    # Проверка секции storage
    storage = config['storage']
    if 'type' not in storage:
        raise ValueError("В секции storage отсутствует поле 'type'")
    
    valid_storage_types = ['yandex_disk', 'google_drive', 's3', 'local']
    if storage['type'] not in valid_storage_types:
        raise ValueError(f"Неподдерживаемый тип хранилища: {storage['type']}")
    
    # Проверка конфигурации для конкретного типа хранилища
    storage_type = storage['type']
    if storage_type not in storage:
        raise ValueError(f"Отсутствует конфигурация для хранилища типа: {storage_type}")
    
    logger.debug(f"Конфигурация валидна, тип хранилища: {storage_type}")

def save_config(config: Dict[str, Any], config_path: str):
    """
    Сохранить конфигурацию в файл
    """
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"Конфигурация сохранена в {config_path}")

def get_default_config() -> Dict[str, Any]:
    """
    Получить конфигурацию по умолчанию
    """
    return {
        'backup': {
            'name': 'default-backup',
            'description': 'Automatic backup',
            'exclude': ['.git', '__pycache__', '*.pyc', '*.log', '.DS_Store'],
            'max_backup_size': '10GB',
            'split_size': '1GB'
        },
        'storage': {
            'type': 'yandex_disk',
            'yandex_disk': {
                'token': '${YANDEX_TOKEN}',
                'folder': '/Backups'
            }
        },
        'encryption': {
            'enabled': False,
            'algorithm': 'AES-256-GCM',
            'password': '${ENCRYPTION_PASSWORD}'
        },
        'compression': {
            'enabled': True,
            'level': 6,
            'format': 'zip'
        },
        'retention': {
            'keep_last': 30,
            'keep_daily': 7,
            'keep_weekly': 4,
            'keep_monthly': 12
        },
        'logging': {
            'level': 'INFO',
            'file': 'backup.log',
            'max_size': '10MB',
            'backup_count': 5
        }
    }