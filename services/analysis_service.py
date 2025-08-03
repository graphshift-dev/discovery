"""
Analysis Service - Clean architecture with no duplication.
Two cases: single repo or org
Local/remote determination happens at abstract level.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .base_analyzer import BaseAnalyzer
from .clone_service import CloneService

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Clean analysis service with unified architecture.
    
    Architecture Pattern:
    Phase 1: Discovery (local vs remote) → Phase 2: Unified Analysis → Phase 3: Cleanup
    
    Single Repo: local/remote determination → base repo analyzer
    Organization: local/remote discovery → normalized data structure → unified parallel analysis
    
    No code duplication after discovery phase.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_analyzer = BaseAnalyzer(config)
        self.clone_service = CloneService(config)
        
        analysis_config = config.get("graphshift", {}).get("analysis", {})
        self.max_concurrent_repos = analysis_config.get("max_concurrent_repos", 5)
    
    async def run_analysis(
        self,
        repo_path: Optional[str] = None,
        org_name: Optional[str] = None,
        to_version: str = "21",
        scope: str = "all-deprecations",
        max_repos: int = 50,
        keep_clones: bool = True,
        provider: str = "github",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Main analysis method - only two cases: single repo or org.
        Local/remote determination happens at abstract level.
        """
        try:
            if repo_path:
                # Single repo case
                return await self._analyze_single_repo(
                    repo_path, to_version, scope, progress_callback
                )
            elif org_name:
                # Organization case
                return await self._analyze_organization(
                    org_name, to_version, scope, max_repos, keep_clones, 
                    provider, progress_callback
                )
            else:
                raise ValueError("Must provide either repo_path or org_name")
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return None
    
    async def _analyze_single_repo(
        self,
        repo_path: str,
        to_version: str,
        scope: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Single repo analysis - handles both local and remote at abstract level.
        """
        # Abstract level: local/remote determination
        is_local = self._is_local_path(repo_path)
        
        if is_local:
            # Local repo
            local_path = Path(repo_path).resolve()
            repo_name = local_path.name
            cleanup_path = None
            
            if progress_callback:
                progress_callback(f"Analyzing local repository: {repo_name}")
        else:
            # Remote repo - clone first
            if progress_callback:
                progress_callback("Cloning remote repository")
            
            clone_result = await self.clone_service.clone_single_repository(repo_path)
            if not clone_result:
                raise Exception(f"Failed to clone repository: {repo_path}")
            
            local_path = clone_result
            repo_name = self._extract_repo_name(repo_path)
            cleanup_path = clone_result
            
            if progress_callback:
                progress_callback(f"Analyzing cloned repository: {repo_name}")
        
        # Base level: repo analyzer (same for both local/remote)
        result = await self._base_repo_analyzer(
            str(local_path), repo_name, to_version, scope, progress_callback
        )
        
        # Add metadata
        result.update({
            'type': 'single_repo',
            'repos_analyzed': 1,
            'cleanup_path': cleanup_path
        })
        
        return result
    
    async def _analyze_organization(
        self,
        org_name: str,
        to_version: str,
        scope: str,
        max_repos: int,
        keep_clones: bool,
        provider: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Organization analysis - unified architecture after discovery phase.
        Local/remote discovery → normalized data structure → unified analysis.
        """
        # Phase 1: Discovery - only difference between local/remote
        org_path = Path(org_name)
        is_local = org_path.exists() and org_path.is_dir()
        
        if is_local:
            # Local discovery: scan directories
            if progress_callback:
                progress_callback(f"Discovering repositories in local directory: {org_name}")
            
            repo_items = self._discover_local_repos(org_path, max_repos)
            cleanup_paths = None
            
        else:
            # Remote discovery: fetch and clone repositories
            if progress_callback:
                progress_callback(f"Discovering repositories in remote organization: {org_name}")
            
            repo_items = await self._discover_and_clone_remote_repos(
                org_name, provider, max_repos, progress_callback
            )
            
            # Handle cleanup paths for display
            if not keep_clones:
                cleanup_paths = None  # Will be cleaned up
            else:
                cleanup_paths = [item['local_path'] for item in repo_items if item.get('success')]
        
        if not repo_items:
            raise Exception(f"No Java repositories found in {org_name}")
        
        # Phase 2: Unified Analysis - same for all repo types
        if progress_callback:
            progress_callback(f"Starting parallel analysis of {len(repo_items)} repositories")
        
        analysis_results = await self._parallel_repo_analysis(
            repo_items, to_version, scope, progress_callback
        )
        
        # Phase 3: Cleanup - only for remote repos if not keeping clones
        remote_repos = [item for item in repo_items if not item.get('is_local', True)]
        if remote_repos and not keep_clones:
            await self._cleanup_cloned_repos(remote_repos)
        
        # Aggregate results
        total_issues = sum(len(r.get('findings', [])) for r in analysis_results)
        
        return {
            'type': 'organization',
            'organization': org_name,
            'repositories': analysis_results,
            'total_issues': total_issues,
            'repos_analyzed': len(analysis_results),
            'cleanup_paths': cleanup_paths
        }
    
    async def _base_repo_analyzer(
        self,
        local_path: str,
        repo_name: str,
        to_version: str,
        scope: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Base repo analyzer - core analysis logic used by both single repo and org.
        No duplication - same logic for all cases.
        """
        if progress_callback:
            progress_callback(f"Running analysis on {repo_name}")
        
        # Run JAR analysis
        raw_result = await self.base_analyzer.analyze_directory(
            local_path, to_version, scope
        )
        
        if not raw_result:
            raise Exception(f"JAR analysis failed for {repo_name}")
        
        # Normalize result format
        if isinstance(raw_result, list):
            findings = raw_result
        else:
            findings = raw_result.get('findings', [])
        
        if progress_callback:
            progress_callback(f"Analysis complete: {len(findings)} issues found in {repo_name}")
        
        return {
            'repository': repo_name,
            'findings': findings,
            'total_issues': len(findings)
        }
    
    def _discover_local_repos(self, org_path: Path, max_repos: int) -> List[Dict[str, Any]]:
        """Discover local Java repositories - normalized format"""
        repo_items = []
        for item in org_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it's a Java repository
                java_files = list(item.rglob("*.java"))
                if java_files:
                    # Normalize to same format as remote repos
                    repo_items.append({
                        'local_path': item,
                        'repo_name': item.name,
                        'success': True,
                        'is_local': True
                    })
                    if len(repo_items) >= max_repos:
                        break
        return repo_items
    
    async def _discover_and_clone_remote_repos(
        self,
        org_name: str,
        provider: str,
        max_repos: int,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        """Discover and clone remote repositories"""
        from .scm_service import create_scm_service
        scm_service = create_scm_service(self.config)
        
        # Discover repositories
        all_repos, error = await scm_service.list_org_repos(org_name, provider, max_repos)
        if error or not all_repos:
            raise Exception(f"Failed to discover repositories: {error}")
        
        # Filter to Java repositories
        java_repos = scm_service.filter_java_repos(all_repos)[:max_repos]
        if not java_repos:
            raise Exception(f"No Java repositories found in {org_name}")
        
        if progress_callback:
            progress_callback(f"Cloning {len(java_repos)} repositories")
        
        # Clone repositories
        clone_results = await self.clone_service.clone_organization_repositories(
            java_repos, org_name, self.max_concurrent_repos
        )
        
        # Add is_local flag for consistency with local repos
        successful_clones = []
        for c in clone_results:
            if c['success']:
                c['is_local'] = False  # Mark as remote
                successful_clones.append(c)
        
        return successful_clones
    
    async def _parallel_repo_analysis(
        self,
        repo_items: List[Dict[str, Any]],
        to_version: str,
        scope: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Parallel repo analysis - unified logic for both local and remote.
        All repo_items now have the same normalized structure.
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_repos)
        
        async def analyze_single_item(item: Dict[str, Any]):
            async with semaphore:
                try:
                    # Unified handling - all items have same structure now
                    local_path = str(item['local_path'])
                    repo_name = item['repo_name']
                    
        
                    
                    # Same base repo analyzer for all cases
                    result = await self._base_repo_analyzer(
                        local_path, repo_name, to_version, scope, progress_callback
                    )
                    
        
                    return result
                    
                except Exception as e:
                    print(f"DEBUG: Analysis failed for {repo_name}: {e}")
                    logger.error(f"Analysis failed for {repo_name}: {e}")
                    return None
        
        # Execute parallel analysis
        tasks = [analyze_single_item(item) for item in repo_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        analysis_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Analysis task failed: {result}")
            elif result:
                analysis_results.append(result)
        
        return analysis_results
    
    async def _cleanup_cloned_repos(self, clone_results: List[Dict[str, Any]]):
        """Cleanup cloned repositories"""
        await self.clone_service.cleanup_cloned_repositories(clone_results)
    
    def _is_local_path(self, path_or_url: str) -> bool:
        """Determine if path is local or remote URL"""
        if path_or_url.startswith(("http://", "https://", "git@")):
            return False
        
        try:
            return Path(path_or_url).resolve().exists()
        except (OSError, ValueError):
            return False
    
    def _extract_repo_name(self, repo_path_or_url: str) -> str:
        """Extract repository name from path or URL"""
        if repo_path_or_url.startswith(("http://", "https://", "git@")):
            return repo_path_or_url.split("/")[-1].replace(".git", "")
        else:
            return Path(repo_path_or_url).name