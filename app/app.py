import os
import psutil
import time
import threading
import logging
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальные переменные для хранения настроек ресурсов
cpu_load = 0
memory_load_mb = 0

# Флаг для управления нагрузочными потоками
should_run = True

# Безопасные пределы и параметры
MAX_MEMORY_PERCENT = 85  # Максимальное использование памяти в процентах от доступного
CPU_CHECK_INTERVAL = 0.5  # Интервал для проверки CPU в секундах
MEMORY_CHECK_INTERVAL = 5.0  # Интервал для проверки памяти в секундах (увеличен с 1.0 до 5.0)

# Функция для создания нагрузки на CPU
def cpu_load_thread():
    global cpu_load, should_run
    logger.info("CPU load thread started")
    
    while should_run:
        try:
            if cpu_load > 0:
                start_time = time.time()
                # Выполняем интенсивные вычисления для загрузки CPU
                while time.time() - start_time < 0.1 and should_run:
                    _ = [i**2 for i in range(10000)]
                # Спим, чтобы достичь желаемого уровня загрузки
                if should_run and cpu_load < 100:
                    sleep_time = 0.1 * (100 - cpu_load) / cpu_load
                    time.sleep(min(sleep_time, 0.5))  # Ограничиваем максимальное время сна
            else:
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error in CPU load thread: {str(e)}")
            time.sleep(1)  # Пауза перед повторной попыткой

# Функция для создания нагрузки на память
def memory_load_thread():
    global memory_load_mb, should_run
    memory_data = []
    
    logger.info("Memory load thread started")
    
    # Параметры для контроля скорости роста памяти
    MAX_MEMORY_GROWTH_RATE = 10  # Максимальный рост в МБ в секунду (уменьшено с 20 до 10)
    memory_growth_factor = 0.05  # Замедление в 20 раз (1/20) (уменьшено с 0.1 до 0.05)
    last_allocation_time = time.time()
    last_memory_size = 0
    allocation_interval = 0.5  # Интервал между выделениями памяти в секундах (уменьшено с 1.0 до 0.5)
    
    while should_run:
        try:
            # Получаем информацию о системной памяти
            system_memory = psutil.virtual_memory()
            available_memory_mb = system_memory.available / (1024 * 1024)
            
            # Текущий размер используемой памяти нашим процессом в МБ
            current_size = sum(len(d) for d in memory_data) / (1024 * 1024)
            
            # Безопасный лимит памяти (чтобы предотвратить OOM killer)
            safe_limit_mb = system_memory.total * (MAX_MEMORY_PERCENT / 100) / (1024 * 1024)
            process_limit_mb = min(memory_load_mb, safe_limit_mb)
            
            logger.debug(f"Memory status: current={current_size:.1f}MB, target={process_limit_mb:.1f}MB, available={available_memory_mb:.1f}MB")
            
            current_time = time.time()
            if process_limit_mb > current_size and available_memory_mb > (process_limit_mb - current_size) * 1.2:
                # Проверяем прошло ли достаточно времени с последнего выделения памяти
                if current_time - last_allocation_time >= allocation_interval:
                    # Вычисляем максимально допустимый прирост памяти за этот интервал
                    time_since_last = current_time - last_allocation_time
                    max_allowed_growth = MAX_MEMORY_GROWTH_RATE * time_since_last
                    
                    # Увеличиваем использование памяти небольшими порциями
                    target_increment = min(
                        (process_limit_mb - current_size) * memory_growth_factor,
                        max_allowed_growth
                    )
                    
                    # Ограничиваем размер чанка до 5MB или меньше
                    chunk_size = min(5 * 1024 * 1024, int(target_increment * 1024 * 1024))
                    
                    if chunk_size > 0:
                        try:
                            memory_data.append('X' * chunk_size)
                            logger.debug(f"Allocated {chunk_size / (1024*1024):.1f}MB more memory")
                            last_allocation_time = current_time
                            last_memory_size = current_size
                        except MemoryError:
                            logger.warning("Memory allocation error - reached system limit")
                            time.sleep(2)
                else:
                    logger.debug(f"Waiting for allocation interval: {allocation_interval - (current_time - last_allocation_time):.1f}s remaining")
            elif memory_load_mb < current_size and memory_data:
                # Уменьшаем использование памяти
                memory_data.pop()
                logger.debug("Released memory chunk")
                last_allocation_time = current_time
                last_memory_size = current_size
            
            time.sleep(MEMORY_CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Error in memory load thread: {str(e)}")
            time.sleep(1)  # Пауза перед повторной попыткой

# Функция для мониторинга ресурсов
def resource_monitor_thread():
    while should_run:
        try:
            process = psutil.Process(os.getpid())
            current_memory = process.memory_info().rss / (1024 * 1024)
            current_cpu = psutil.cpu_percent(interval=0.1)
            
            logger.debug(f"Resource monitor: CPU={current_cpu:.1f}%, Memory={current_memory:.1f}MB")
            
            # Если мы близки к пределу доступной памяти, уменьшаем целевую память
            system_memory = psutil.virtual_memory()
            if system_memory.percent > 90:
                global memory_load_mb
                old_memory_load = memory_load_mb
                memory_load_mb = min(memory_load_mb, current_memory * 0.9)
                logger.warning(f"System memory pressure detected! Reducing target from {old_memory_load}MB to {memory_load_mb}MB")
                
            time.sleep(5)  # Проверяем каждые 5 секунд
        except Exception as e:
            logger.error(f"Error in resource monitor thread: {str(e)}")
            time.sleep(1)

# Запускаем потоки нагрузки
def start_threads():
    global cpu_thread, memory_thread, monitor_thread
    
    cpu_thread = threading.Thread(target=cpu_load_thread)
    memory_thread = threading.Thread(target=memory_load_thread)
    monitor_thread = threading.Thread(target=resource_monitor_thread)
    
    cpu_thread.daemon = True
    memory_thread.daemon = True
    monitor_thread.daemon = True
    
    cpu_thread.start()
    memory_thread.start()
    monitor_thread.start()
    
    logger.info("All resource management threads started")

# Запускаем все потоки при старте приложения
start_threads()

@app.route('/')
def index():
    return render_template('index.html', 
                          cpu_load=cpu_load, 
                          memory_load_mb=memory_load_mb)

@app.route('/update_resources', methods=['POST'])
def update_resources():
    global cpu_load, memory_load_mb
    
    try:
        new_cpu_load = int(request.form.get('cpu', 0))
        new_memory_load_mb = int(request.form.get('memory', 0))
        
        # Проверяем, что значения в допустимых пределах
        new_cpu_load = max(0, min(new_cpu_load, 100))
        new_memory_load_mb = max(0, min(new_memory_load_mb, 8 * 1024))  # Максимум 8GB
        
        logger.info(f"Resource update requested: CPU={new_cpu_load}%, Memory={new_memory_load_mb}MB")
        
        # Безопасно обновляем значения
        cpu_load = new_cpu_load
        
        # Если запрошенная память слишком велика, ограничиваем ее
        system_memory = psutil.virtual_memory()
        safe_limit_mb = system_memory.total * (MAX_MEMORY_PERCENT / 100) / (1024 * 1024)
        
        if new_memory_load_mb > safe_limit_mb:
            logger.warning(f"Requested memory {new_memory_load_mb}MB exceeds safe limit {safe_limit_mb:.1f}MB")
            memory_load_mb = safe_limit_mb
        else:
            memory_load_mb = new_memory_load_mb
        
        return jsonify({
            'status': 'success',
            'cpu_load': cpu_load,
            'memory_load_mb': memory_load_mb,
            'memory_load_gb': memory_load_mb / 1024
        })
    except Exception as e:
        logger.error(f"Error in update_resources: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/status')
def status():
    try:
        # Получаем текущие данные о ресурсах
        current_cpu = psutil.cpu_percent(interval=0.1)
        current_memory = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        
        # Информация о системных ресурсах
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=None)
        
        return jsonify({
            'current_cpu': current_cpu,
            'current_memory': current_memory,
            'current_memory_gb': current_memory / 1024,
            'target_cpu': cpu_load,
            'target_memory': memory_load_mb,
            'target_memory_gb': memory_load_mb / 1024,
            'system_memory_percent': system_memory.percent,
            'system_cpu_percent': system_cpu
        })
    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/healthz')
def health_check():
    # Простая проверка работоспособности для Kubernetes
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Запускаем на всех интерфейсах для работы в контейнере
    logger.info("Starting application server")
    app.run(host='0.0.0.0', port=5000) 