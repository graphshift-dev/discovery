"""
Help Service - Handles all help-related functionality.
Clean separation: commands.py delegates help logic to this service.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HelpService:
    """
    Single responsibility: Generate help content for CLI commands.
    Commands.py delegates all help logic to this service.
    """
    
    def __init__(self):
        """Initialize help service"""
        pass
    
    def get_analyze_help(self) -> str:
        """Get help text for analyze command"""
        return """
GraphShift Analysis Commands:

Single Repository Analysis:
  graphshift analyze --local-path <path>     # Analyze local repository
  graphshift analyze --repo <url>            # Analyze remote repository

Organization Analysis:
  graphshift analyze --org <org-name>        # Analyze remote organization
  graphshift analyze --local-org <path>      # Analyze local organization

Options:
  --to-version {8,11,17,21}     Target JDK version (default: 21)
  --scope {upgrade-blockers,all-deprecations}  Analysis scope
  --max-repos N                 Maximum repositories to analyze
  --keep-clones                 Keep cloned repositories (default: true)
  
Examples:
  graphshift analyze --repo https://github.com/spring-projects/spring-petclinic
  graphshift analyze --org spring-projects --to-version 17
  graphshift analyze --local-path C:\\my-java-project
        """.strip()
    
    def get_health_help(self) -> str:
        """Get help text for health command"""
        return """
GraphShift Health Check:

  graphshift health             # Check system health
  graphshift health --verbose   # Detailed health information
  
Checks:
  - Java installation and version
  - JAR analyzer availability
  - Configuration validity
  - Network connectivity (for remote analysis)
        """.strip()
    
    def get_general_help(self) -> str:
        """Get general help text"""
        return """
GraphShift - Java Migration Analysis Tool

Commands:
  analyze    Analyze Java repositories for migration opportunities
  health     Check system health and configuration

Use 'graphshift <command> --help' for command-specific help.

For more information, visit: https://docs.graphshift.dev
        """.strip()