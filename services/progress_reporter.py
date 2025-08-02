import time
import sys
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

class OperationType(Enum):
    """Types of operations that can be tracked"""
    SINGLE_REPO = "single_repo"
    MULTI_REPO = "multi_repo" 
    ORGANIZATION = "organization"
    AST_PARSING = "ast_parsing"
    PATTERN_MATCHING = "pattern_matching"

@dataclass
class OperationStats:
    """Universal operation statistics"""
    operation_type: OperationType
    operation_name: str = ""
    total_items: int = 0
    completed_items: int = 0
    current_item: str = ""
    
    # Timing
    start_time: float = 0.0
    
    # Results (flexible for any operation type)
    results: Dict[str, Any] = None
    
    # Errors
    errors: int = 0
    
    def __post_init__(self):
        if self.results is None:
            self.results = {}

class ProgressReporter:
    """Universal progress reporter with consistent interface"""
    
    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        self.current_operation: Optional[OperationStats] = None
        self._last_dashboard_update = 0
        self._dashboard_interval = 60  # Update every 60 seconds
        self._dashboard_shown = False
        
    def start_operation(self, operation_type: OperationType, operation_name: str, total_items: int = 1, **kwargs) -> None:
        """Start any type of operation with unified interface"""
        if self.quiet:
            return
            
        self.current_operation = OperationStats(
            operation_type=operation_type,
            operation_name=operation_name,
            total_items=total_items,
            start_time=time.time()
        )
        
        # Store additional context in results
        if kwargs:
            self.current_operation.results.update(kwargs)
        
        # Display based on operation type
        if operation_type == OperationType.SINGLE_REPO:
            # Skip printing here - CLI output service handles this
            pass
        elif operation_type == OperationType.ORGANIZATION:
            parallel_threads = kwargs.get('parallel_threads', 5)
            print(f"GraphShift Organization Analysis: {operation_name}")
            print(f"Total Repositories Found: {total_items}")
            print(f"Parallel Threads: {parallel_threads}")
            print("=" * 60)
            self._show_dashboard(force=True)
            self._last_dashboard_update = time.time()
        elif operation_type == OperationType.MULTI_REPO:
            print(f"Analyzing {total_items} repositories...")
        elif operation_type == OperationType.AST_PARSING:
            if total_items > 0:
                print(f"  Parsing {total_items} files...", end="", flush=True)
        # Pattern matching starts silently
    
    def update_progress(self, current_item: int, total_items: int = None, current_item_name: str = "") -> None:
        """Update progress for any operation type"""
        if not self.current_operation:
            return
            
        self.current_operation.completed_items = current_item
        if total_items is not None:
            self.current_operation.total_items = total_items
        if current_item_name:
            self.current_operation.current_item = current_item_name
        
        # Handle display based on operation type
        if self.current_operation.operation_type == OperationType.ORGANIZATION:
            # Only update dashboard every 60 seconds for org analysis
            now = time.time()
            if (now - self._last_dashboard_update) >= self._dashboard_interval:
                self._show_dashboard()
                self._last_dashboard_update = now
        elif self.current_operation.operation_type == OperationType.AST_PARSING:
            # Show progress every 50 files or every 30 seconds
            if (not self.quiet and 
                (current_item % 50 == 0 or (time.time() - self.current_operation.start_time) % 30 < 1)):
                self._show_ast_progress(current_item_name)
        elif self.current_operation.operation_type == OperationType.MULTI_REPO:
            if not self.quiet:
                print(f"  Completed {current_item}/{self.current_operation.total_items}: {current_item_name}")
    
    def _show_dashboard(self, force: bool = False):
        """Show time-based dashboard for organization analysis"""
        if self.quiet or not self.current_operation:
            return
        
        # Clear previous dashboard
        if self._dashboard_shown and not force:
            sys.stdout.write('\033[8A\033[J')
        
        # Calculate timing
        elapsed = time.time() - self.current_operation.start_time
        elapsed_minutes = int(elapsed // 60)
        elapsed_seconds = int(elapsed % 60)
        
        # Estimate remaining time
        if self.current_operation.completed_items > 0:
            avg_time_per_item = elapsed / self.current_operation.completed_items
            remaining_items = self.current_operation.total_items - self.current_operation.completed_items
            estimated_remaining = avg_time_per_item * remaining_items
            remaining_minutes = int(estimated_remaining // 60)
            eta_str = f"{remaining_minutes}m"
        else:
            eta_str = "calculating..."
        
        # Progress bar
        progress_bar = self._create_progress_bar(
            self.current_operation.completed_items, 
            self.current_operation.total_items, 
            40
        )
        
        # Dashboard display
        print(f"Organization: {self.current_operation.operation_name}")
        print(f"Repos Completed: {self.current_operation.completed_items}/{self.current_operation.total_items}")
        print(f"Current Repo: {self.current_operation.current_item}")
        
        # Show file counts if available in results
        total_files = self.current_operation.results.get('total_files_scanned', 0)
        current_files = self.current_operation.results.get('files_in_current_repo', 0)
        if total_files > 0:
            print(f"Files Scanned Total: {total_files:,}")
            print(f"Files in Current Repo: {current_files}")
        
        print(f"Time Elapsed: {elapsed_minutes}m {elapsed_seconds}s")
        
        # Only show ETA if we have meaningful progress data
        if self.current_operation.completed_items > 0 and eta_str != "calculating...":
            print(f"Estimated Time Remaining: {eta_str}")
            
        print(f"Progress: {progress_bar}")
        
        sys.stdout.flush()
        self._dashboard_shown = True
    
    def _show_ast_progress(self, current_file_name: str):
        """Show AST parsing progress"""
        if not self.current_operation:
            return
            
        current = self.current_operation.completed_items
        total = self.current_operation.total_items
        
        # Calculate time estimation
        elapsed = time.time() - self.current_operation.start_time
        if current > 0:
            avg_time_per_file = elapsed / current
            remaining_files = total - current
            estimated_remaining = avg_time_per_file * remaining_files
            remaining_minutes = int(estimated_remaining // 60)
            remaining_seconds = int(estimated_remaining % 60)
            
            if remaining_minutes > 0:
                time_str = f"{remaining_minutes}m{remaining_seconds}s"
            else:
                time_str = f"{remaining_seconds}s"
        else:
            time_str = "calculating..."
        
        # Show clean progress with time estimation
        progress_bar = self._create_progress_bar(current, total, 25)
        file_name_short = Path(current_file_name).name if current_file_name else ""
        print(f"\r  {progress_bar} ({current}/{total}) {file_name_short} ~{time_str}", 
              end="", flush=True)
    
    def _create_progress_bar(self, current: int, total: int, width: int = 40) -> str:
        """ASCII progress bar"""
        if total == 0:
            return "[" + "#" * width + "] 100%"
        
        filled = int(width * current / total)
        bar = "#" * filled + "-" * (width - filled)
        percentage = int(100 * current / total)
        return f"[{bar}] {percentage}%"
    
    def complete_operation(self, duration: float = None, results: Dict[str, Any] = None) -> None:
        """Complete any type of operation with unified interface"""
        if self.quiet or not self.current_operation:
            return
            
        # Calculate duration if not provided
        if duration is None:
            duration = time.time() - self.current_operation.start_time
            
        # Store results
        if results:
            self.current_operation.results.update(results)
        
        # Display based on operation type
        if self.current_operation.operation_type == OperationType.SINGLE_REPO:
            total_issues = results.get('total_migration_issues', 0) if results else 0
            print(f"Analysis complete: {total_issues} migration issues found ({duration:.1f}s)")
            
        elif self.current_operation.operation_type == OperationType.ORGANIZATION:
            self._complete_org_analysis(duration, results)
            
        elif self.current_operation.operation_type == OperationType.MULTI_REPO:
            total_repos = self.current_operation.completed_items
            print(f"Analysis for all {self.current_operation.total_items} repositories completed")
            print(f"Successfully analyzed: {total_repos}/{self.current_operation.total_items} repositories")
            
        elif self.current_operation.operation_type == OperationType.AST_PARSING:
            methods_found = results.get('methods_found', 0) if results else 0
            print(f"  Parsing complete: {methods_found} methods ({duration:.1f}s)")
            
        elif self.current_operation.operation_type == OperationType.PATTERN_MATCHING:
            matches_found = results.get('matches_found', 0) if results else 0
            print(f"  Pattern matching complete: {matches_found} issues found ({duration:.1f}s)")
        
        # Clear current operation
        self.current_operation = None
    
    def _complete_org_analysis(self, duration: float, results: Dict[str, Any] = None):
        """Complete organization analysis with detailed summary"""
        elapsed_minutes = int(duration // 60)
        elapsed_seconds = int(duration % 60)
        
        # Clear dashboard
        if self._dashboard_shown:
            sys.stdout.write('\033[8A\033[J')
        
        print("=" * 60)
        print(f"Organization Analysis Complete!")
        
        total_repos_analyzed = self.current_operation.completed_items
        total_repos_found = self.current_operation.total_items
        
        repos_display = f"{total_repos_analyzed}/{total_repos_found}" if total_repos_found > 0 else str(total_repos_analyzed)
        
        print(f"Repositories Analyzed: {repos_display}")
        
        if results:
            total_files = results.get('total_files_scanned', 0)
            total_issues = results.get('total_migration_issues', 0)
            if total_files > 0:
                print(f"Total Files Scanned: {total_files:,}")
            if total_issues > 0:
                print(f"Total Migration Issues: {total_issues:,}")
        
        print(f"Total Time: {elapsed_minutes}m {elapsed_seconds}s")
    
    # Legacy methods for backward compatibility
    def report_progress(self, message: str):
        """Report general progress message"""
        if self.verbose and not self.quiet:
            print(f"  {message}")
    
    def report_error(self, error_msg: str):
        """Report error message"""
        if self.current_operation:
            self.current_operation.errors += 1
        if not self.quiet:
            print(f"Error: {error_msg}")
    
    def report_discovery(self, files_found: int, dirs_scanned: int):
        """Report file discovery progress"""
        if self.current_operation:
            self.current_operation.results['total_files_scanned'] = self.current_operation.results.get('total_files_scanned', 0) + files_found
        if not self.quiet and files_found > 0:
            print(f"  Discovered {files_found} Java files in {dirs_scanned} directories")
    
    def report_analysis_start(self, total_files: int, total_patterns: int):
        """Report start of analysis - required by kb_analyzer_service"""
        pass  # Silent start
    
    def report_analysis_complete(self, total_matches: int, analysis_time: float):
        """Report analysis completion"""
        if not self.quiet:
            print(f"Analysis complete: {total_matches} migration issues found ({analysis_time:.1f}s)")

def create_progress_reporter(verbose: bool = False, quiet: bool = False) -> ProgressReporter:
    """Create progress reporter instance"""
    return ProgressReporter(verbose=verbose, quiet=quiet) 