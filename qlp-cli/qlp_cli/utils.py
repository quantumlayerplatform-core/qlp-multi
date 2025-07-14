"""
Utility functions for QuantumLayer CLI
"""

import os
import random
import zipfile
import tarfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta


def extract_capsule(file_path: str, output_dir: str) -> bool:
    """Extract a capsule archive to the specified directory"""
    
    file_path = Path(file_path)
    output_dir = Path(output_dir)
    
    if not file_path.exists():
        return False
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if file_path.suffix == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
        elif file_path.suffix in ['.tar', '.gz']:
            with tarfile.open(file_path, 'r:*') as tar_ref:
                tar_ref.extractall(output_dir)
        else:
            return False
        
        return True
    except Exception:
        return False


def format_time(seconds: float) -> str:
    """Format time duration in human-readable format"""
    
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_random_tip() -> str:
    """Get a random tip for users"""
    
    tips = [
        "Use 'qlp interactive' for a conversational experience",
        "Add --github flag to automatically push to GitHub",
        "You can generate from images with 'qlp from-image'",
        "Check your stats with 'qlp stats personal'",
        "Use specific descriptions for better results",
        "Include 'with tests' to get comprehensive test coverage",
        "Try 'qlp watch' to generate code from TODO comments",
        "Specify a language with -l flag for consistent output",
        "Use --deploy flag to deploy directly to cloud",
        "Join our Discord for tips and tricks!"
    ]
    
    return random.choice(tips)


def validate_description(description: str) -> bool:
    """Validate that description is sufficient"""
    
    if not description or len(description.strip()) < 10:
        return False
    
    words = description.split()
    return len(words) >= 3


def ensure_config() -> bool:
    """Ensure configuration directory exists"""
    
    config_dir = Path.home() / '.quantumlayer'
    config_dir.mkdir(exist_ok=True)
    
    # Create default config if not exists
    config_file = config_dir / 'config.json'
    if not config_file.exists():
        default_config = {
            'api_url': 'http://localhost:8000',
            'api_key': '',
            'default_language': 'auto',
            'output_dir': './generated',
            'telemetry_enabled': False,
            'created_at': datetime.now().isoformat()
        }
        
        import json
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
    
    return True


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    
    return f"{size_bytes:.1f} TB"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    
    # Remove invalid characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename.strip()


def estimate_generation_time(description: str) -> int:
    """Estimate generation time in seconds based on description complexity"""
    
    word_count = len(description.split())
    
    # Base time + complexity factor
    base_time = 30
    complexity_factor = word_count * 2
    
    # Cap at 5 minutes
    return min(base_time + complexity_factor, 300)


def create_progress_message(stage: str, detail: str = "") -> str:
    """Create a formatted progress message"""
    
    stages = {
        "init": "🚀 Initializing",
        "analyze": "🔍 Analyzing requirements",
        "design": "📐 Designing architecture",
        "generate": "⚡ Generating code",
        "validate": "✅ Validating output",
        "package": "📦 Packaging files",
        "deploy": "☁️  Deploying",
        "complete": "🎉 Complete"
    }
    
    message = stages.get(stage, stage)
    if detail:
        message += f" - {detail}"
    
    return message