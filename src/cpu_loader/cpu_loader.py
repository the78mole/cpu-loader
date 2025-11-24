"""
CPU Loader Module
Provides CPU load generation with controllable load per thread.
Uses a C extension for efficient CPU load generation.
"""
import multiprocessing
from typing import Dict

try:
    from cpu_loader import cpu_loader_core  # type: ignore[attr-defined]
except ImportError:
    raise ImportError(
        "cpu_loader_core module not found. Please build the C extension with: "
        "uv pip install -e ."
    )


class CPULoader:
    """Manages CPU load generation across multiple threads using C extension."""

    def __init__(self, num_threads: int = None):
        """
        Initialize the CPU loader.

        Args:
            num_threads: Number of threads to use. Defaults to CPU count.
        """
        if num_threads is None:
            num_threads = multiprocessing.cpu_count()

        self.num_threads = num_threads
        cpu_loader_core.init_loader(num_threads)

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

        cpu_loader_core.set_thread_load(thread_id, load_percent)

    def set_all_loads(self, load_percent: float):
        """
        Set the same CPU load for all threads.

        Args:
            load_percent: Load percentage (0.0 to 100.0)
        """
        if load_percent < 0 or load_percent > 100:
            raise ValueError("Load percent must be between 0 and 100")

        for thread_id in range(self.num_threads):
            cpu_loader_core.set_thread_load(thread_id, load_percent)

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

        return cpu_loader_core.get_thread_load(thread_id)

    def get_all_loads(self) -> Dict[int, float]:
        """
        Get the current load settings for all threads.

        Returns:
            Dictionary mapping thread ID to load percentage (0.0 to 100.0)
        """
        return cpu_loader_core.get_all_loads()

    def get_num_threads(self) -> int:
        """Get the number of threads."""
        return cpu_loader_core.get_num_threads()

    def set_num_threads(self, num_threads: int):
        """
        Change the number of threads.

        Args:
            num_threads: New number of threads
        """
        if num_threads <= 0:
            raise ValueError("Number of threads must be positive")

        self.num_threads = num_threads
        cpu_loader_core.init_loader(num_threads)

    def shutdown(self):
        """Shutdown all threads."""
        cpu_loader_core.shutdown()
