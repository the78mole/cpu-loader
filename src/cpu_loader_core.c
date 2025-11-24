#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
#include <stdbool.h>
#include <stdio.h>

#define CYCLE_TIME_NS 100000000L  // 100ms in nanoseconds

typedef struct {
    pthread_t thread;
    int thread_id;
    double load;  // 0.0 to 1.0
    bool running;
    bool stop;
    pthread_mutex_t lock;
} WorkerThread;

static WorkerThread *workers = NULL;
static int num_threads = 0;
static pthread_mutex_t global_lock = PTHREAD_MUTEX_INITIALIZER;

// High-resolution timer
static inline long long get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

// Busy-wait for specified nanoseconds
static inline void busy_wait_ns(long long ns) {
    long long start = get_time_ns();
    while ((get_time_ns() - start) < ns) {
        // Busy loop
    }
}

static void *worker_thread(void *arg) {
    WorkerThread *worker = (WorkerThread *)arg;

    while (!worker->stop) {
        long long cycle_start = get_time_ns();

        pthread_mutex_lock(&worker->lock);
        double load = worker->load;
        pthread_mutex_unlock(&worker->lock);

        if (load <= 0.0) {
            // No load, sleep for the full cycle
            struct timespec sleep_time = {0, CYCLE_TIME_NS};
            nanosleep(&sleep_time, NULL);
        } else if (load >= 1.0) {
            // 100% load, busy-wait for the entire cycle
            busy_wait_ns(CYCLE_TIME_NS);
        } else {
            // Partial load
            long long work_time_ns = (long long)(load * CYCLE_TIME_NS);

            // Busy-wait for work time
            busy_wait_ns(work_time_ns);

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
