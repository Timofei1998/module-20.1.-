import requests
import time
import psutil
import json
import os
from multiprocessing import Pool, Manager
import random

# Путь к файлу для записи результатов
RESULTS_FILE = 'app/multiprocessing_results.json'

# URL API списка университетов Российской Федерации
API_URL = 'http://universities.hipolabs.com/search?country=Russian+Federation'

# Общее число запросов
NUM_REQUESTS = 100

# Максимальное число одновременно работающих процессов
MAX_PROCESSES = 10

# Сколько раз в целом можно пытаться заново запустить неудачные запросы
TOTAL_MAX_RETRIES = 5

def fetch_universities(args):
    """
    Делает до max_retries локальных попыток отправить запрос.
    Если ни одна не удалась, возвращает False.
    При успехе возвращает True.
    """
    request_number, max_retries, counter = args
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(API_URL, timeout=5)
            response.raise_for_status()
            with counter['lock']:
                counter['successful_requests'] += 1
            print(f"[Запрос #{request_number}] Успех на попытке {attempt}.")
            return True
        except requests.RequestException as e:
            print(f"[Запрос #{request_number}] Ошибка (попытка {attempt}): {e}")
            if attempt < max_retries:
                sleep_time = 0.5 + random.uniform(0, 0.5)
                print(f"Повтор через {sleep_time:.2f} с...")
                time.sleep(sleep_time)
    with counter['lock']:
        counter['failed_requests'] += 1
    print(f"[Запрос #{request_number}] Не удался после {max_retries} локальных попыток.")
    return False

def perform_test():
    """
    Механизм:
    1) Имеем список из 100 запросов (1..100).
    2) В каждой итерации создаём пул, обрабатываем только текущий список неудачных.
    3) Если остались неуспешные - снова пытаемся (до TOTAL_MAX_RETRIES итераций).
    """
    manager = Manager()

    shared_counter = manager.dict({
        'successful_requests': 0,
        'failed_requests': 0,
        'lock': manager.Lock()
    })

    results = {
        'total_requests': NUM_REQUESTS,
        'successful_requests': 0,
        'failed_requests': 0,
        'average_time_per_request': 0.0,
        'cpu_usage_percent': 0.0,
        'memory_usage_mb': 0.0,
        'total_elapsed_time': 0.0
    }

    process = psutil.Process(os.getpid())
    cpu_before = process.cpu_times()
    total_cpu_time_before = cpu_before.user + cpu_before.system
    mem_before = process.memory_info().rss / (1024 * 1024)

    start_time = time.time()

    all_requests = list(range(1, NUM_REQUESTS + 1))

    current_retry = 0
    while all_requests and current_retry < TOTAL_MAX_RETRIES:
        print(f"\nИтерация {current_retry+1}/{TOTAL_MAX_RETRIES}, запросов осталось: {len(all_requests)}")

        success_before_iter = shared_counter['successful_requests']
        fail_before_iter = shared_counter['failed_requests']

        args = [(req_num, 3, shared_counter) for req_num in all_requests]

        with Pool(processes=MAX_PROCESSES) as pool:
            results_map = pool.map(fetch_universities, args)

        iteration_new_success = shared_counter['successful_requests'] - success_before_iter
        iteration_new_fail = shared_counter['failed_requests'] - fail_before_iter

        print(f"Итерация {current_retry+1} завершена. Новых успехов: {iteration_new_success}, новых неудач: {iteration_new_fail}.")

        all_requests = [args[i][0] for i, success in enumerate(results_map) if not success]

        current_retry += 1

    end_time = time.time()

    cpu_after = process.cpu_times()
    total_cpu_time_after = cpu_after.user + cpu_after.system
    mem_after = process.memory_info().rss / (1024 * 1024)

    delta_cpu_time = total_cpu_time_after - total_cpu_time_before
    delta_wall_time = end_time - start_time
    cpu_usage_percent = (delta_cpu_time / delta_wall_time) * 100

    # Итоговые результаты
    results['successful_requests'] = shared_counter['successful_requests']
    results['failed_requests'] = NUM_REQUESTS - shared_counter['successful_requests']
    results['total_elapsed_time'] = delta_wall_time
    results['average_time_per_request'] = delta_wall_time / NUM_REQUESTS
    results['cpu_usage_percent'] = cpu_usage_percent
    results['memory_usage_mb'] = mem_after - mem_before

    return results

def save_results(results):
    try:
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"Результаты тестирования сохранены в {RESULTS_FILE}.")
    except IOError as e:
        print(f"Ошибка при сохранении результатов: {e}")

def main():
    print("Начало многопроцессного тестирования...")
    results = perform_test()
    print("Тестирование завершено.")
    print(json.dumps(results, indent=4, ensure_ascii=False))
    save_results(results)

if __name__ == "__main__":
    main()
