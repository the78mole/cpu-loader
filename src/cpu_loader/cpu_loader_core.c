#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
#include <stdbool.h>
#include <stdio.h>

#define CYCLE_TIME_NS 10000000L  // 10ms in nanoseconds for better responsiveness

// Computation types for busy-wait
typedef enum {
    COMPUTE_BUSY_WAIT = 0,
    COMPUTE_PI_CALCULATION = 1,
    COMPUTE_PRIME_NUMBERS = 2,
    COMPUTE_MATRIX_MULTIPLY = 3,
    COMPUTE_FIBONACCI = 4
} ComputationType;

typedef struct {
    pthread_t thread;
    int thread_id;
    double load;  // 0.0 to 1.0
    bool running;
    bool stop;
    ComputationType compute_type;
    pthread_mutex_t lock;
} WorkerThread;

static WorkerThread *workers = NULL;
static int num_threads = 0;
static ComputationType global_compute_type = COMPUTE_BUSY_WAIT;
static pthread_mutex_t global_lock = PTHREAD_MUTEX_INITIALIZER;

// High-resolution timer
static inline long long get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

// Time-controlled PI calculation using Leibniz formula
static void calculate_pi_timed(long long duration_ns) {
    long long start = get_time_ns();
    double pi = 0.0;
    int i = 0;

    // Check time every 100 iterations for better responsiveness
    while ((get_time_ns() - start) < duration_ns) {
        for (int batch = 0; batch < 100 && (get_time_ns() - start) < duration_ns; batch++) {
            pi += (i % 2 == 0 ? 1.0 : -1.0) / (2 * i + 1);
            i++;
        }
    }
}

// Prime number checking (time-controlled)
static bool is_prime_quick(long long n) {
    if (n < 2) return false;
    if (n == 2) return true;
    if (n % 2 == 0) return false;

    for (long long i = 3; i * i <= n; i += 2) {
        if (n % i == 0) return false;
    }
    return true;
}

// Time-controlled prime number finding
static void find_primes_timed(long long duration_ns) {
    long long start = get_time_ns();
    long long n = 1000; // Start from a reasonable number

    while ((get_time_ns() - start) < duration_ns) {
        // Process numbers one by one with frequent time checks
        is_prime_quick(n);
        n++;
        if (n > 100000) n = 1000; // Reset to avoid overflow

        // Check time more frequently for better control
        if ((n % 50) == 0 && (get_time_ns() - start) >= duration_ns) {
            break;
        }
    }
}

// Simple matrix multiplication (4x4 matrices) - time controlled
static void matrix_multiply_timed(long long duration_ns) {
    long long start = get_time_ns();
    double a[4][4] = {{1,2,3,4},{5,6,7,8},{9,10,11,12},{13,14,15,16}};
    double b[4][4] = {{16,15,14,13},{12,11,10,9},{8,7,6,5},{4,3,2,1}};
    double result[4][4];

    while ((get_time_ns() - start) < duration_ns) {
        // Perform matrix multiplication with frequent time checks
        for (int i = 0; i < 4; i++) {
            for (int j = 0; j < 4; j++) {
                result[i][j] = 0;
                for (int k = 0; k < 4; k++) {
                    result[i][j] += a[i][k] * b[k][j];
                }
                // Check time after each element calculation
                if ((get_time_ns() - start) >= duration_ns) {
                    return;
                }
            }
        }
        // Vary matrices slightly to prevent optimization
        a[0][0] = result[0][0] / 1000000.0;
    }
}

// Time-controlled lightweight computational work (simplified approach)
static void fibonacci_timed(long long duration_ns) {
    long long start = get_time_ns();
    volatile double result = 0.0; // Use volatile to prevent optimization
    int counter = 0;

    while ((get_time_ns() - start) < duration_ns) {
        // Perform lightweight mathematical operations
        for (int i = 0; i < 100 && (get_time_ns() - start) < duration_ns; i++) {
            result += counter * 1.1 + 0.5;
            counter = (counter + 1) % 1000;
        }

        // Small computational pause
        struct timespec tiny_pause = {0, 5000}; // 5 microseconds
        nanosleep(&tiny_pause, NULL);
    }
}

// Perform computation based on type for specified duration
static void perform_computation(ComputationType type, long long duration_ns) {
    switch (type) {
        case COMPUTE_PI_CALCULATION:
            calculate_pi_timed(duration_ns);
            break;

        case COMPUTE_PRIME_NUMBERS:
            find_primes_timed(duration_ns);
            break;

        case COMPUTE_MATRIX_MULTIPLY:
            matrix_multiply_timed(duration_ns);
            break;

        case COMPUTE_FIBONACCI:
            fibonacci_timed(duration_ns);
            break;

        case COMPUTE_BUSY_WAIT:
        default:
            // Original busy-wait implementation
            {
                long long start = get_time_ns();
                while ((get_time_ns() - start) < duration_ns) {
                    // Busy loop
                }
            }
            break;
    }
}

// Busy-wait for specified nanoseconds (backward compatibility)
static inline void busy_wait_ns(long long ns) {
    perform_computation(COMPUTE_BUSY_WAIT, ns);
}

static void *worker_thread(void *arg) {
    WorkerThread *worker = (WorkerThread *)arg;

    while (!worker->stop) {
        long long cycle_start = get_time_ns();

        pthread_mutex_lock(&worker->lock);
        double load = worker->load;
        ComputationType compute_type = worker->compute_type;
        pthread_mutex_unlock(&worker->lock);

        if (load <= 0.0) {
            // No load, sleep for the full cycle
            struct timespec sleep_time = {0, CYCLE_TIME_NS};
            nanosleep(&sleep_time, NULL);
        } else if (load >= 1.0) {
            // 100% load, perform computation for the entire cycle
            perform_computation(compute_type, CYCLE_TIME_NS);
        } else {
            // Partial load
            long long work_time_ns = (long long)(load * CYCLE_TIME_NS);

            // Perform computation for work time
            perform_computation(compute_type, work_time_ns);

            // Sleep for the rest of the cycle
            long long elapsed = get_time_ns() - cycle_start;
            long long remaining = CYCLE_TIME_NS - elapsed;

            if (remaining > 1000000) {  // > 1ms
                // Sleep for most of the remaining time
                struct timespec sleep_time;
                sleep_time.tv_sec = remaining / 1000000000L;
                sleep_time.tv_nsec = remaining % 1000000000L;
                nanosleep(&sleep_time, NULL);
            }
        }
    }

    return NULL;
}

// Initialize the CPU loader with specified number of threads
static PyObject *init_loader(PyObject *self, PyObject *args) {
    int new_num_threads;

    if (!PyArg_ParseTuple(args, "i", &new_num_threads)) {
        return NULL;
    }

    if (new_num_threads <= 0) {
        PyErr_SetString(PyExc_ValueError, "Number of threads must be positive");
        return NULL;
    }

    pthread_mutex_lock(&global_lock);

    // Stop existing threads if any
    if (workers != NULL) {
        for (int i = 0; i < num_threads; i++) {
            workers[i].stop = true;
        }
        for (int i = 0; i < num_threads; i++) {
            pthread_join(workers[i].thread, NULL);
            pthread_mutex_destroy(&workers[i].lock);
        }
        free(workers);
    }

    // Allocate new workers
    num_threads = new_num_threads;
    workers = calloc(num_threads, sizeof(WorkerThread));

    // Start threads
    for (int i = 0; i < num_threads; i++) {
        workers[i].thread_id = i;
        workers[i].load = 0.0;
        workers[i].running = false;
        workers[i].stop = false;
        workers[i].compute_type = global_compute_type;
        pthread_mutex_init(&workers[i].lock, NULL);

        if (pthread_create(&workers[i].thread, NULL, worker_thread, &workers[i]) != 0) {
            pthread_mutex_unlock(&global_lock);
            PyErr_SetString(PyExc_RuntimeError, "Failed to create thread");
            return NULL;
        }
        workers[i].running = true;
    }

    pthread_mutex_unlock(&global_lock);

    Py_RETURN_NONE;
}

// Set load for a specific thread
static PyObject *set_thread_load(PyObject *self, PyObject *args) {
    int thread_id;
    double load_percent;

    if (!PyArg_ParseTuple(args, "id", &thread_id, &load_percent)) {
        return NULL;
    }

    pthread_mutex_lock(&global_lock);

    if (thread_id < 0 || thread_id >= num_threads) {
        pthread_mutex_unlock(&global_lock);
        PyErr_SetString(PyExc_ValueError, "Invalid thread ID");
        return NULL;
    }

    if (load_percent < 0.0 || load_percent > 100.0) {
        pthread_mutex_unlock(&global_lock);
        PyErr_SetString(PyExc_ValueError, "Load must be between 0 and 100");
        return NULL;
    }

    pthread_mutex_lock(&workers[thread_id].lock);
    workers[thread_id].load = load_percent / 100.0;
    pthread_mutex_unlock(&workers[thread_id].lock);

    pthread_mutex_unlock(&global_lock);

    Py_RETURN_NONE;
}

// Get load for a specific thread
static PyObject *get_thread_load(PyObject *self, PyObject *args) {
    int thread_id;

    if (!PyArg_ParseTuple(args, "i", &thread_id)) {
        return NULL;
    }

    pthread_mutex_lock(&global_lock);

    if (thread_id < 0 || thread_id >= num_threads) {
        pthread_mutex_unlock(&global_lock);
        PyErr_SetString(PyExc_ValueError, "Invalid thread ID");
        return NULL;
    }

    pthread_mutex_lock(&workers[thread_id].lock);
    double load = workers[thread_id].load * 100.0;
    pthread_mutex_unlock(&workers[thread_id].lock);

    pthread_mutex_unlock(&global_lock);

    return PyFloat_FromDouble(load);
}

// Get all thread loads
static PyObject *get_all_loads(PyObject *self, PyObject *args) {
    pthread_mutex_lock(&global_lock);

    PyObject *dict = PyDict_New();
    for (int i = 0; i < num_threads; i++) {
        pthread_mutex_lock(&workers[i].lock);
        double load = workers[i].load * 100.0;
        pthread_mutex_unlock(&workers[i].lock);

        PyObject *key = PyLong_FromLong(i);
        PyObject *value = PyFloat_FromDouble(load);
        PyDict_SetItem(dict, key, value);
        Py_DECREF(key);
        Py_DECREF(value);
    }

    pthread_mutex_unlock(&global_lock);

    return dict;
}

// Get number of threads
static PyObject *get_num_threads(PyObject *self, PyObject *args) {
    pthread_mutex_lock(&global_lock);
    int n = num_threads;
    pthread_mutex_unlock(&global_lock);

    return PyLong_FromLong(n);
}

// Set computation type
static PyObject *set_computation_type(PyObject *self, PyObject *args) {
    int comp_type;

    if (!PyArg_ParseTuple(args, "i", &comp_type)) {
        return NULL;
    }

    if (comp_type < 0 || comp_type > COMPUTE_FIBONACCI) {
        PyErr_SetString(PyExc_ValueError, "Invalid computation type");
        return NULL;
    }

    pthread_mutex_lock(&global_lock);
    global_compute_type = (ComputationType)comp_type;

    // Update all existing workers
    for (int i = 0; i < num_threads; i++) {
        pthread_mutex_lock(&workers[i].lock);
        workers[i].compute_type = global_compute_type;
        pthread_mutex_unlock(&workers[i].lock);
    }

    pthread_mutex_unlock(&global_lock);

    Py_RETURN_NONE;
}

// Get computation type
static PyObject *get_computation_type(PyObject *self, PyObject *args) {
    pthread_mutex_lock(&global_lock);
    int comp_type = (int)global_compute_type;
    pthread_mutex_unlock(&global_lock);

    return PyLong_FromLong(comp_type);
}

// Shutdown all threads
static PyObject *shutdown_loader(PyObject *self, PyObject *args) {
    pthread_mutex_lock(&global_lock);

    if (workers != NULL) {
        for (int i = 0; i < num_threads; i++) {
            workers[i].stop = true;
        }
        for (int i = 0; i < num_threads; i++) {
            pthread_join(workers[i].thread, NULL);
            pthread_mutex_destroy(&workers[i].lock);
        }
        free(workers);
        workers = NULL;
        num_threads = 0;
    }

    pthread_mutex_unlock(&global_lock);

    Py_RETURN_NONE;
}

// Method definitions
static PyMethodDef CoreMethods[] = {
    {"init_loader", init_loader, METH_VARARGS, "Initialize the CPU loader"},
    {"set_thread_load", set_thread_load, METH_VARARGS, "Set load for a thread"},
    {"get_thread_load", get_thread_load, METH_VARARGS, "Get load for a thread"},
    {"get_all_loads", get_all_loads, METH_NOARGS, "Get all thread loads"},
    {"get_num_threads", get_num_threads, METH_NOARGS, "Get number of threads"},
    {"set_computation_type", set_computation_type, METH_VARARGS, "Set computation type"},
    {"get_computation_type", get_computation_type, METH_NOARGS, "Get computation type"},
    {"shutdown", shutdown_loader, METH_NOARGS, "Shutdown the CPU loader"},
    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef coremodule = {
    PyModuleDef_HEAD_INIT,
    "cpu_loader_core",
    "CPU loader core implementation in C",
    -1,
    CoreMethods
};

// Module initialization
PyMODINIT_FUNC PyInit_cpu_loader_core(void) {
    return PyModule_Create(&coremodule);
}
