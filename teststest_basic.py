echo import pytest > tests\test_basic.py
echo from pathlib import Path >> tests\test_basic.py
echo. >> tests\test_basic.py
echo def test_imports(): >> tests\test_basic.py
echo     """Тест импортов""" >> tests\test_basic.py
echo     try: >> tests\test_basic.py
echo         from src.cli import main, cli >> tests\test_basic.py
echo         from src import __version__ >> tests\test_basic.py
echo         assert __version__ == "1.0.0" >> tests\test_basic.py
echo         print("✅ Импорты работают") >> tests\test_basic.py
echo         return True >> tests\test_basic.py
echo     except ImportError as e: >> tests\test_basic.py
echo         print(f"❌ Ошибка импорта: {e}") >> tests\test_basic.py
echo         return False >> tests\test_basic.py
echo. >> tests\test_basic.py
echo def test_structure(): >> tests\test_basic.py
echo     """Тест структуры проекта""" >> tests\test_basic.py
echo     required_files = [ >> tests\test_basic.py
echo         "requirements.txt", >> tests\test_basic.py
echo         "src/__init__.py", >> tests\test_basic.py
echo         "src/main.py", >> tests\test_basic.py
echo         "src/cli.py", >> tests\test_basic.py
echo         "tests/test_basic.py" >> tests\test_basic.py
echo     ] >> tests\test_basic.py
echo. >> tests\test_basic.py
echo     for file_path in required_files: >> tests\test_basic.py
echo         if Path(file_path).exists(): >> tests\test_basic.py
echo             print(f"✅ Файл найден: {file_path}") >> tests\test_basic.py
echo         else: >> tests\test_basic.py
echo             print(f"❌ Файл не найден: {file_path}") >> tests\test_basic.py
echo             return False >> tests\test_basic.py
echo     return True >> tests\test_basic.py
echo. >> tests\test_basic.py
echo if __name__ == "__main__": >> tests\test_basic.py
echo     print("Запуск тестов...") >> tests\test_basic.py
echo     test_imports() >> tests\test_basic.py
echo     test_structure() >> tests\test_basic.py
echo     print("✅ Тесты завершены") >> tests\test_basic.py