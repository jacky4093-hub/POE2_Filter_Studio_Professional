# POE2 Filter Studio

## Team Roles

ChatGPT
- Architecture
- Product Manager
- Code Review
- Phase Planning

Claude Code
- Implementation
- Multi-file Changes
- Refactoring
- Testing

GitHub Copilot
- Code Completion
- Small Suggestions

## Development Rules

1. Prefer clean architecture
2. GUI framework: PySide6 / Qt6
3. Do not use PyQt6.
4. All new UI code must use PySide6 imports.
5. Keep tests passing
6. Avoid over-engineering
7. Follow phase-based development

## Current Project Status

- Repository: jacky4093-hub/POE2_Filter_Studio_Professional
- Latest commit: P10 Search & Quick Filter Complete
- Completed phases: P1 through P10
- Test status: 644 passed
- GUI framework: PySide6 / Qt6 (do not use PyQt6)

## Current focus

- P18.1 V4 Shell complete — 4-panel layout, NavigationBarV4, StatusBarV4
- Completed phases: P1 through P17.8 + P18.1
- Test status: 1800+ passed

## UI Design Reference

Primary UI Reference: `docs/ui_reference/V4_MAIN_UI.png`

This file is the canonical V4 UI design reference for POE2 Filter Studio.

- **Do not rename** this file.
- **Do not move** this file to a different path.
- **Do not duplicate** this file or create alternative reference images.
- **Do not create** a new primary interface reference image under a different name.

All V4 UI implementation decisions must be grounded in this reference.
Future milestones (P18.2+) must consult this file before making layout changes.
