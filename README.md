# CPU Loader

A tool to generate CPU load on a system with runtime configuration through a WebUI and REST API.

## Features

- 🔥 **Controllable CPU Load**: Generate precise CPU load per thread
- 🎛️ **Per-Thread Control**: Individual sliders for each CPU thread
- 🚀 **REST API**: Full programmatic control via HTTP endpoints
- 🌐 **Modern WebUI**: Beautiful, responsive interface for real-time control
- ⚡ **Instant Response**: Changes take effect immediately
- 📊 **Live Monitoring**: View active threads and average load in real-time

## Screenshots

### WebUI Interface
![CPU Loader Control - 25% Load](https://github.com/user-attachments/assets/94f5a1a1-4328-46af-9155-e7d50cc8ba0e)
*Individual thread control with sliders and preset buttons*

![CPU Loader Control - 50% Load](https://github.com/user-attachments/assets/bcab1f61-03a6-48ea-83b7-4402ec0d1389)
*Setting all threads to 50% load*

![CPU Loader Control - 100% Load](https://github.com/user-attachments/assets/542afa1c-16da-4aff-a021-1e905e6f3372)
*Maximum load across all threads*

## Installation

1. Clone the repository:
```bash
git clone https://github.com/the78mole/cpu-loader.git
cd cpu-loader
```

2. Install dependencies and build C extension:
```bash
uv pip install -e .
```

This will compile the high-performance C extension for efficient CPU load generation.

3. (Optional) Set up pre-commit hooks for development:
```bash
pre-commit install
```

## Usage

### Starting the Server

```bash
uv run src/main.py
```

The server will start on `http://localhost:8000`

### WebUI

Open your browser and navigate to `http://localhost:8000`

**Features:**
- **Individual Thread Control**: Use sliders to set load for each thread (0-100%)
- **Preset Buttons**: Quick-set all threads to 0%, 10%, 25%, 50%, 80%, 90%, or 100%
- **Live Stats**: View active thread count and average load
- **Real-time Updates**: Changes are applied instantly with visual feedback

### REST API

#### Get Thread Status
```bash
curl http://localhost:8000/api/threads
```

Response:
```json
{
  "num_threads": 4,
  "loads": {
    "0": 0.0,
    "1": 0.0,
    "2": 0.0,
    "3": 0.0
  }
}
```

#### Set Load for Specific Thread
```bash
curl -X PUT http://localhost:8000/api/threads/0/load \
  -H "Content-Type: application/json" \
  -d '{"load_percent": 50.0}'
```

#### Set Load for All Threads
```bash
curl -X POST http://localhost:8000/api/threads/load/all \
  -H "Content-Type: application/json" \
  -d '{"load_percent": 75.0}'
```

#### Change Number of Threads
```bash
curl -X POST http://localhost:8000/api/threads \
  -H "Content-Type: application/json" \
  -d '{"num_threads": 8}'
```

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI.

## Example Script

An example script (`src/example.py`) is provided to demonstrate programmatic control:

```bash
# Start the server first
uv run src/main.py

# In another terminal, run the example
uv run src/example.py
```

The example demonstrates:
- Getting current status
- Setting all threads to a specific load
- Gradually increasing load
- Individual thread control
- Resetting to idle

## Architecture

- **src/cpu_loader_core.c**: High-performance C implementation using pthreads for CPU load generation
- **src/cpu_loader.py**: Python wrapper providing a clean API to the C extension
- **src/main.py**: FastAPI application with REST API and embedded WebUI
- **Threading Model**: Native pthreads for maximum efficiency and precise timing
- **Load Algorithm**: High-resolution busy-wait loops with nanosecond precision

## Requirements

- Python 3.8+
- FastAPI 0.115.0+
- Uvicorn 0.32.0+
- Pydantic 2.10.0+
- C compiler (gcc or clang) for building the extension

## Use Cases

- **Performance Testing**: Test application behavior under various CPU loads
- **Stress Testing**: Validate system stability under high CPU utilization
- **Thermal Testing**: Check cooling system effectiveness
- **Power Consumption Analysis**: Measure power usage at different load levels
- **Benchmarking**: Create reproducible load scenarios

## Development

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. The hooks include:

- **Code Formatting**: Black and isort for consistent Python formatting
- **Linting**: Flake8 for code quality checks
- **Type Checking**: Mypy for static type analysis
- **General Checks**: Trailing whitespace, end-of-file fixes, YAML/JSON/TOML validation

To run pre-commit manually on all files:
```bash
pre-commit run --all-files
```

The hooks will run automatically on `git commit` after installation.

## License

This project is provided as-is for testing and development purposes.
