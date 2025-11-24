"""
CPU Loader FastAPI Application
Provides REST API and WebUI for controlling CPU load.
"""
import argparse
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Set

import psutil
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
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


# Global CPU loader instance, MQTT publisher, and WebSocket connections
cpu_loader = None
mqtt_publisher: Optional[MQTTPublisher] = None
websocket_connections: Set[WebSocket] = set()
monitoring_task = None


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

            # Prepare message
            message = {
                "type": "cpu_metrics",
                "total_cpu_percent": round(total_cpu, 1),
                "per_cpu_percent": [round(cpu, 1) for cpu in per_cpu],
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
                mqtt_publisher.publish_cpu_metrics(total_cpu, per_cpu)

        except Exception as e:
            logger.error(f"Error in CPU monitoring loop: {e}")
            await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global cpu_loader, mqtt_publisher, monitoring_task
    # Startup
    cpu_loader = CPULoader()

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
    return CPUMetricsResponse(total_cpu_percent=total_cpu, per_cpu_percent=per_cpu)


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
    args = parse_args()

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

    # Store MQTT args in app state for lifespan to access
    app.state.mqtt_args = mqtt_args

    # Run the server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    run()
