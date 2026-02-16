"""
Запуск всех тестов в симуляции для CubeSat 1U системы
Без использования реального оборудования
"""
import subprocess
import sys
import os
from datetime import datetime


def run_all_tests():
    """Запуск всех тестов в симуляции"""
    print("=" * 60)
    print("ЗАПУСК ВСЕХ ТЕСТОВ В СИМУЛЯЦИИ")
    print("=" * 60)
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Список тестов для запуска
    test_files = [
        "tests/simple_test_suite.py",
        "tests/test_communication_simulated.py",
        # Добавьте другие тестовые файлы по мере необходимости
    ]

    results = []
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Запуск тестов из: {test_file}")
            print("-" * 40)

            # Запуск тестов с помощью subprocess
            try:
                result = subprocess.run(
                    [sys.executable, test_file],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 минуты на каждый файл
                )

                # Подсчет результатов
                output_lines = result.stdout.split('\n')
                passed = failed = errors = 0

                for line in output_lines:
                    if 'OK' in line and 'test' in line:
                        passed += 1
                    elif 'FAIL' in line:
                        failed += 1
                    elif 'ERROR' in line:
                        errors += 1

                test_result = {
                    'file': test_file,
                    'passed': passed,
                    'failed': failed,
                    'errors': errors,
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }

                results.append(test_result)
                total_tests += passed + failed + errors
                total_passed += passed
                total_failed += failed
                total_errors += errors

                print(f"Результат: {passed} пройдено, {failed} неудач, {errors} ошибок")
                print()

                if result.returncode != 0 or failed > 0 or errors > 0:
                    print("STDOUT:")
                    print(result.stdout)
                    if result.stderr:
                        print("STDERR:")
                        print(result.stderr)
                    print()

            except subprocess.TimeoutExpired:
                print(f"Таймаут при выполнении {test_file}")
                results.append({
                    'file': test_file,
                    'passed': 0,
                    'failed': 0,
                    'errors': 1,
                    'returncode': -1,
                    'stdout': '',
                    'stderr': 'Timeout'
                })
                total_errors += 1
                print()
        else:
            print(f"Файл не найден: {test_file}")
            print()

    # Итоговый отчет
    print("=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    print(f"Всего тестов: {total_tests}")
    print(f"Пройдено: {total_passed}")
    print(f"Неудач: {total_failed}")
    print(f"Ошибок: {total_errors}")
    print(f"Успеваемость: {(total_passed/total_tests*100):.1f}% если есть тесты" if total_tests > 0 else "Нет пройденных тестов")

    if total_errors == 0 and total_failed == 0 and total_passed > 0:
        print("\n✅ Все тесты пройдены успешно!")
        return True
    else:
        print(f"\n❌ Ошибки в тестировании: {total_errors} ошибок, {total_failed} неудач")
        return False


def run_with_pytest():
    """Запуск тестов с помощью pytest (альтернативный метод)"""
    print("\nАльтернативный запуск с помощью pytest:")
    print("-" * 40)

    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/",
            "-v", "--tb=short", "-x"  # -x для остановки при первой ошибке
        ], capture_output=True, text=True, timeout=300)  # 5 минут на все тесты

        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"Pytest результат: {result.returncode}")
        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("Pytest: Таймаут выполнения")
        return False


if __name__ == '__main__':
    print("CubeSat 1U - Тестирование в симуляции")
    print("=====================================")

    # Запуск основных тестов
    success_main = run_all_tests()

    # Запуск с помощью pytest
    success_pytest = run_with_pytest()

    # Итог
    print("\n" + "=" * 60)
    print("ФИНАЛЬНЫЙ РЕЗУЛЬТАТ")
    print("=" * 60)
    if success_main and success_pytest:
        print("✅ Все тесты пройдены успешно в обоих режимах!")
        sys.exit(0)
    else:
        print("⚠️  Некоторые тесты не прошли")
        sys.exit(1 if not success_main else 0)