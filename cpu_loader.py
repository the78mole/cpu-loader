"""
CPU Loader Module
Provides CPU load generation with controllable load per thread.
"""
import threading
import time
import multiprocessing
from typing import Dict, List


class CPULoader:
    """Manages CPU load generation across multiple threads."""
    
    def __init__(self, num_threads: int = None):
        """
        Initialize the CPU loader.
        
        Args:
            num_threads: Number of threads to use. Defaults to CPU count.
        """
        if num_threads is None:
            num_threads = multiprocessing.cpu_count()
        
        self.num_threads = num_threads
        self.threads: List[threading.Thread] = []
        self.thread_loads: Dict[int, float] = {i: 0.0 for i in range(num_threads)}
        self.stop_flags: Dict[int, threading.Event] = {i: threading.Event() for i in range(num_threads)}
        self.lock = threading.Lock()
        
        # Start all threads
        for i in range(num_threads):
            thread = threading.Thread(target=self._worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
    
    def _worker(self, thread_id: int):
        """
        Worker thread that generates CPU load.
        
        Args:
            thread_id: ID of the thread
        """
        while not self.stop_flags[thread_id].is_set():
            load = self.thread_loads[thread_id]
            
            if load <= 0:
                # No load, just sleep
                time.sleep(0.1)
            else:
                # Generate load using busy waiting
                # load is the fractional value (0.0 to 1.0) representing the percentage (0% to 100%)
                work_time = load * 0.1  # Work for this fraction of 100ms
                sleep_time = (1.0 - load) * 0.1  # Sleep for the rest
                
                if work_time > 0:
                    start = time.time()
                    # Busy loop to generate CPU load
                    while time.time() - start < work_time:
                        pass
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
    def set_thread_load(self, thread_id: int, load_percent: float):
        """
        Set the CPU load for a specific thread.
        
        Args:
            thread_id: ID of the thread (0 to num_threads-1)
            load_percent: Load percentage (0.0 to 100.0)
        """
        if thread_id < 0 or thread_id >= self.num_threads:
            raise ValueError(f"Thread ID must be between 0 and {self.num_threads - 1}")
        
        if load_percent < 0 or load_percent > 100:
            raise ValueError("Load percent must be between 0 and 100")
        
        with self.lock:
            self.thread_loads[thread_id] = load_percent / 100.0
    
    def set_all_loads(self, load_percent: float):
        """
        Set the same CPU load for all threads.
        
        Args:
            load_percent: Load percentage (0.0 to 100.0)
        """
        if load_percent < 0 or load_percent > 100:
            raise ValueError("Load percent must be between 0 and 100")
        
        with self.lock:
            for thread_id in range(self.num_threads):
                self.thread_loads[thread_id] = load_percent / 100.0
    
    def get_thread_load(self, thread_id: int) -> float:
        """
        Get the current load setting for a specific thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            Load percentage (0.0 to 100.0)
        """
        if thread_id < 0 or thread_id >= self.num_threads:
            raise ValueError(f"Thread ID must be between 0 and {self.num_threads - 1}")
        
        with self.lock:
            return self.thread_loads[thread_id] * 100.0
    
    def get_all_loads(self) -> Dict[int, float]:
        """
        Get the current load settings for all threads.
        
        Returns:
            Dictionary mapping thread ID to load percentage (0.0 to 100.0)
        """
        with self.lock:
            return {tid: load * 100.0 for tid, load in self.thread_loads.items()}
    
    def get_num_threads(self) -> int:
        """Get the number of threads."""
        return self.num_threads
    
    def set_num_threads(self, num_threads: int):
        """
        Change the number of threads.
        
        Args:
            num_threads: New number of threads
        """
        if num_threads <= 0:
            raise ValueError("Number of threads must be positive")
        
        # Stop existing threads
        for thread_id in range(self.num_threads):
            self.stop_flags[thread_id].set()
        
        # Wait for threads to finish with longer timeout and verification
        for thread in self.threads:
            thread.join(timeout=2.0)
            if thread.is_alive():
                # Thread didn't stop cleanly, but since it's a daemon, it will be terminated
                pass
        
        # Reset state
        self.num_threads = num_threads
        self.threads = []
        self.thread_loads = {i: 0.0 for i in range(num_threads)}
        self.stop_flags = {i: threading.Event() for i in range(num_threads)}
        
        # Start new threads
        for i in range(num_threads):
            thread = threading.Thread(target=self._worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
    
    def shutdown(self):
        """Shutdown all threads."""
        for thread_id in range(self.num_threads):
            self.stop_flags[thread_id].set()
        
        # Wait for all threads to finish with verification
        for thread in self.threads:
            thread.join(timeout=2.0)
            if thread.is_alive():
                # Thread didn't stop cleanly, but since it's a daemon, it will be terminated
                pass
