import asyncio
import aiohttp
import time
import psutil
import json
import os

# Путь к файлу для записи результатов
RESULTS_FILE = 'app/asyncio_results.json'

# URL API списка университетов Российской Федерации
API_URL = 'http://universities.hipolabs.com/search?country=Russian+Federation'

# Количество повторений запроса для тестирования
NUM_REQUESTS = 100

# Максимальное количество одновременных запросов
MAX_CONCURRENT_REQUESTS = 10

async def fetch_universities(session, request_number):
    """
    Отправляет асинхронный HTTP-запрос к API и возвращает статус выполнения.
    """
    try:
        async with session.get(API_URL, timeout=10) as response:
            response.raise_for_status()
            await response.json()
            print(f"Запрос {request_number}/{NUM_REQUESTS} выполнен.")
            return True
    except aiohttp.ClientError as e:
        print(f"Ошибка при запросе {request_number}: {e}")
        return False
    except asyncio.TimeoutError:
        print(f"Тайм-аут запроса {request_number}.")
        return False

async def perform_test():
    """
    Выполняет серию асинхронных запросов и собирает метрики производительности.
    """
    results = {
        'total_requests': NUM_REQUESTS,
        'successful_requests': 0,
        'failed_requests': 0,
        'average_time_per_request': 0.0,
        'cpu_usage_percent': 0.0,
        'memory_usage_mb': 0.0,
        'total_elapsed_time': 0.0
    }

    # Получаем текущие значения CPU и памяти до теста
    process = psutil.Process(os.getpid())
    cpu_times_before = process.cpu_times()
    total_cpu_time_before = cpu_times_before.user + cpu_times_before.system
    mem_before = process.memory_info().rss / (1024 * 1024)  # в МБ

    start_time = time.time()

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            asyncio.create_task(fetch_universities(session, i + 1))
            for i in range(NUM_REQUESTS)
        ]
        responses = await asyncio.gather(*tasks)

    end_time = time.time()

    # Получаем текущие значения CPU и памяти после теста
    cpu_times_after = process.cpu_times()
    total_cpu_time_after = cpu_times_after.user + cpu_times_after.system
    mem_after = process.memory_info().rss / (1024 * 1024)  # в МБ

    # Вычисляем разницу в CPU времени и общее время выполнения
    delta_cpu_time = total_cpu_time_after - total_cpu_time_before
    delta_wall_time = end_time - start_time

    # Вычисляем процент использования CPU
    cpu_usage_percent = (delta_cpu_time / delta_wall_time) * 100

    # Обработка результатов
    results['successful_requests'] = sum(responses)
    results['failed_requests'] = NUM_REQUESTS - results['successful_requests']
    results['total_elapsed_time'] = delta_wall_time
    results['average_time_per_request'] = delta_wall_time / NUM_REQUESTS
    results['cpu_usage_percent'] = cpu_usage_percent
    results['memory_usage_mb'] = mem_after - mem_before

    return results

def save_results(results):
    """
    Сохраняет результаты тестирования в JSON-файл.
    """
    try:
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"Результаты тестирования сохранены в файл {RESULTS_FILE}.")
    except IOError as e:
        print(f"Ошибка при сохранении результатов: {e}")

def main():
    print("Начало асинхронного тестирования с использованием asyncio...")
    results = asyncio.run(perform_test())
    print("Тестирование завершено.")
    print(json.dumps(results, indent=4, ensure_ascii=False))
    save_results(results)

if __name__ == "__main__":
    main()
