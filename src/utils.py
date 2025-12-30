"""
Вспомогательные утилиты
"""
import os
import sys
import logging
import hashlib
from pathlib import Path
from typing import Optional
import json
from datetime import datetime, timedelta
import humanize

def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
) -> None:
    """
    Настройка логирования
    
    Args:
        level: Уровень логирования
        log_file: Путь к файлу лога
        log_format: Формат сообщений лога
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers
    )

def format_size(size_bytes: int) -> str:
    """
    Форматировать размер в читаемый вид
    
    Args:
        size_bytes: Размер в байтах
    
    Returns:
        str: Отформатированный размер
    """
    return humanize.naturalsize(size_bytes)

def format_duration(seconds: float) -> str:
    """
    Форматировать длительность в читаемый вид
    
    Args:
        seconds: Количество секунд
    
    Returns:
        str: Отформатированная длительность
    """
    return humanize.precisedelta(timedelta(seconds=seconds))

def calculate_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """
    Вычислить хэш файла
    
    Args:
        file_path: Путь к файлу
        algorithm: Алгоритм хэширования
    
    Returns:
        str: Хэш файла
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()

def ensure_directory(path: str) -> Path:
    """
    Убедиться, что директория существует
    
    Args:
        path: Путь к директории
    
    Returns:
        Path: Объект Path созданной директории
    """
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory

def read_json_file(file_path: str) -> dict:
    """
    Прочитать JSON файл
    
    Args:
        file_path: Путь к JSON файлу
    
    Returns:
        dict: Содержимое JSON файла
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json_file(data: dict, file_path: str) -> None:
    """
    Записать данные в JSON файл
    
    Args:
        data: Данные для записи
        file_path: Путь к JSON файлу
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_version() -> str:
    """
    Получить версию приложения
    
    Returns:
        str: Версия приложения
    """
    # Можно читать из pyproject.toml или __init__.py
    try:
        from src import __version__
        return __version__
    except ImportError:
        return "1.0.0"

def validate_path(path: str, must_exist: bool = True) -> Path:
    """
    Проверить путь
    
    Args:
        path: Путь для проверки
        must_exist: Должен ли путь существовать
    
    Returns:
        Path: Объект Path
    
    Raises:
        FileNotFoundError: Если путь должен существовать, но не существует
        ValueError: Если путь некорректен
    """
    path_obj = Path(path).resolve()
    
    if must_exist and not path_obj.exists():
        raise FileNotFoundError(f"Путь не существует: {path}")
    
    return path_obj

def create_backup_metadata(
    source: str,
    backup_id: str,
    file_count: int,
    total_size: int,
    description: Optional[str] = None,
    **kwargs
) -> dict:
    """
    Создать метаданные для резервной копии
    
    Args:
        source: Источник резервного копирования
        backup_id: ID резервной копии
        file_count: Количество файлов
        total_size: Общий размер
        description: Описание резервной копии
        **kwargs: Дополнительные метаданные
    
    Returns:
        dict: Метаданные резервной копии
    """
    return {
        'backup_id': backup_id,
        'source': str(source),
        'description': description,
        'file_count': file_count,
        'total_size': total_size,
        'created_at': datetime.now().isoformat(),
        'version': get_version(),
        **kwargs
    }

def format_datetime(dt: datetime) -> str:
    """
    Форматировать дату-время в читаемый вид
    
    Args:
        dt: Объект datetime
    
    Returns:
        str: Отформатированная дата-время
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_datetime(dt_str: str) -> datetime:
    """
    Разобрать строку даты-времени
    
    Args:
        dt_str: Строка с датой-временем
    
    Returns:
        datetime: Объект datetime
    """
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Не удалось разобрать дату: {dt_str}")