# QuantumLayer CLI 🧠

Build complete software systems with one command.

## Installation

```bash
pip install quantumlayer
```

## Quick Start

### Generate a project
```bash
qlp generate "REST API for task management with user authentication"
```

### Interactive mode
```bash
qlp interactive
```

### Generate from image
```bash
qlp from-image architecture-diagram.png
```

## Features

- 🚀 **One Command Generation** - Complete projects from natural language
- 💬 **Interactive Mode** - Build through conversation
- 🎨 **Image to Code** - Generate from architecture diagrams
- 📊 **Multiple Languages** - Python, JavaScript, Go, Java, and more
- 🧪 **Tests Included** - Comprehensive test coverage
- 🐳 **Docker Ready** - Containerization out of the box
- 🚢 **Auto Deploy** - Direct deployment to AWS/Azure/GCP
- 🐙 **GitHub Integration** - Push to GitHub automatically
- 🧠 **Chain of Thought** - See AI reasoning process in real-time
- 📝 **Live Preview** - Preview generated code before creation
- 💰 **Cost Tracking** - See estimated and actual generation costs
- 🔍 **Validation Tools** - Verify generated code quality

## Examples

### Basic API
```bash
qlp generate "REST API with CRUD operations"
```

### Full Stack Application
```bash
qlp generate "E-commerce platform with React frontend and Node.js backend, PostgreSQL database, and Stripe payment integration"
```

### With Deployment
```bash
qlp generate "Serverless API for image processing" --deploy aws
```

### Push to GitHub
```bash
qlp generate "Discord bot with moderation features" --github
```

### Show AI Reasoning
```bash
qlp generate "E-commerce API" --show-reasoning
```

### Live Preview
```bash
qlp generate "Task management app" --preview
```

## Interactive Mode

Start an interactive session to build your project through conversation:

```bash
$ qlp interactive

🧠 QuantumLayer Interactive Mode
What would you like to build today?

You: I need a blog platform
QL: What programming language would you prefer? (Python, JavaScript, Go, etc.)
You: Python with FastAPI
QL: Should I include database and authentication?
You: Yes, use PostgreSQL and JWT auth
QL: That sounds like a solid project! Any other features you'd like to add?
You: Add an admin panel and API documentation
QL: I have enough information. Type 'generate' when ready!
You: generate

🚀 Generating...
✅ Generated 47 files
📁 Project saved to: ./generated/blog-platform
```

## Configuration

Configure default settings:

```bash
# Initialize config
qlp config --init

# Set API endpoint (for self-hosted)
export QLP_API_URL=https://api.quantumlayer.ai

# Set API key (for cloud version)
export QLP_API_KEY=your-api-key
```

## Commands

### Core Commands
- `generate` - Generate a project from description
- `status` - Check workflow status by ID
- `interactive` - Start interactive mode
- `from-image` - Generate from architecture diagram

### Additional Commands
- `watch` - Watch for TODO comments
- `stats` - View statistics
- `config` - Manage configuration
- `validate` - Validate a generated capsule
- `inspect` - Inspect capsule contents and metadata
- `check-github` - Check GitHub repository created by QuantumLayer

### Command Options

#### Generate Options
- `--language, -l` - Programming language (python, javascript, go, etc.)
- `--output, -o` - Output directory
- `--deploy` - Deploy to cloud (aws, azure, gcp)
- `--github` - Push to GitHub automatically
- `--timeout, -t` - Timeout in minutes (default: 10)
- `--dry-run` - Preview without generating
- `--show-reasoning, -r` - Display AI reasoning process
- `--preview, -p` - Show live code preview before generation

#### Status Command
```bash
# Check status of a running workflow
qlp status <workflow-id>

# Example output for completed workflow:
✅ Workflow completed!

Capsule ID    06dc9be3-9f72-48f8-b472-756e617af92f
Execution Time    259.2s
Tasks Completed   6/6

Generated Files:
  📁 source/
    📄 main.py
    📄 module_5.py
    📄 README.md
    ... and 2 more
```

## Tips

1. **Be Specific** - More detail = better results
2. **Mention Stack** - Specify preferred technologies
3. **Include Features** - List key requirements
4. **Request Tests** - Say "with tests" for TDD approach

## Requirements

- Python 3.8+
- Internet connection
- QuantumLayer backend (local or cloud)

## Support

- Documentation: https://docs.quantumlayer.ai
- Discord: https://discord.gg/quantumlayer
- Issues: https://github.com/quantumlayer/qlp-cli/issues

## License

MIT License - see LICENSE file for details.