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

from cpu_loader import CPULoader
from mqtt_publisher import MQTTPublisher

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
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CPU Loader Control</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 900px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .status {
            background: #f0f0f0;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 25px;
            text-align: center;
        }
        .status-item {
            display: inline-block;
            margin: 0 15px;
        }
        .cpu-metrics {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 25px;
        }
        .cpu-metrics h3 {
            margin: 0 0 15px 0;
            color: #333;
            font-size: 16px;
        }
        .cpu-bar-container {
            margin-bottom: 12px;
        }
        .cpu-bar-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 13px;
            color: #666;
        }
        .cpu-bar-wrapper {
            background: #e0e0e0;
            border-radius: 8px;
            height: 20px;
            overflow: hidden;
            position: relative;
        }
        .cpu-bar {
            background: linear-gradient(90deg, #4CAF50 0%, #FFC107 50%, #F44336 100%);
            height: 100%;
            transition: width 0.3s ease;
            border-radius: 8px;
        }
        .cpu-bar.total {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        .preset-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            justify-content: center;
        }
        .preset-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .preset-btn:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .preset-btn:active {
            transform: translateY(0);
        }
        .thread-controls {
            display: grid;
            gap: 20px;
        }
        .thread-control {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .thread-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .thread-label {
            font-weight: 600;
            color: #333;
            font-size: 16px;
        }
        .thread-value {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-weight: 600;
            min-width: 60px;
            text-align: center;
        }
        .slider-container {
            position: relative;
        }
        .slider {
            width: 100%;
            height: 8px;
            border-radius: 5px;
            background: #ddd;
            outline: none;
            -webkit-appearance: none;
        }
        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .slider::-moz-range-thumb {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .slider-labels {
            display: flex;
            justify-content: space-between;
            margin-top: 5px;
            font-size: 12px;
            color: #666;
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
        .success {
            background: #efe;
            color: #3c3;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 CPU Loader Control</h1>
        <p class="subtitle">Control CPU load per thread in real-time</p>

        <div class="status">
            <div class="status-item">
                <strong>Active Threads:</strong> <span id="thread-count">-</span>
            </div>
            <div class="status-item">
                <strong>Target Load:</strong> <span id="avg-load">-</span>%
            </div>
        </div>

        <div class="cpu-metrics">
            <h3>📊 Real-Time CPU Usage</h3>
            <div class="cpu-bar-container">
                <div class="cpu-bar-label">
                    <span><strong>Total CPU</strong></span>
                    <span id="total-cpu-value">-</span>
                </div>
                <div class="cpu-bar-wrapper">
                    <div class="cpu-bar total" id="total-cpu-bar" style="width: 0%"></div>
                </div>
            </div>
            <div id="per-cpu-bars"></div>
        </div>

        <div class="error" id="error-message"></div>
        <div class="success" id="success-message"></div>

        <div class="preset-buttons">
            <button class="preset-btn" onclick="setAllLoads(0)">0%</button>
            <button class="preset-btn" onclick="setAllLoads(10)">10%</button>
            <button class="preset-btn" onclick="setAllLoads(25)">25%</button>
            <button class="preset-btn" onclick="setAllLoads(50)">50%</button>
            <button class="preset-btn" onclick="setAllLoads(80)">80%</button>
            <button class="preset-btn" onclick="setAllLoads(90)">90%</button>
            <button class="preset-btn" onclick="setAllLoads(100)">100%</button>
        </div>

        <div id="thread-controls" class="thread-controls">
            <!-- Thread controls will be dynamically inserted here -->
        </div>
    </div>

    <script>
        let numThreads = 0;
        let updateTimeout = null;
        let ws = null;
        let numCPUs = 0;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/cpu-metrics`;

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket connected');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'cpu_metrics') {
                    updateCPUMetrics(data);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 2000);
            };
        }

        function updateCPUMetrics(data) {
            // Update total CPU
            const totalCpu = data.total_cpu_percent;
            document.getElementById('total-cpu-value').textContent = `${totalCpu}%`;
            document.getElementById('total-cpu-bar').style.width = `${totalCpu}%`;

            // Update per-CPU bars
            const perCpuContainer = document.getElementById('per-cpu-bars');
            if (data.per_cpu_percent.length !== numCPUs) {
                numCPUs = data.per_cpu_percent.length;
                // Recreate all CPU bars
                perCpuContainer.innerHTML = '';
                data.per_cpu_percent.forEach((cpu, index) => {
                    const barHtml = `
                        <div class="cpu-bar-container">
                            <div class="cpu-bar-label">
                                <span>CPU ${index}</span>
                                <span id="cpu-${index}-value">-</span>
                            </div>
                            <div class="cpu-bar-wrapper">
                                <div class="cpu-bar" id="cpu-${index}-bar" style="width: 0%"></div>
                            </div>
                        </div>
                    `;
                    perCpuContainer.insertAdjacentHTML('beforeend', barHtml);
                });
            }

            // Update values
            data.per_cpu_percent.forEach((cpu, index) => {
                document.getElementById(`cpu-${index}-value`).textContent = `${cpu}%`;
                document.getElementById(`cpu-${index}-bar`).style.width = `${cpu}%`;
            });
        }

        async function fetchStatus() {
            try {
                const response = await fetch('/api/threads');
                const data = await response.json();

                numThreads = data.num_threads;
                document.getElementById('thread-count').textContent = numThreads;

                // Calculate average load
                const loads = Object.values(data.loads);
                const avgLoad = loads.length > 0
                    ? (loads.reduce((a, b) => a + b, 0) / loads.length).toFixed(1)
                    : 0;
                document.getElementById('avg-load').textContent = avgLoad;

                // Update or create thread controls
                updateThreadControls(data.loads);
            } catch (error) {
                showError('Failed to fetch status: ' + error.message);
            }
        }

        function updateThreadControls(loads) {
            const container = document.getElementById('thread-controls');

            // If number of threads changed, recreate all controls
            if (container.children.length !== Object.keys(loads).length) {
                container.innerHTML = '';

                for (let i = 0; i < Object.keys(loads).length; i++) {
                    const control = createThreadControl(i, loads[i]);
                    container.appendChild(control);
                }
            } else {
                // Just update values
                Object.entries(loads).forEach(([threadId, load]) => {
                    const slider = document.getElementById(`slider-${threadId}`);
                    const value = document.getElementById(`value-${threadId}`);
                    if (slider && value) {
                        slider.value = load;
                        value.textContent = load.toFixed(0) + '%';
                    }
                });
            }
        }

        function createThreadControl(threadId, initialLoad) {
            const div = document.createElement('div');
            div.className = 'thread-control';
            div.innerHTML = `
                <div class="thread-header">
                    <span class="thread-label">Thread ${threadId}</span>
                    <span class="thread-value" id="value-${threadId}">
                        ${initialLoad.toFixed(0)}%
                    </span>
                </div>
                <div class="slider-container">
                    <input type="range" min="0" max="100" value="${initialLoad}"
                           class="slider" id="slider-${threadId}"
                           oninput="updateThreadLoad(${threadId}, this.value)">
                    <div class="slider-labels">
                        <span>0%</span>
                        <span>25%</span>
                        <span>50%</span>
                        <span>75%</span>
                        <span>100%</span>
                    </div>
                </div>
            `;
            return div;
        }

        async function updateThreadLoad(threadId, loadPercent) {
            // Update UI immediately for responsiveness
            document.getElementById(`value-${threadId}`).textContent = loadPercent + '%';

            // Debounce API calls
            if (updateTimeout) {
                clearTimeout(updateTimeout);
            }

            updateTimeout = setTimeout(async () => {
                try {
                    const response = await fetch(`/api/threads/${threadId}/load`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ load_percent: parseFloat(loadPercent) })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to update thread load');
                    }

                    // Refresh status to get accurate average
                    await fetchStatus();
                } catch (error) {
                    showError('Failed to update thread ' + threadId + ': ' + error.message);
                }
            }, 100);
        }

        async function setAllLoads(loadPercent) {
            try {
                const response = await fetch('/api/threads/load/all', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ load_percent: loadPercent })
                });

                if (!response.ok) {
                    throw new Error('Failed to set loads');
                }

                showSuccess(`All threads set to ${loadPercent}%`);

                // Update UI
                await fetchStatus();
            } catch (error) {
                showError('Failed to set all loads: ' + error.message);
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('error-message');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 5000);
        }

        function showSuccess(message) {
            const successDiv = document.getElementById('success-message');
            successDiv.textContent = message;
            successDiv.style.display = 'block';
            setTimeout(() => {
                successDiv.style.display = 'none';
            }, 3000);
        }

        // Initial load and periodic refresh
        fetchStatus();
        connectWebSocket();
        setInterval(fetchStatus, 5000);
    </script>
</body>
</html>
    """
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
        "--host", default="0.0.0.0", help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind the server to (default: 8000)"
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


if __name__ == "__main__":
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
