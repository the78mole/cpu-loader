"""
CPU Loader FastAPI Application
Provides REST API and WebUI for controlling CPU load.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict
import uvicorn

from cpu_loader import CPULoader


# Pydantic models for request/response validation
class ThreadLoadRequest(BaseModel):
    load_percent: float = Field(..., ge=0, le=100, description="Load percentage (0-100)")


class AllThreadsLoadRequest(BaseModel):
    load_percent: float = Field(..., ge=0, le=100, description="Load percentage (0-100)")


class ThreadCountRequest(BaseModel):
    num_threads: int = Field(..., gt=0, description="Number of threads (must be positive)")


class ThreadsStatusResponse(BaseModel):
    num_threads: int
    loads: Dict[int, float]


# Initialize FastAPI app
app = FastAPI(
    title="CPU Loader API",
    description="Control CPU load generation with configurable threads",
    version="1.0.0"
)

# Global CPU loader instance
cpu_loader = CPULoader()


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
                <strong>Average Load:</strong> <span id="avg-load">-</span>%
            </div>
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
                    <span class="thread-value" id="value-${threadId}">${initialLoad.toFixed(0)}%</span>
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
        num_threads=cpu_loader.get_num_threads(),
        loads=cpu_loader.get_all_loads()
    )


@app.post("/api/threads")
async def set_thread_count(request: ThreadCountRequest):
    """Set the number of threads."""
    try:
        cpu_loader.set_num_threads(request.num_threads)
        return {
            "status": "success",
            "num_threads": request.num_threads,
            "message": f"Thread count set to {request.num_threads}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/threads/{thread_id}/load")
async def set_thread_load(thread_id: int, request: ThreadLoadRequest):
    """Set the CPU load for a specific thread."""
    try:
        cpu_loader.set_thread_load(thread_id, request.load_percent)
        return {
            "status": "success",
            "thread_id": thread_id,
            "load_percent": request.load_percent,
            "message": f"Thread {thread_id} load set to {request.load_percent}%"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/threads/load/all")
async def set_all_thread_loads(request: AllThreadsLoadRequest):
    """Set the same CPU load for all threads."""
    try:
        cpu_loader.set_all_loads(request.load_percent)
        return {
            "status": "success",
            "load_percent": request.load_percent,
            "num_threads": cpu_loader.get_num_threads(),
            "message": f"All threads set to {request.load_percent}%"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    cpu_loader.shutdown()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
