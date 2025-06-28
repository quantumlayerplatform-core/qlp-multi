#!/usr/bin/env python3
"""
QLP Quick Win #2: Real-time Progress Tracking
Provides WebSocket-based progress updates during code generation
"""

import asyncio
import json
from typing import Dict, Set, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import structlog

logger = structlog.get_logger()

class ProgressTracker:
    """Manages progress tracking for code generation tasks"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.task_progress: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, task_id: str, websocket: WebSocket):
        """Connect a client to track a specific task"""
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        
        self.active_connections[task_id].add(websocket)
        logger.info(f"Client connected to track task: {task_id}")
        
        # Send current progress if task exists
        if task_id in self.task_progress:
            await self.send_update(task_id, self.task_progress[task_id])
    
    async def disconnect(self, task_id: str, websocket: WebSocket):
        """Disconnect a client from tracking"""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        logger.info(f"Client disconnected from task: {task_id}")
    
    async def update_progress(
        self,
        task_id: str,
        stage: str,
        progress: float,
        message: str,
        details: Dict[str, Any] = None
    ):
        """Update progress for a task and notify all connected clients"""
        progress_data = {
            "task_id": task_id,
            "stage": stage,
            "progress": min(max(progress, 0), 100),  # Clamp between 0-100
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.task_progress[task_id] = progress_data
        await self.send_update(task_id, progress_data)
    
    async def send_update(self, task_id: str, data: Dict[str, Any]):
        """Send update to all clients tracking this task"""
        if task_id not in self.active_connections:
            return
        
        disconnected = set()
        message = json.dumps(data)
        
        for websocket in self.active_connections[task_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
                else:
                    disconnected.add(websocket)
            except Exception as e:
                logger.error(f"Error sending update: {str(e)}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(task_id, websocket)
    
    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Mark a task as complete and send final update"""
        await self.update_progress(
            task_id,
            "complete",
            100,
            "Code generation complete!",
            {"result": result}
        )
        
        # Clean up after a delay
        await asyncio.sleep(5)
        if task_id in self.task_progress:
            del self.task_progress[task_id]
    
    async def fail_task(self, task_id: str, error: str):
        """Mark a task as failed"""
        await self.update_progress(
            task_id,
            "failed",
            0,
            f"Generation failed: {error}",
            {"error": error}
        )


# Global progress tracker instance
progress_tracker = ProgressTracker()


# Integration with code generation
class ProgressAwareGenerator:
    """Wrapper that adds progress tracking to generation"""
    
    def __init__(self):
        from advanced_integration import AdvancedProductionGenerator
        self.generator = AdvancedProductionGenerator()
        
    async def generate_with_progress(
        self,
        task_id: str,
        description: str,
        requirements: Dict[str, Any] = None,
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate code with progress updates"""
        
        try:
            # Stage 1: Initialization
            await progress_tracker.update_progress(
                task_id,
                "initializing",
                10,
                "Analyzing requirements...",
                {"description_length": len(description)}
            )
            
            # Stage 2: Strategy Selection
            await asyncio.sleep(0.5)  # Simulate processing
            desc_lower = description.lower()
            if any(word in desc_lower for word in ["test", "testing"]):
                strategy = "TEST_DRIVEN"
            elif any(word in desc_lower for word in ["complex", "distributed"]):
                strategy = "MULTI_MODEL"
            else:
                strategy = "TEST_DRIVEN"
            
            await progress_tracker.update_progress(
                task_id,
                "strategy_selected",
                20,
                f"Selected {strategy} strategy",
                {"strategy": strategy}
            )
            
            # Stage 3: Code Generation
            await progress_tracker.update_progress(
                task_id,
                "generating",
                40,
                "Generating code with AI models...",
                {"models": ["GPT-4", "Claude", "DeepSeek", "CodeLlama"]}
            )
            
            # Actual generation
            result = await self.generator.generate_production_code(
                description, requirements, constraints
            )
            
            # Stage 4: Validation
            await progress_tracker.update_progress(
                task_id,
                "validating",
                70,
                "Validating generated code...",
                {"confidence": result.get("confidence", 0)}
            )
            
            # Stage 5: Finalization
            await progress_tracker.update_progress(
                task_id,
                "finalizing",
                90,
                "Finalizing output...",
                {
                    "code_length": len(result.get("code", "")),
                    "tests_generated": bool(result.get("tests")),
                    "patterns_applied": result.get("patterns_applied", [])
                }
            )
            
            # Complete
            await progress_tracker.complete_task(task_id, {
                "confidence": result.get("confidence", 0),
                "validation_score": result.get("validation_score", 0)
            })
            
            return result
            
        except Exception as e:
            await progress_tracker.fail_task(task_id, str(e))
            raise


# WebSocket endpoint for progress tracking
async def websocket_progress_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time progress tracking"""
    await progress_tracker.connect(task_id, websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await progress_tracker.disconnect(task_id, websocket)


# Example HTML client for testing
PROGRESS_CLIENT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>QLP Progress Tracker</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .progress-bar { width: 100%; height: 30px; background: #f0f0f0; border-radius: 15px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #00ff88, #00ffff); transition: width 0.5s; }
        .status { margin: 20px 0; }
        .details { background: #f5f5f5; padding: 10px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>QLP Code Generation Progress</h1>
    <div class="progress-bar">
        <div class="progress-fill" id="progress" style="width: 0%"></div>
    </div>
    <div class="status">
        <h3>Status: <span id="stage">Waiting...</span></h3>
        <p id="message">Connecting to server...</p>
    </div>
    <div class="details" id="details"></div>
    
    <script>
        const taskId = new URLSearchParams(window.location.search).get('task_id') || 'test-task';
        const ws = new WebSocket(`ws://localhost:8001/ws/progress/${taskId}`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Update progress bar
            document.getElementById('progress').style.width = data.progress + '%';
            
            // Update status
            document.getElementById('stage').textContent = data.stage.replace('_', ' ').toUpperCase();
            document.getElementById('message').textContent = data.message;
            
            // Update details
            if (data.details && Object.keys(data.details).length > 0) {
                document.getElementById('details').innerHTML = 
                    '<strong>Details:</strong><br>' + 
                    JSON.stringify(data.details, null, 2).replace(/\n/g, '<br>');
            }
            
            // Handle completion
            if (data.stage === 'complete') {
                document.getElementById('progress').style.background = '#00ff88';
            } else if (data.stage === 'failed') {
                document.getElementById('progress').style.background = '#ff6666';
            }
        };
        
        ws.onerror = (error) => {
            document.getElementById('message').textContent = 'Connection error: ' + error;
        };
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    # Save the HTML client
    with open("progress_tracker_demo.html", "w") as f:
        f.write(PROGRESS_CLIENT_HTML)
    print("Created progress_tracker_demo.html - Open in browser to test WebSocket progress tracking")
