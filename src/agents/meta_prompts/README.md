# Meta-Prompt Engineering System

## Overview

The Meta-Prompt Engineering System implements **recursive self-improvement** for code generation, based on principles from critical rationalism and evolutionary epistemology. It enables prompts to evolve and improve over time, learning from each execution to generate increasingly sophisticated and principled code.

## Core Philosophy

> "All life is problem-solving" - Karl Popper

The system embodies key principles:
- **Conjecture and Refutation**: Generate hypotheses (prompts), test them, learn from failures
- **Explanation Depth**: Seek deeper, harder-to-vary explanations
- **Error Correction**: Mistakes are opportunities for improvement
- **Universal Principles**: Extract timeless truths from specific instances

## Architecture

### 1. Prompt Genome (`prompt_genome.py`)
DNA-like structures that encode prompt strategies:
- **Objectives**: What the prompt aims to achieve
- **Constraints**: Boundaries and requirements
- **Principles**: Timeless software engineering wisdom
- **Examples**: Learned patterns from past executions
- **Evolution History**: How the prompt has changed over time

### 2. Principle Library (`principle_library.py`)
Curated collection of software engineering wisdom from:
- David Deutsch (explanation depth, error correction)
- Karl Popper (critical rationalism, problem-solving)
- Edsger Dijkstra (simplicity, correctness)
- Alan Kay (biological thinking, message passing)
- Barbara Liskov (abstraction, substitution)
- And many more...

### 3. Meta Engineer (`meta_engineer.py`)
The brain that creates and evolves prompts using 7 strategies:
1. **Conjecture & Refutation**: Generate → Test → Refute → Improve
2. **Explanation Depth**: Seek fundamental understanding
3. **Error Correction**: Learn from every mistake
4. **Principle Extraction**: Derive universal truths
5. **Creative Destruction**: Break to understand
6. **Contrarian**: Challenge assumptions
7. **Synthesis**: Combine best ideas

## How It Works

### 1. Initial Prompt Generation
```python
prompt = await engineer.generate_meta_prompt(
    task_description="Build a distributed cache",
    agent_role="implementer",
    evolution_strategy=PromptEvolutionStrategy.EXPLANATION_DEPTH
)
```

### 2. Execution & Learning
The system learns from each execution:
```python
await engineer.learn_from_execution(
    agent_role="implementer",
    result=code_output,
    performance_metrics={
        "validation_score": 0.95,
        "confidence_score": 0.88,
        "execution_time": 45.2
    }
)
```

### 3. Evolution
Prompts evolve through:
- **Mutation**: Small random changes
- **Crossover**: Combining successful strategies
- **Selection**: Survival of the fittest
- **Learning**: Incorporating new examples

### 4. Storage & Persistence
Evolved prompts are stored in `data/prompt_genomes/` as JSON files, creating a growing library of optimized prompts.

## Integration with Ensemble

The system seamlessly integrates with the existing ensemble through `enhance_with_meta_prompts.py`:

1. Each agent role gets tailored evolution strategies
2. Prompts are enhanced before execution
3. Results feed back into the learning system
4. Continuous improvement happens automatically

## Usage Examples

### Basic Usage
```bash
# Run tests to see it in action
python test_meta_prompts.py
```

### With Ensemble
```bash
# Just run your normal ensemble - meta-prompts are integrated
python test_ensemble.py
```

### Direct Meta-Prompt Generation
```python
from src.agents.meta_prompts import MetaPromptEngineer

engineer = MetaPromptEngineer()
prompt = await engineer.generate_meta_prompt(
    task_description="Implement rate limiting",
    agent_role="implementer",
    evolution_strategy=PromptEvolutionStrategy.PRINCIPLE_EXTRACTION
)
```

## Expected Improvements

With meta-prompt engineering, you should see:

1. **Higher Confidence Scores**: Approaching 90%+ as prompts improve
2. **Better Code Quality**: More thoughtful, principled implementations
3. **Deeper Understanding**: Code that explains its design decisions
4. **Continuous Learning**: Each execution makes future ones better
5. **Emergent Wisdom**: System discovers new principles over time

## Evolution Strategies Explained

### Conjecture & Refutation
Generate bold hypotheses, test rigorously, learn from failures. Example:
> "What if we treat every function as a pure transformation?"

### Explanation Depth
Seek fundamental understanding, not surface solutions. Example:
> "Don't just implement caching, understand why caching solves this specific problem"

### Error Correction
Every bug is a learning opportunity. Example:
> "This race condition teaches us about the importance of atomic operations"

### Principle Extraction
Derive universal truths from specific instances. Example:
> "From this API design, we learn: explicit is better than implicit"

### Creative Destruction
Sometimes you must break things to understand them. Example:
> "What happens if we remove this abstraction entirely?"

### Contrarian
Challenge conventional wisdom. Example:
> "Everyone uses ORM, but what if direct SQL is better here?"

### Synthesis
Combine the best of multiple approaches. Example:
> "Functional programming's immutability + OOP's encapsulation"

## Monitoring Evolution

Check how your prompts are evolving:

```python
# Get evolution report
report = engineer.get_evolution_report()
print(f"Total Genomes: {report['total_genomes']}")
print(f"Top Principles: {report['top_principles']}")

# Get best genome for a role
genome = engineer.get_best_genome_for_role("implementer")
print(f"Fitness Score: {genome.fitness_score()}")
```

## Future Enhancements

1. **Cross-Project Learning**: Share learned patterns across projects
2. **Principle Discovery**: Automatically discover new principles
3. **Meta-Meta Prompts**: Prompts that improve the improvement process
4. **Visualization**: See prompt evolution in real-time
5. **A/B Testing**: Systematically compare strategies

## Philosophy in Action

This system embodies the belief that:
- Problems are soluble (Deutsch)
- Knowledge grows through conjecture and criticism (Popper)
- The best code embodies deep principles (Dijkstra)
- Systems should be grown, not built (Kay)

By applying these principles to prompt engineering itself, we create a system that not only generates code but continuously improves its ability to generate better code.

## Conclusion

The Meta-Prompt Engineering System represents a fundamental shift from static prompts to evolving, learning systems. It's not just about generating code - it's about building a system that gets better at generating code over time, embodying the very principles of evolution and epistemology that drive human knowledge forward.

As Deutsch says: "The beginning of infinity" - and this system is just the beginning of infinitely improving code generation.