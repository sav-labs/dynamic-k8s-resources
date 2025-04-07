import os
import psutil
import time
import threading
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Глобальные переменные для хранения настроек ресурсов
cpu_load = 0
memory_load_mb = 0

# Флаг для управления нагрузочными потоками
should_run = True

# Функция для создания нагрузки на CPU
def cpu_load_thread():
    global cpu_load, should_run
    while should_run:
        if cpu_load > 0:
            start_time = time.time()
            # Выполняем интенсивные вычисления для загрузки CPU
            while time.time() - start_time < 0.1:
                _ = [i**2 for i in range(10000)]
            # Спим, чтобы достичь желаемого уровня загрузки
            time.sleep(0.1 * (100 - cpu_load) / cpu_load) if cpu_load < 100 else 0
        else:
            time.sleep(0.5)

# Функция для создания нагрузки на память
def memory_load_thread():
    global memory_load_mb, should_run
    memory_data = []
    
    while should_run:
        # Текущий размер используемой памяти в МБ
        current_size = sum(len(d) for d in memory_data) / (1024 * 1024)
        
        if memory_load_mb > current_size:
            # Увеличиваем использование памяти
            # Пытаемся выделить примерно 10 МБ за раз для более плавного увеличения
            chunk_size = min(10 * 1024 * 1024, int((memory_load_mb - current_size) * 1024 * 1024))
            if chunk_size > 0:
                try:
                    memory_data.append('X' * chunk_size)
                except MemoryError:
                    print("Достигнут предел памяти")
        elif memory_load_mb < current_size and memory_data:
            # Уменьшаем использование памяти
            memory_data.pop()
        
        time.sleep(0.5)

# Запускаем потоки нагрузки
cpu_thread = threading.Thread(target=cpu_load_thread)
memory_thread = threading.Thread(target=memory_load_thread)
cpu_thread.daemon = True
memory_thread.daemon = True
cpu_thread.start()
memory_thread.start()

@app.route('/')
def index():
    return render_template('index.html', 
                          cpu_load=cpu_load, 
                          memory_load_mb=memory_load_mb)

@app.route('/update_resources', methods=['POST'])
def update_resources():
    global cpu_load, memory_load_mb
    
    cpu_load = int(request.form.get('cpu', 0))
    memory_load_mb = int(request.form.get('memory', 0))
    
    return jsonify({
        'status': 'success',
        'cpu_load': cpu_load,
        'memory_load_mb': memory_load_mb,
        'memory_load_gb': memory_load_mb / 1024
    })

@app.route('/status')
def status():
    # Получаем текущие данные о ресурсах
    current_cpu = psutil.cpu_percent(interval=0.5)
    current_memory = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    
    return jsonify({
        'current_cpu': current_cpu,
        'current_memory': current_memory,
        'current_memory_gb': current_memory / 1024,
        'target_cpu': cpu_load,
        'target_memory': memory_load_mb,
        'target_memory_gb': memory_load_mb / 1024
    })

if __name__ == '__main__':
    # Запускаем на всех интерфейсах для работы в контейнере
    app.run(host='0.0.0.0', port=5000, debug=True) 