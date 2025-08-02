"""
Commands - Thin command shell that delegates to services.
Clean architecture: Commands.py should just be a command shell.

Your Architecture:
commands.py --> helpservice - gets help output
commands.py --> healthservice - gets health output  
commands.py --> analyze - hands off to analysis service
analysisService-> outputservice- creates the output-->feedback to commands.py
AnalysisService--> progress reporter service- creates progress report-->feedback to commands.py
"""

import asyncio
import logging
from typing import Dict, Optional, Any

from services.help_service import HelpService
from services.health_service import HealthService
from services.analysis_service import AnalysisService

logger = logging.getLogger("graphshift.cli")


class GraphShiftCommands:
    """
    Thin command shell - delegates all logic to services.
    Single responsibility: Parse commands and delegate to appropriate services.
    """

    def __init__(self, config: Dict[str, Any], memory_overrides: Optional[Dict[str, str]] = None):
        """Initialize command shell with service delegation"""
        self.config = config
        self.memory_overrides = memory_overrides or {}
        
        # Initialize services (commands.py delegates to these)
        self.help_service = HelpService()
        self.health_service = HealthService(config)
        self.analysis_service = AnalysisService(config, memory_overrides)
    
    async def handle_help(self, command: Optional[str] = None) -> None:
        """
        Handle help command - delegates to HelpService.
        commands.py --> helpservice - gets help output
        """
        try:
            if command == "analyze":
                help_text = self.help_service.get_analyze_help()
            elif command == "health":
                help_text = self.help_service.get_health_help()
            else:
                help_text = self.help_service.get_general_help()
            
            print(help_text)
            
        except Exception as e:
            logger.error(f"Help command failed: {e}")
            print(f"Help failed: {str(e)}")
    
    async def handle_health(self, verbose: bool = False) -> None:
        """
        Handle health command - delegates to HealthService.
        commands.py --> healthservice - gets health output
        """
        try:
            # Delegate to HealthService
            health_results = self.health_service.perform_health_check(verbose)
            
            # Format and display results
            formatted_output = self.health_service.format_health_results(health_results, verbose)
            print(formatted_output)

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            print(f"Health check failed: {str(e)}")

    async def handle_analyze_repository(
        self, 
        repo_path_or_url: str,
        to_version: str = "21",
        scope: str = "all-deprecations",
        log_level: int = 2,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Handle single repository analysis - delegates to AnalysisService.
        commands.py --> analyze - hands off to analysis service
        analysisService-> outputservice- creates the output-->feedback to commands.py
        """
        try:
            # Show analysis start
            repo_name = self._extract_repo_name(repo_path_or_url)
            print(f"Starting analysis: {repo_name}")
            
            # Delegate to AnalysisService
            result = await self.analysis_service.analyze_single_repository(
                repo_path_or_url, to_version, scope, log_level
            )
            
            if result:
                # Output already handled by main orchestrator
                # Show completion
                total_issues = len(result['analysis_result']) if isinstance(result['analysis_result'], list) else len(result['analysis_result'].get('findings', []))
                print(f"Analysis complete: {total_issues} issues found")
                
                # Handle cleanup info
                if result.get('cleanup_path'):
                    print(f"Clone retained at: {result['cleanup_path']}")
            
            return result

        except Exception as e:
            logger.error(f"Repository analysis failed: {e}")
            print(f"Analysis failed: {str(e)}")
            return None
    
    async def handle_analyze_organization(
        self,
        org_name: str,
        to_version: str = "21",
        scope: str = "all-deprecations",
        max_repos: int = 50,
        log_level: int = 2,
        provider: str = "github",
        keep_clones: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Handle organization analysis - delegates to AnalysisService.
        commands.py --> analyze - hands off to analysis service
        analysisService-> outputservice- creates the output-->feedback to commands.py
        AnalysisService--> progress reporter service- creates progress report-->feedback to commands.py
        """
        try:
            # Show analysis start
            print(f"Starting organization analysis: {org_name} (up to {max_repos} repos)")
            
            # Delegate to AnalysisService
            result = await self.analysis_service.analyze_organization(
                org_name, to_version, scope, max_repos, log_level, provider, keep_clones
            )
            
            if result:
                # Output already handled by main orchestrator
                
                # Handle cleanup info
                if result.get('cleanup_info'):
                    cleanup_info = result['cleanup_info']
                    print(f"Clones retained in: {cleanup_info['parent_dir']}")
                    print(f"Total repositories: {cleanup_info['repo_count']}")
                elif not keep_clones:
                    print("Cleanup: Temporary clones removed automatically")
            
            return result
            
        except Exception as e:
            logger.error(f"Organization analysis failed: {e}")
            print(f"Organization analysis failed: {str(e)}")
            return None

    def _extract_repo_name(self, repo_path_or_url: str) -> str:
        """Extract repository name from path or URL"""
        if repo_path_or_url.startswith(("http://", "https://", "git@")):
            return repo_path_or_url.split("/")[-1].replace(".git", "")
        else:
            from pathlib import Path
            return Path(repo_path_or_url).name


# Legacy compatibility functions for main.py
async def health_check(config: Dict[str, Any]) -> None:
    """Legacy compatibility wrapper"""
    commands = GraphShiftCommands(config)
    await commands.handle_health(verbose=False)


def load_configuration() -> Dict[str, Any]:
    """Load configuration and set GraphShift base directory"""
    import os
    from pathlib import Path
    
    try:
        from core.config_manager import ConfigManager
        config_manager = ConfigManager()
        
        # Set base directory to GraphShift package location
        package_dir = Path(__file__).parent.parent  # discovery/ directory
        original_cwd = os.getcwd()
        
        # Change to package directory for all operations
        os.chdir(package_dir)
        logger.info(f"GraphShift base directory set to: {package_dir}")
        
        # Load config file (now relative to package dir)
        config_path = "config/config.yaml"
        success, error = config_manager.load_config(config_path)
        
        if not success:
            logger.warning(f"Failed to load config file: {error}")
            return _get_default_config()
        
        # Get configuration
        if hasattr(config_manager, 'get_config'):
            config = config_manager.get_config()
        elif hasattr(config_manager, 'config'):
            config = config_manager.config
        else:
            return _get_default_config()
        
        # Add base directory info to config for reference
        config['_graphshift_base_dir'] = str(package_dir)
        config['_original_cwd'] = original_cwd
        
        return config
        
    except Exception as e:
        logger.warning(f"Failed to load configuration: {e}")
        return _get_default_config()


def _get_default_config() -> Dict[str, Any]:
    """Get default configuration"""
    return {
        "graphshift": {
            "jar": {
                "path": "resources/gs-analyzer.jar",
                "memory": "2g",
                "initial_memory": "512m"
            },
            "analysis": {
                "max_concurrent_repos": 5
            }
        }
    }


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )