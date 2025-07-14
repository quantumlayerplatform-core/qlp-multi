# Changelog

All notable changes to the QuantumLayer CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-01-14

### Added
- New `status` command to check workflow status by ID
- Improved progress tracking that shows actual task completion
- Better handling of completed workflow responses

### Fixed
- Progress bar stuck at 10% issue - now uses correct `/workflow/status` endpoint
- Progress tracking now shows smooth time-based progress when task info unavailable
- Status command updated to use the correct endpoint and handle response format
- Proper detection of completed workflows with result extraction

### Changed
- Progress updates now based on actual task completion rather than time estimates
- More informative progress messages during generation
- Timeout can now be configured with `--timeout` flag (default: 30 minutes)

## [0.1.0] - 2025-01-14

### Added
- Initial release of QuantumLayer CLI
- `generate` command for creating projects from natural language
- `interactive` mode for conversational project building
- `from-image` command for generating from architecture diagrams
- `watch` mode for monitoring TODO comments
- `stats` command for viewing platform statistics
- `config` command for managing settings
- GitHub integration with `--github` flag
- Cloud deployment support with `--deploy` flag
- Beautiful terminal UI with Rich library
- Progress tracking during generation
- Automatic file download and extraction