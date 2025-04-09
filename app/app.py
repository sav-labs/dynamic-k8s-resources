import os
import time
import threading
import logging
from flask import Flask, render_template, jsonify
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables to store memory data and settings
memory_data = []
memory_increment_mb = int(os.environ.get('MEMORY_INCREMENT_MB', 10))  # Default to 10MB/sec
should_run = True

# Function to increase memory usage by a specific amount every second
def memory_increment_thread():
    global memory_data, should_run, memory_increment_mb
    
    logger.info(f"Memory increment thread started with {memory_increment_mb}MB per second")
    
    while should_run:
        try:
            # Create a chunk of exactly memory_increment_mb megabytes
            chunk_size = memory_increment_mb * 1024 * 1024
            memory_data.append('X' * chunk_size)
            
            # Log current memory usage
            current_usage = sum(len(d) for d in memory_data) / (1024 * 1024)
            logger.info(f"Memory increased by {memory_increment_mb}MB. Total usage: {current_usage:.2f}MB")
            
            # Sleep for exactly 1 second
            time.sleep(1)
            
        except MemoryError:
            logger.error("Memory allocation error - reached system limit")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error in memory increment thread: {str(e)}")
            time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html', memory_increment_mb=memory_increment_mb)

@app.route('/status')
def status():
    try:
        # Get current process resource info
        process = psutil.Process(os.getpid())
        current_memory = process.memory_info().rss / (1024 * 1024)
        current_cpu = psutil.cpu_percent(interval=0.1)
        
        # System resource info
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=None)
        
        return jsonify({
            'current_memory': current_memory,
            'current_memory_gb': current_memory / 1024,
            'system_memory_percent': system_memory.percent,
            'system_memory_available_gb': system_memory.available / (1024 * 1024 * 1024),
            'system_memory_total_gb': system_memory.total / (1024 * 1024 * 1024),
            'current_cpu': current_cpu,
            'system_cpu': system_cpu,
            'memory_increment_mb': memory_increment_mb
        })
    except Exception as e:
        logger.error(f"Error in status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/healthz')
def health_check():
    # Simple health check for Kubernetes
    return jsonify({'status': 'ok'})

# Start memory increment thread when app starts
memory_thread = threading.Thread(target=memory_increment_thread)
memory_thread.daemon = True
memory_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False) 