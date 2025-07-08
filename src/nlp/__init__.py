"""
Universal NLP Foundation Package
Provides emergent understanding without domain constraints
"""

from .universal_decomposer import (
    UniversalDecomposer,
    Pattern,
    Intent,
    Requirements,
    DecompositionResult,
    PatternMemory,
    IntentLearner,
    RequirementExtractor,
    DecompositionEngine
)

__all__ = [
    'UniversalDecomposer',
    'Pattern',
    'Intent', 
    'Requirements',
    'DecompositionResult',
    'PatternMemory',
    'IntentLearner',
    'RequirementExtractor',
    'DecompositionEngine'
]