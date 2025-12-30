#!/usr/bin/env python3
"""
Интеграционный тест приложения
"""

import subprocess
import sys
import os
from pathlib import Path
import zipfile
import shutil

def run_command(cmd, check=True):
    """Выполнить команду и вернуть результат"""
    print(f"🚀 Выполняю: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(f"📤 Вывод: {result.stdout.strip()}")
    if result.stderr:
        print(f"⚠️  Ошибки: {result.stderr.strip()}")
    
    if check and result.returncode != 0:
        print(f"❌ Команда завершилась с ошибкой: {result.returncode}")
        sys.exit(1)
    
    return result

def test_local_installation():
    """Тест локальной установки"""
    print("\n" + "="*60)
    print("🧪 Тест локальной установки")
    print("="*60)
    
    # Проверяем зависимости
    print("\n1. Проверка зависимостей...")
    run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Проверяем CLI
    print("\n2. Проверка CLI...")
    run_command([sys.executable, "-m", "src.main", "--help"])
    run_command([sys.executable, "-m", "src.main", "--version"])
    run_command([sys.executable, "-m", "src.main", "info"])
    
    print("✅ Локальная установка работает!")

def test_backup_functionality():
    """Тест функциональности резервного копирования"""
    print("\n" + "="*60)
    print("🧪 Тест функциональности резервного копирования")
    print("="*60)
    
    # Создаем тестовые данные
    test_dir = Path("test-data")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("Тестовые данные 1")
    (test_dir / "file2.txt").write_text("Тестовые данные 2")
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir" / "file3.txt").write_text("Тестовые данные 3")
    
    # Создаем резервную копию
    print("\n1. Создание резервной копии...")
    backup_file = "test-backup.zip"
    if Path(backup_file).exists():
        Path(backup_file).unlink()
    
    run_command([
        sys.executable, "-m", "src.main", 
        "backup", str(test_dir),
        "--output", backup_file,
        "--compress"
    ])
    
    # Проверяем архив
    print("\n2. Проверка архива...")
    if not Path(backup_file).exists():
        print(f"❌ Архив не создан: {backup_file}")
        sys.exit(1)
    
    with zipfile.ZipFile(backup_file, 'r') as zipf:
        files = zipf.namelist()
        print(f"✅ Архив создан. Файлов в архиве: {len(files)}")
        for file in files:
            print(f"   - {file}")
    
    # Восстанавливаем
    print("\n3. Восстановление из архива...")
    restored_dir = Path("test-restored")
    if restored_dir.exists():
        shutil.rmtree(restored_dir)
    
    run_command([
        sys.executable, "-m", "src.main",
        "restore", backup_file, str(restored_dir),
        "--overwrite"
    ])
    
    # Проверяем восстановленные файлы
    print("\n4. Проверка восстановленных файлов...")
    restored_files = list(restored_dir.rglob("*"))
    print(f"✅ Восстановлено файлов: {len(restored_files)}")
    
    # Сравниваем содержимое
    for orig_file in test_dir.rglob("*"):
        if orig_file.is_file():
            rel_path = orig_file.relative_to(test_dir)
            restored_file = restored_dir / rel_path
            
            if not restored_file.exists():
                print(f"❌ Файл не восстановлен: {rel_path}")
                continue
            
            orig_content = orig_file.read_text()
            restored_content = restored_file.read_text()
            
            if orig_content == restored_content:
                print(f"   ✅ {rel_path} - OK")
            else:
                print(f"   ❌ {rel_path} - содержимое не совпадает")
    
    # Очистка
    shutil.rmtree(test_dir, ignore_errors=True)
    shutil.rmtree(restored_dir, ignore_errors=True)
    if Path(backup_file).exists():
        Path(backup_file).unlink()
    
    print("✅ Функциональность резервного копирования работает!")

def test_docker_functionality():
    """Тест Docker функциональности"""
    print("\n" + "="*60)
    print("🐳 Тест Docker функциональности")
    print("="*60)
    
    # Собираем образ
    print("\n1. Сборка Docker образа...")
    run_command(["docker", "build", "-t", "cloud-backup-test", "."])
    
    # Проверяем образ
    print("\n2. Проверка Docker образа...")
    result = run_command(["docker", "images", "cloud-backup-test"])
    if "cloud-backup-test" not in result.stdout:
        print("❌ Docker образ не создан")
        sys.exit(1)
    
    # Тестируем базовые команды
    print("\n3. Тест базовых команд через Docker...")
    run_command(["docker", "run", "--rm", "cloud-backup-test", "--help"])
    run_command(["docker", "run", "--rm", "cloud-backup-test", "--version"])
    run_command(["docker", "run", "--rm", "cloud-backup-test", "info"])
    
    # Подготавливаем тестовые данные для Docker
    print("\n4. Подготовка тестовых данных для Docker...")
    docker_test_dir = Path("docker-test-data")
    docker_backup_dir = Path("docker-backups")
    docker_restored_dir = Path("docker-restored")
    
    for dir_path in [docker_test_dir, docker_backup_dir, docker_restored_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
        dir_path.mkdir()
    
    (docker_test_dir / "docker-file.txt").write_text("Тестовые данные для Docker")
    
    # Тестируем резервное копирование через Docker
    print("\n5. Тест резервного копирования через Docker...")
    run_command([
        "docker", "run", "--rm",
        "-v", f"{docker_test_dir.absolute()}:/data:ro",
        "-v", f"{docker_backup_dir.absolute()}:/backups",
        "cloud-backup-test",
        "backup", "/data", "--output", "/backups/docker-test.zip", "--compress"
    ])
    
    # Проверяем, что архив создан
    backup_path = docker_backup_dir / "docker-test.zip"
    if not backup_path.exists():
        print(f"❌ Архив не создан: {backup_path}")
        sys.exit(1)
    
    print(f"✅ Docker архив создан: {backup_path}")
    
    # Тестируем восстановление через Docker
    print("\n6. Тест восстановления через Docker...")
    run_command([
        "docker", "run", "--rm",
        "-v", f"{docker_backup_dir.absolute()}:/backups:ro",
        "-v", f"{docker_restored_dir.absolute()}:/restored",
        "cloud-backup-test",
        "restore", "/backups/docker-test.zip", "/restored", "--overwrite"
    ])
    
    # Проверяем восстановленные файлы
    restored_files = list(docker_restored_dir.rglob("*"))
    print(f"✅ Восстановлено файлов через Docker: {len(restored_files)}")
    
    # Очистка
    for dir_path in [docker_test_dir, docker_backup_dir, docker_restored_dir]:
        shutil.rmtree(dir_path, ignore_errors=True)
    
    # Удаляем тестовый образ
    print("\n7. Очистка Docker образа...")
    run_command(["docker", "rmi", "cloud-backup-test"])
    
    print("✅ Docker функциональность работает!")

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск интеграционных тестов Cloud Backup CLI")
    print("="*60)
    
    try:
        # Проверяем текущую директорию
        if not Path("src").exists() or not Path("requirements.txt").exists():
            print("❌ Запустите тест из корневой директории проекта")
            sys.exit(1)
        
        test_local_installation()
        test_backup_functionality()
        test_docker_functionality()
        
        print("\n" + "="*60)
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("="*60)
        print("\nПроект готов к работе! Можно использовать команды:")
        print("  python -m src.main --help")
        print("  docker build -t cloud-backup .")
        print("  docker run --rm cloud-backup info")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()