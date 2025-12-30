"""
Модуль шифрования и дешифрования файлов
"""
import os
from pathlib import Path
from typing import Optional
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)

class Encryptor:
    """Класс для шифрования и дешифрования файлов"""
    
    def __init__(self, password: str, algorithm: str = 'AES-256-GCM'):
        """
        Инициализировать шифратор
        
        Args:
            password: Пароль для шифрования
            algorithm: Алгоритм шифрования (AES-256-GCM или Fernet)
        """
        self.password = password.encode()
        self.algorithm = algorithm
        
        if algorithm == 'Fernet':
            # Генерация ключа из пароля
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'cloud-backup-salt',
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.password))
            self.cipher = Fernet(key)
        else:
            # Для AES-GCM ключ будет генерироваться при каждом шифровании
            self.cipher = None
    
    def encrypt_file(self, source_path: str, target_path: str) -> None:
        """
        Зашифровать файл
        
        Args:
            source_path: Путь к исходному файлу
            target_path: Путь для сохранения зашифрованного файла
        """
        if self.algorithm == 'Fernet':
            self._encrypt_fernet(source_path, target_path)
        else:
            self._encrypt_aes_gcm(source_path, target_path)
        
        logger.info(f"Файл зашифрован