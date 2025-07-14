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


# Thought bubbles for different stages
THOUGHT_BUBBLES = {
    "analyzing": [
        "🤔 Understanding your requirements...",
        "📝 Breaking down the project structure...",
        "🧩 Identifying key components...",
        "🎯 Planning the implementation approach...",
        "🔍 Analyzing dependencies and integrations..."
    ],
    "generating": [
        "⚡ Generating production-ready code...",
        "🏗️ Building the architecture...",
        "✨ Crafting elegant solutions...",
        "🔧 Implementing best practices...",
        "📦 Creating modular components..."
    ],
    "validating": [
        "🧪 Running comprehensive tests...",
        "✅ Validating code quality...",
        "🔒 Checking security patterns...",
        "📊 Analyzing performance metrics...",
        "🎨 Ensuring code style consistency..."
    ],
    "packaging": [
        "📦 Packaging your project...",
        "🎁 Preparing deliverables...",
        "📄 Generating documentation...",
        "🚀 Finalizing deployment configs...",
        "🎉 Almost there..."
    ]
}


def get_random_thought(stage: str) -> str:
    """Get a random thought bubble for the current stage"""
    thoughts = THOUGHT_BUBBLES.get(stage.lower(), ["🤖 Processing..."])
    return random.choice(thoughts)


def format_cost(cost_usd: float) -> str:
    """Format cost in USD with color coding"""
    if cost_usd < 0.10:
        return f"[green]${cost_usd:.3f}[/]"
    elif cost_usd < 0.50:
        return f"[yellow]${cost_usd:.3f}[/]"
    else:
        return f"[red]${cost_usd:.3f}[/]"


def estimate_cost(description: str, language: str = "auto") -> float:
    """Estimate generation cost based on complexity"""
    # Base cost estimation
    word_count = len(description.split())
    
    # Complexity factors
    base_cost = 0.02  # Base cost per generation
    word_factor = word_count * 0.001  # Cost per word
    
    # Language complexity multipliers
    language_multipliers = {
        "python": 1.0,
        "javascript": 1.1,
        "typescript": 1.2,
        "go": 1.3,
        "java": 1.4,
        "auto": 1.1
    }
    
    lang_multiplier = language_multipliers.get(language.lower(), 1.1)
    
    # Calculate total
    estimated_cost = (base_cost + word_factor) * lang_multiplier
    
    # Cap at reasonable maximum
    return min(estimated_cost, 2.0)