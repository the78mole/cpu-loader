"""
CPU Loader FastAPI Application
Provides REST API and WebUI for controlling CPU load.
"""

import argparse
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional, Set

import psutil
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cpu_loader.cpu_loader import CPULoader
from cpu_loader.mqtt_publisher import MQTTPublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class ThreadLoadRequest(BaseModel):
    load_percent: float = Field(
        ..., ge=0, le=100, description="Load percentage (0-100)"
    )


class AllThreadsLoadRequest(BaseModel):
    load_percent: float = Field(
        ..., ge=0, le=100, description="Load percentage (0-100)"
    )


class ThreadCountRequest(BaseModel):
    num_threads: int = Field(
        ..., gt=0, description="Number of threads (must be positive)"
    )


class ThreadsStatusResponse(BaseModel):
    num_threads: int
    loads: Dict[int, float]


class CPUMetricsResponse(BaseModel):
    total_cpu_percent: float
    per_cpu_percent: List[float]
    cpu_temperature: Optional[float] = None


class ComputationTypeRequest(BaseModel):
    computation_type: str = Field(
        ..., description="Computation type: busy-wait, pi, primes, matrix, fibonacci"
    )


class ComputationTypeResponse(BaseModel):
    computation_type: str
    available_types: List[str]


# Global CPU loader instance, MQTT publisher, and WebSocket connections
cpu_loader = None
mqtt_publisher: Optional[MQTTPublisher] = None
websocket_connections: Set[WebSocket] = set()
monitoring_task = None
temperature_monitoring_enabled = True
temperature_monitoring_enabled = True


def get_cpu_temperature() -> Optional[float]:
    """Get CPU temperature if available and enabled."""
    if not temperature_monitoring_enabled:
        return None

    try:
        # Try to get CPU temperature using psutil
        temperatures = psutil.sensors_temperatures()

        # Common temperature sensor names to check
        temp_names = ["coretemp", "cpu_thermal", "acpi", "k8temp", "k10temp"]

        for temp_name in temp_names:
            if temp_name in temperatures:
                # Get the first temperature reading
                temp_list = temperatures[temp_name]
                if temp_list:
                    return round(temp_list[0].current, 1)

        # If no specific sensor found, try the first available
        for sensor_name, temp_list in temperatures.items():
            if temp_list:
                return round(temp_list[0].current, 1)

    except (AttributeError, OSError, ImportError):
        # Temperature monitoring not available on this system
        pass

    return None


async def cpu_monitoring_loop():
    """Background task that monitors CPU usage and broadcasts to all WebSocket clients."""
    # Initialize psutil
    psutil.cpu_percent(interval=None, percpu=True)

    while True:
        try:
            # Wait for 1 second
            await asyncio.sleep(1.0)

            # Get CPU metrics (non-blocking after first call)
            per_cpu = psutil.cpu_percent(interval=None, percpu=True)
            total_cpu = sum(per_cpu) / len(per_cpu) if per_cpu else 0.0

            # Get CPU temperature if available
            cpu_temp = get_cpu_temperature()

            # Prepare message
            message = {
                "type": "cpu_metrics",
                "total_cpu_percent": round(total_cpu, 1),
                "per_cpu_percent": [round(cpu, 1) for cpu in per_cpu],
                "cpu_temperature": cpu_temp,
            }

            # Broadcast to all connected clients
            if websocket_connections:
                disconnected = set()
                for websocket in websocket_connections:
                    try:
                        await websocket.send_json(message)
                    except Exception:
                        disconnected.add(websocket)

                # Remove disconnected clients
                websocket_connections.difference_update(disconnected)

            # Publish to MQTT if enabled
            if mqtt_publisher:
                mqtt_publisher.publish_cpu_metrics(total_cpu, per_cpu, cpu_temp)

        except Exception as e:
            logger.error(f"Error in CPU monitoring loop: {e}")
            await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global cpu_loader, mqtt_publisher, monitoring_task
    # Startup
    cpu_loader = CPULoader()

    # Set computation type if specified in app state
    computation_type = getattr(app.state, "computation_type", None)
    if computation_type:
        cpu_loader.set_computation_type_from_string(computation_type)

    # Initialize MQTT publisher with settings from arguments or environment
    mqtt_args = getattr(app.state, "mqtt_args", {})
    try:
        mqtt_publisher = MQTTPublisher(**mqtt_args)
    except ImportError:
        logger.warning("MQTT publishing disabled: paho-mqtt not installed")
        mqtt_publisher = None
    except Exception as e:
        logger.error(f"Failed to initialize MQTT publisher: {e}")
        mqtt_publisher = None

    monitoring_task = asyncio.create_task(cpu_monitoring_loop())
    yield
    # Shutdown
    if monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
    if mqtt_publisher:
        mqtt_publisher.disconnect()
    cpu_loader.shutdown()


# Initialize FastAPI app
app = FastAPI(
    title="CPU Loader API",
    description="Control CPU load generation with configurable threads",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/favicon.ico")
async def get_favicon():
    """Serve the favicon."""
    favicon_path = Path(__file__).parent / "static" / "favicon.svg"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/svg+xml")
    else:
        raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/", response_class=HTMLResponse)
async def get_webui():
    """Serve the WebUI."""
    from pathlib import Path

    template_path = Path(__file__).parent / "templates" / "index.html"
    html_content = template_path.read_text()
    return HTMLResponse(content=html_content)


@app.get("/api/threads", response_model=ThreadsStatusResponse)
async def get_threads_status():
    """Get the current status of all threads."""
    return ThreadsStatusResponse(
        num_threads=cpu_loader.get_num_threads(), loads=cpu_loader.get_all_loads()
    )


@app.websocket("/ws/cpu-metrics")
async def websocket_cpu_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time CPU metrics."""
    await websocket.accept()
    websocket_connections.add(websocket)
    try:
        # Keep connection alive
        while True:
            # Wait for any message (ping/pong)
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.discard(websocket)
    except Exception:
        websocket_connections.discard(websocket)


@app.get("/api/cpu-metrics", response_model=CPUMetricsResponse)
async def get_cpu_metrics():
    """Get current CPU utilization metrics."""
    per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
    total_cpu = psutil.cpu_percent(interval=0)
    cpu_temp = get_cpu_temperature()
    return CPUMetricsResponse(
        total_cpu_percent=total_cpu, per_cpu_percent=per_cpu, cpu_temperature=cpu_temp
    )


@app.post("/api/threads")
async def set_thread_count(request: ThreadCountRequest):
    """Set the number of threads."""
    try:
        cpu_loader.set_num_threads(request.num_threads)

        # Publish updated settings to MQTT
        if mqtt_publisher:
            mqtt_publisher.publish_load_settings(
                cpu_loader.get_num_threads(), cpu_loader.get_all_loads()
            )

        return {
            "status": "success",
            "num_threads": request.num_threads,
            "message": f"Thread count set to {request.num_threads}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/threads/{thread_id}/load")
async def set_thread_load(thread_id: int, request: ThreadLoadRequest):
    """Set the CPU load for a specific thread."""
    try:
        cpu_loader.set_thread_load(thread_id, request.load_percent)

        # Publish updated settings to MQTT
        if mqtt_publisher:
            mqtt_publisher.publish_load_settings(
                cpu_loader.get_num_threads(), cpu_loader.get_all_loads()
            )

        return {
            "status": "success",
            "thread_id": thread_id,
            "load_percent": request.load_percent,
            "message": f"Thread {thread_id} load set to {request.load_percent}%",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/threads/load/all")
async def set_all_thread_loads(request: AllThreadsLoadRequest):
    """Set the same CPU load for all threads."""
    try:
        cpu_loader.set_all_loads(request.load_percent)

        # Publish updated settings to MQTT
        if mqtt_publisher:
            mqtt_publisher.publish_load_settings(
                cpu_loader.get_num_threads(), cpu_loader.get_all_loads()
            )

        return {
            "status": "success",
            "load_percent": request.load_percent,
            "num_threads": cpu_loader.get_num_threads(),
            "message": f"All threads set to {request.load_percent}%",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/computation-type", response_model=ComputationTypeResponse)
async def get_computation_type():
    """Get the current computation type."""
    current_type = cpu_loader.get_computation_type_string()
    available_types = ["busy-wait", "pi", "primes", "matrix", "fibonacci"]
    return ComputationTypeResponse(
        computation_type=current_type, available_types=available_types
    )


@app.put("/api/computation-type")
async def set_computation_type(request: ComputationTypeRequest):
    """Set the computation type for CPU load generation."""
    try:
        cpu_loader.set_computation_type_from_string(request.computation_type)
        return {
            "status": "success",
            "computation_type": request.computation_type,
            "message": f"Computation type set to {request.computation_type}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="CPU Loader - Generate controllable CPU load with REST API and WebUI"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )
    parser.add_argument(
        "--disable-temperature",
        action="store_true",
        help="Disable CPU temperature monitoring (useful if temperature sensors are unavailable)",
    )
    parser.add_argument(
        "--computation-type",
        choices=["busy-wait", "pi", "primes", "matrix", "fibonacci"],
        default="busy-wait",
        help="Type of computation to perform during CPU load generation (default: busy-wait)",
    )

    # MQTT arguments
    mqtt_group = parser.add_argument_group("MQTT settings")
    mqtt_group.add_argument(
        "--mqtt-broker-host",
        help="MQTT broker hostname (env: MQTT_BROKER_HOST)",
    )
    mqtt_group.add_argument(
        "--mqtt-broker-port",
        type=int,
        help="MQTT broker port (env: MQTT_BROKER_PORT, default: 1883)",
    )
    mqtt_group.add_argument(
        "--mqtt-username",
        help="MQTT username (env: MQTT_USERNAME)",
    )
    mqtt_group.add_argument(
        "--mqtt-password",
        help="MQTT password (env: MQTT_PASSWORD)",
    )
    mqtt_group.add_argument(
        "--mqtt-topic-prefix",
        help="MQTT topic prefix (env: MQTT_TOPIC_PREFIX, default: cpu-loader)",
    )
    mqtt_group.add_argument(
        "--mqtt-client-id",
        help="MQTT client ID (env: MQTT_CLIENT_ID, default: cpu-loader)",
    )

    return parser.parse_args()


def run():
    """Entry point for the CPU Loader application."""
    global temperature_monitoring_enabled
    args = parse_args()

    # Set temperature monitoring based on CLI argument
    temperature_monitoring_enabled = not args.disable_temperature

    # Prepare MQTT arguments (only non-None values)
    mqtt_args = {}
    if args.mqtt_broker_host:
        mqtt_args["broker_host"] = args.mqtt_broker_host
    if args.mqtt_broker_port:
        mqtt_args["broker_port"] = args.mqtt_broker_port
    if args.mqtt_username:
        mqtt_args["username"] = args.mqtt_username
    if args.mqtt_password:
        mqtt_args["password"] = args.mqtt_password
    if args.mqtt_topic_prefix:
        mqtt_args["topic_prefix"] = args.mqtt_topic_prefix
    if args.mqtt_client_id:
        mqtt_args["client_id"] = args.mqtt_client_id

    # Store MQTT args and computation type in app state for lifespan to access
    app.state.mqtt_args = mqtt_args
    app.state.computation_type = args.computation_type

    # Run the server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    run()
