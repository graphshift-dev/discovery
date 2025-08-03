#!/usr/bin/env python3
"""
GraphShift Main Orchestrator
Responsibilities:
1. Orchestration (workflow management)
2. CLI feedback (progress, status, results)
3. Hand off to services (analysis, output formatting)

"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class MainOrchestrator:

    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("graphshift.main")
    
    async def orchestrate_analysis(
        self,
        repo_path: Optional[str] = None,
        org_name: Optional[str] = None,
        to_version: str = "21",
        scope: str = "all-deprecations",
        max_repos: int = 500,
        keep_clones: bool = True,
        provider: str = "github"
    ) -> bool:
        """
        Main orchestration method - manages the entire workflow.
        Returns success/failure for CLI exit codes.
        """
        try:
            # Import services (lazy loading)
            from services.analysis_service import AnalysisService
            from services.output_formatter import OutputFormatter
            
            # Initialize services
            analysis_service = AnalysisService(self.config)
            output_formatter = OutputFormatter(self.config)
            
            # CLI Feedback: Starting
            if repo_path:
                self._print_starting_repo(repo_path)
            else:
                self._print_starting_org(org_name, max_repos)
            
            # Hand off to Analysis Service
            analysis_result = await analysis_service.run_analysis(
                repo_path=repo_path,
                org_name=org_name,
                to_version=to_version,
                scope=scope,
                max_repos=max_repos,
                keep_clones=keep_clones,
                provider=provider,
                progress_callback=self._print_progress
            )
            
            if not analysis_result:
                self._print_failed("Analysis failed")
                return False
            
            # CLI Feedback: Analysis Complete
            self._print_analysis_complete(analysis_result)
            
            # Hand off to Output Formatter
            output_result = await output_formatter.format_and_save(
                analysis_result=analysis_result,
                is_organization=bool(org_name)
            )
            
            # CLI Feedback: Files Saved
            self._print_files_saved(output_result)
            
            # CLI Feedback: Success
            self._print_success()
            return True
            
        except KeyboardInterrupt:
            self._print_cancelled()
            return False
        except Exception as e:
            self._print_failed(str(e))
            self.logger.error(f"Orchestration failed: {e}", exc_info=True)
            return False
    
    async def orchestrate_health_check(self, verbose: bool = False) -> bool:
        """Orchestrate health check workflow"""
        try:
            from services.health_service import HealthService
            
            self._print_health_starting()
            
            health_service = HealthService(self.config)
            health_result = health_service.perform_health_check(verbose)
            
            self._print_health_result(health_result, verbose)
            
            return health_result['overall_status'] == 'healthy'
            
        except Exception as e:
            self._print_failed(f"Health check failed: {str(e)}")
            return False
    
    def _print_starting_repo(self, repo_path: str):
        """CLI Feedback: Starting repository analysis"""
        print(f"Starting analysis: {repo_path}")
    
    def _print_starting_org(self, org_name: str, max_repos: int):
        """CLI Feedback: Starting organization analysis"""
        print(f"Starting organization analysis: {org_name} (up to {max_repos} repos)")
    
    def _print_progress(self, message: str):
        """CLI Feedback: Progress updates from analysis service"""
        print(f"Progress: {message}")
    
    def _print_analysis_complete(self, analysis_result: Dict[str, Any]):
        """CLI Feedback: Analysis completed"""
        total_issues = analysis_result.get('total_issues', 0)
        repos_analyzed = analysis_result.get('repos_analyzed', 1)
        print(f"Analysis complete: {total_issues} issues found across {repos_analyzed} repositories")
    
    def _print_files_saved(self, output_result: Dict[str, Any]):
        """CLI Feedback: Files saved"""
        files_saved = output_result.get('files_saved', [])
        total_files = len(files_saved)
        
        # Show file paths for both single repo and organization
        if output_result.get('type') == 'organization':
            repos_processed = output_result.get('repositories_processed', 0)
            print(f"Reports saved: {total_files} files ({repos_processed} repositories + organization summary)")
        else:
            print(f"Reports saved: {total_files} files")
        
        # Show file paths only for single repo analysis
        if output_result.get('type') != 'organization':
            for file_path in files_saved:
                print(f"  • {file_path}")
    
    def _print_cloning_phase(self, repo_count: int, phase: str = "start"):
        """CLI Feedback: Cloning phase messages"""
        if phase == "start":
            print(f"\nCloning Phase: Downloading {repo_count} repositories...")
        elif phase == "success":
            print(f"Successfully cloned {repo_count} repositories")
        elif phase == "analysis_start":
            print(f"\nAnalysis Phase: Analyzing cloned repositories...")
    
    def _print_error(self, message: str):
        """CLI Feedback: Error messages"""
        print(f"Error: {message}")
    
    def _print_kept_clones_info(self, org_name: str, parent_dir: str, repo_count: int):
        """CLI Feedback: Information about kept clones"""
        print(f"\nClones retained in: {parent_dir}")
        print(f"Total repositories: {repo_count}")
    
    def _print_cleanup_message(self, is_auto: bool = False):
        """CLI Feedback: Cleanup messages"""
        if is_auto:
            print("Cleanup: Temporary clones removed automatically")
    
    def _print_health_starting(self):
        """CLI Feedback: Health check starting"""
        print("Running system health check...")
    
    def _print_health_result(self, health_result: Dict[str, Any], verbose: bool):
        """CLI Feedback: Health check results"""
        status = health_result['overall_status'].upper()
        print(f"System Health: {status}")
        
        if verbose:
            for check in health_result.get('checks', []):
                status_icon = "✓" if check['passed'] else "✗"
                print(f"  {status_icon} {check['name']}: {check['message']}")
    
    def _print_success(self):
        """CLI Feedback: Operation successful"""
        print("Operation completed successfully")
        print("Visit https://docs.graphshift.dev for extensive real world examples to remediate all your deprecations")
    
    def _print_failed(self, reason: str):
        """CLI Feedback: Operation failed"""
        print(f"Operation failed: {reason}")
    
    def _print_cancelled(self):
        """CLI Feedback: Operation cancelled"""
        print("Operation cancelled by user")
    
    async def orchestrate_config_command(self, action: str) -> bool:
        """Handle config command"""
        from pathlib import Path
        import subprocess
        import os
        
        # Get user's config file path
        try:
            user_config_file = Path.home() / ".graphshift" / "config.yaml"
            if user_config_file.exists():
                import yaml
                with open(user_config_file, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    base_dir = user_config.get('base_directory')
                    if base_dir:
                        config_file = Path(base_dir) / "config" / "config.yaml"
                    else:
                        config_file = None
            else:
                config_file = None
        except Exception:
            config_file = None
        
        if not config_file or not config_file.exists():
            print("GraphShift not initialized or config file not found.")
            print("Run 'graphshift init' first to set up your working directory.")
            return False
        
        if action == "edit":
            # Try to open with system default editor
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(str(config_file))
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', str(config_file)])
                print(f"Opened config file: {config_file}")
                return True
            except Exception as e:
                print(f"Could not open editor: {e}")
                print(f"Please manually edit: {config_file}")
                return False
                
        elif action == "show":
            # Display current config
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                print("Current GraphShift Configuration:")
                print("=" * 40)
                print(content)
                return True
            except Exception as e:
                print(f"Could not read config file: {e}")
                return False
                
        elif action == "path":
            # Show config file path
            print(f"Config file location: {config_file}")
            return True
            
        else:
            print("Available config actions: edit, show, path")
            return False


def create_argument_parser() -> argparse.ArgumentParser:
    """Create clean argument parser - just the essentials"""
    parser = argparse.ArgumentParser(
        prog="graphshift",
        description="GraphShift - Java Migration Analysis Tool",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", 
        help="Analyze Java repositories",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
    )
    analyze_group = analyze_parser.add_mutually_exclusive_group(required=True)
    analyze_group.add_argument("--repo", help="Single repository URL")
    analyze_group.add_argument("--local-path", help="Local repository path")
    analyze_group.add_argument("--org", help="Organization name")
    analyze_group.add_argument("--local-org", help="Local organization directory")
    
    analyze_parser.add_argument("--to-version", choices=["8", "11", "17", "21"], default="21", help="Target JDK version")
    analyze_parser.add_argument("--scope", choices=["upgrade-blockers", "all-deprecations"], default="all-deprecations", help="Analysis scope")
    analyze_parser.add_argument("--max-repos", type=int, default=500, help="Maximum repositories to analyze")
    analyze_parser.add_argument("--no-keep-clones", action="store_true", help="Delete clones after analysis")
    analyze_parser.add_argument("--provider", choices=["github", "gitlab", "bitbucket"], default="github", help="SCM provider")
    
    # Health command
    health_parser = subparsers.add_parser(
        "health", 
        help="Check system health",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
    )
    health_parser.add_argument("--verbose", action="store_true", help="Detailed health information")
    
    # Init command
    init_parser = subparsers.add_parser(
        "init", 
        help="Initialize GraphShift configuration",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
    )
    init_parser.add_argument("--base-dir", help="Base directory for GraphShift files")
    
    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Manage GraphShift configuration",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
    )
    config_subparsers = config_parser.add_subparsers(dest='config_action', help='Configuration actions')
    
    # config edit
    config_edit_parser = config_subparsers.add_parser('edit', help='Open config file for editing')
    
    # config show
    config_show_parser = config_subparsers.add_parser('show', help='Show current configuration')
    
    # config path
    config_path_parser = config_subparsers.add_parser('path', help='Show config file path')
    
    # Global options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--config", help="Configuration file path")
    
    return parser


async def main():
    """Clean main function - just argument parsing and orchestration routing"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Initialization check is now handled in cli_entry_point()
    
    # Load configuration
    try:
        from cli.commands import load_configuration
        config = load_configuration()
    except Exception as e:
        print(f"Configuration error: {e}")
        return False
    
    # Initialize orchestrator
    orchestrator = MainOrchestrator(config)
    
    # Route to appropriate orchestration method
    if args.command == "analyze":
        # Determine analysis type and parameters
        repo_path = args.repo or args.local_path
        org_name = args.org or args.local_org
        keep_clones = not args.no_keep_clones
        
        success = await orchestrator.orchestrate_analysis(
            repo_path=repo_path,
            org_name=org_name,
            to_version=args.to_version,
            scope=args.scope,
            max_repos=args.max_repos,
            keep_clones=keep_clones,
            provider=args.provider
        )
        
    elif args.command == "health":
        success = await orchestrator.orchestrate_health_check(args.verbose)
        
    elif args.command == "init":
        from core.initialization import initialize_graphshift
        success = initialize_graphshift(args.base_dir)
        
    elif args.command == "config":
        success = await orchestrator.orchestrate_config_command(args.config_action)
        
    else:
        parser.print_help()
        return False
    
    return success


def cli_entry_point():
    """Entry point for console scripts"""
    try:
        # Check if this is the init command before doing initialization check
        if len(sys.argv) > 1 and sys.argv[1] == "init":
            # Skip initialization check for init command
            pass
        else:
            # Ensure GraphShift is initialized for all other commands (including --help)
            from core.initialization import ensure_initialized
            if not ensure_initialized():
                sys.exit(1)
        
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        # Give asyncio time to cleanup
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                # Cancel all running tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # Wait briefly for cleanup
                if pending:
                    loop.run_until_complete(asyncio.wait(pending, timeout=2.0))
        except Exception:
            pass  # Ignore cleanup errors
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_entry_point()