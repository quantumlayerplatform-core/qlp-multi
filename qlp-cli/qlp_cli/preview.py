"""
Live code preview for QuantumLayer CLI
"""

import asyncio
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.columns import Columns
from rich.table import Table
from rich.prompt import Confirm
from rich import box
from rich.layout import Layout
from rich.live import Live

console = Console()

# Sample code previews for different project types
PREVIEW_TEMPLATES = {
    "api": {
        "python": {
            "main.py": '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Task Management API")

class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    completed: bool = False

tasks_db = []

@app.get("/")
def read_root():
    return {"message": "Task Management API", "version": "1.0.0"}

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    return tasks_db

@app.post("/tasks", response_model=Task)
def create_task(task: Task):
    task.id = len(tasks_db) + 1
    tasks_db.append(task)
    return task''',
            "requirements.txt": '''fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-jose==3.3.0
passlib==1.7.4
python-multipart==0.0.6''',
            "test_main.py": '''import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Task Management API"

def test_create_task():
    response = client.post("/tasks", json={
        "title": "Test Task",
        "description": "Test Description"
    })
    assert response.status_code == 200
    assert response.json()["title"] == "Test Task"'''
        },
        "javascript": {
            "app.js": '''const express = require('express');
const cors = require('cors');
const helmet = require('helmet');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// In-memory storage
let tasks = [];

// Routes
app.get('/', (req, res) => {
    res.json({ message: 'Task Management API', version: '1.0.0' });
});

app.get('/tasks', (req, res) => {
    res.json(tasks);
});

app.post('/tasks', (req, res) => {
    const task = {
        id: tasks.length + 1,
        ...req.body,
        completed: false
    };
    tasks.push(task);
    res.status(201).json(task);
});''',
            "package.json": '''{
  "name": "task-management-api",
  "version": "1.0.0",
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js",
    "test": "jest"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "helmet": "^7.1.0"
  },
  "devDependencies": {
    "nodemon": "^3.0.1",
    "jest": "^29.7.0",
    "supertest": "^6.3.3"
  }
}''',
            "app.test.js": '''const request = require('supertest');
const app = require('./app');

describe('Task API', () => {
    test('GET / returns API info', async () => {
        const response = await request(app).get('/');
        expect(response.status).toBe(200);
        expect(response.body.message).toBe('Task Management API');
    });
    
    test('POST /tasks creates a new task', async () => {
        const response = await request(app)
            .post('/tasks')
            .send({ title: 'Test Task' });
        expect(response.status).toBe(201);
        expect(response.body.title).toBe('Test Task');
    });
});'''
        }
    },
    "web": {
        "react": {
            "App.jsx": '''import React, { useState } from 'react';
import './App.css';

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState('');

  const addTask = () => {
    if (newTask.trim()) {
      setTasks([...tasks, {
        id: Date.now(),
        text: newTask,
        completed: false
      }]);
      setNewTask('');
    }
  };

  const toggleTask = (id) => {
    setTasks(tasks.map(task =>
      task.id === id ? { ...task, completed: !task.completed } : task
    ));
  };

  return (
    <div className="App">
      <h1>Task Manager</h1>
      <div className="input-group">
        <input
          type="text"
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          placeholder="Add a new task..."
        />
        <button onClick={addTask}>Add</button>
      </div>
      <ul className="task-list">
        {tasks.map(task => (
          <li key={task.id} className={task.completed ? 'completed' : ''}>
            <input
              type="checkbox"
              checked={task.completed}
              onChange={() => toggleTask(task.id)}
            />
            <span>{task.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;''',
            "package.json": '''{
  "name": "task-manager",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  }
}''',
            "App.css": '''.App {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

h1 {
  color: #333;
  text-align: center;
}

.input-group {
  display: flex;
  margin-bottom: 20px;
}

.input-group input {
  flex: 1;
  padding: 10px;
  font-size: 16px;
  border: 1px solid #ddd;
  border-radius: 4px 0 0 4px;
}

.input-group button {
  padding: 10px 20px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
}

.task-list {
  list-style: none;
  padding: 0;
}

.task-list li {
  padding: 10px;
  margin-bottom: 5px;
  background-color: #f5f5f5;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.task-list li.completed span {
  text-decoration: line-through;
  color: #888;
}'''
        }
    },
    "cli": {
        "python": {
            "cli.py": '''import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

TASKS_FILE = Path.home() / '.tasks.json'

def load_tasks():
    if TASKS_FILE.exists():
        with open(TASKS_FILE) as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

@click.group()
def cli():
    """Task Management CLI"""
    pass

@cli.command()
@click.argument('title')
@click.option('--description', '-d', help='Task description')
def add(title, description):
    """Add a new task"""
    tasks = load_tasks()
    task = {
        'id': len(tasks) + 1,
        'title': title,
        'description': description or '',
        'completed': False
    }
    tasks.append(task)
    save_tasks(tasks)
    console.print(f"[green]✅ Task added:[/] {title}")

@cli.command()
def list():
    """List all tasks"""
    tasks = load_tasks()
    
    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    
    for task in tasks:
        status = "✅" if task['completed'] else "⏳"
        table.add_row(str(task['id']), task['title'], status)
    
    console.print(table)

if __name__ == '__main__':
    cli()''',
            "setup.py": '''from setuptools import setup, find_packages

setup(
    name="task-cli",
    version="0.1.0",
    py_modules=['cli'],
    install_requires=[
        'click',
        'rich',
    ],
    entry_points={
        'console_scripts': [
            'task=cli:cli',
        ],
    },
)''',
            "requirements.txt": '''click==8.1.7
rich==13.7.0'''
        }
    }
}

def detect_preview_type(description: str) -> tuple[str, str]:
    """Detect project type and language from description"""
    desc_lower = description.lower()
    
    # Detect type
    if any(word in desc_lower for word in ["api", "rest", "graphql", "backend"]):
        project_type = "api"
    elif any(word in desc_lower for word in ["web", "website", "frontend", "react", "vue"]):
        project_type = "web"
    elif any(word in desc_lower for word in ["cli", "command", "terminal"]):
        project_type = "cli"
    else:
        project_type = "api"  # default
    
    # Detect language/framework
    if "python" in desc_lower or "fastapi" in desc_lower or "django" in desc_lower:
        language = "python"
    elif "javascript" in desc_lower or "node" in desc_lower or "express" in desc_lower:
        language = "javascript"
    elif "react" in desc_lower:
        language = "react"
    else:
        language = "python"  # default
    
    return project_type, language

def create_preview_panel(filename: str, content: str, language: str = None) -> Panel:
    """Create a panel with syntax highlighted code"""
    # Detect language from filename if not provided
    if not language:
        if filename.endswith('.py'):
            language = 'python'
        elif filename.endswith(('.js', '.jsx')):
            language = 'javascript'
        elif filename.endswith('.json'):
            language = 'json'
        elif filename.endswith('.css'):
            language = 'css'
        else:
            language = 'text'
    
    syntax = Syntax(
        content, 
        language, 
        theme="monokai", 
        line_numbers=True,
        word_wrap=True
    )
    
    return Panel(
        syntax,
        title=f"📄 {filename}",
        border_style="blue",
        box=box.ROUNDED,
        padding=(0, 1)
    )

def create_file_tree(files: Dict[str, str]) -> Table:
    """Create a file tree visualization"""
    table = Table(title="📁 Project Structure", show_header=False, box=box.SIMPLE)
    table.add_column(style="cyan")
    
    table.add_row("project/")
    for filename in sorted(files.keys()):
        table.add_row(f"  ├── {filename}")
    
    return table

async def show_live_preview(description: str, language: str = "auto") -> bool:
    """Show live preview of what will be generated"""
    
    project_type, detected_lang = detect_preview_type(description)
    
    if language == "auto":
        language = detected_lang
    
    # Get preview templates
    templates = PREVIEW_TEMPLATES.get(project_type, {})
    files = templates.get(language, templates.get("python", {}))
    
    if not files:
        console.print("[yellow]No preview available for this project type[/]")
        return True
    
    console.print("\n[bold cyan]📝 Live Code Preview[/]\n")
    
    # Show project structure
    console.print(create_file_tree(files))
    console.print()
    
    # Show file contents
    for i, (filename, content) in enumerate(files.items()):
        if i < 2:  # Show first 2 files
            console.print(create_preview_panel(filename, content))
            if i < len(files) - 1:
                console.print()
    
    if len(files) > 2:
        console.print(f"[dim]... and {len(files) - 2} more files[/]\n")
    
    # Show generation info
    info_table = Table(show_header=False, box=None)
    info_table.add_column(style="cyan", width=20)
    info_table.add_column(style="white")
    
    info_table.add_row("Project Type", project_type.title())
    info_table.add_row("Language", language.title())
    info_table.add_row("Files", str(len(files)))
    info_table.add_row("Key Features", "✅ Tests, ✅ Documentation, ✅ Best Practices")
    
    console.print(Panel(
        info_table,
        title="[bold]Generation Details[/]",
        border_style="green"
    ))
    
    console.print()
    
    # Ask for confirmation
    return Confirm.ask("Continue with full generation?", default=True)

async def show_animated_preview(files: Dict[str, str]):
    """Show animated preview with live updates"""
    
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    layout["header"].update(Panel("[bold cyan]🚀 Generating Your Project[/]", border_style="cyan"))
    layout["footer"].update(Panel("[dim]Press Ctrl+C to cancel[/]", border_style="dim"))
    
    with Live(layout, refresh_per_second=4, console=console) as live:
        for i, (filename, content) in enumerate(files.items()):
            # Update body with current file
            layout["body"].update(create_preview_panel(filename, content[:500] + "..."))
            
            # Update header with progress
            progress = f"[bold cyan]🚀 Generating: {filename} ({i+1}/{len(files)})[/]"
            layout["header"].update(Panel(progress, border_style="cyan"))
            
            await asyncio.sleep(1.5)  # Simulate generation time
    
    console.print("[bold green]✅ Preview complete![/]")