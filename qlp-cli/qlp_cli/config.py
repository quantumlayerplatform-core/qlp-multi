"""
Configuration management for QuantumLayer CLI
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Manage CLI configuration"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.quantumlayer'
        self.config_file = self.config_dir / 'config.json'
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        
        # Default configuration
        config = {
            'api_url': os.getenv('QLP_API_URL', 'http://localhost:8000'),
            'api_key': os.getenv('QLP_API_KEY', ''),
            'default_language': 'auto',
            'output_dir': './generated',
            'telemetry_enabled': False
        }
        
        # Load from file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except:
                pass
        
        return config
    
    def save(self):
        """Save configuration to file"""
        self.config_dir.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self._config, f, indent=2)
    
    @property
    def api_url(self) -> str:
        return self._config['api_url']
    
    @api_url.setter
    def api_url(self, value: str):
        self._config['api_url'] = value
        self.save()
    
    @property
    def api_key(self) -> str:
        return self._config['api_key']
    
    @api_key.setter
    def api_key(self, value: str):
        self._config['api_key'] = value
        self.save()
    
    @property
    def default_language(self) -> str:
        return self._config['default_language']
    
    @property
    def output_dir(self) -> str:
        return self._config['output_dir']
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return self._config.copy()