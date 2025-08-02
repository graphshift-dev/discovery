"""
Dedicated Clone Service - handles all repository cloning operations.
Clean separation of concerns following the ideal architecture diagram.
"""

import asyncio
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CloneService:
    """
    Dedicated service for repository cloning operations.
    
    Follows the ideal architecture - single responsibility for cloning,
    separate from analysis logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize clone service with configuration"""
        self.config = config
        # Use clones directory relative to base directory
        self.clone_base_dir = Path("clones")
        self.clone_base_dir.mkdir(parents=True, exist_ok=True)
    
    async def clone_single_repository(self, repo_url: str) -> Optional[Path]:
        """
        Clone a single repository for analysis.
        
        Args:
            repo_url: Repository URL to clone
            
        Returns:
            Path to cloned repository or None if failed
        """
        try:
            repo_name = self._extract_repo_name(repo_url)
            
            # Create clone directory in discovery/clones (not temp folder)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = self.clone_base_dir / f"graphshift_{repo_name}_{timestamp}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            clone_path = temp_dir / repo_name
            
            # Clone with minimal depth for faster analysis
            process = await asyncio.create_subprocess_exec(
                'git', 'clone', '--depth', '1', repo_url, str(clone_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.debug(f"Successfully cloned {repo_url} to {clone_path}")
                return clone_path
            else:
                logger.error(f"Failed to clone {repo_url}: {stderr.decode()}")
                # Cleanup failed clone
                await self._cleanup_directory(temp_dir)
                return None
                
        except Exception as e:
            logger.error(f"Clone operation failed for {repo_url}: {e}")
            return None
    
    async def clone_organization_repositories(
        self, 
        repositories: List[Any], 
        org_name: str,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Clone multiple repositories in parallel with proper concurrency control.
        
        Args:
            repositories: List of repository objects
            org_name: Organization name for directory structure
            max_concurrent: Maximum concurrent clone operations (parallel threads)
            
        Returns:
            List of clone results with success/failure info
        """
        logger.info(f"Starting parallel clone of {len(repositories)} repositories with {max_concurrent} concurrent threads")
        
        # Create organization-specific clone directory
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        org_clone_dir = self.clone_base_dir / f"{org_name}_{timestamp}"
        org_clone_dir.mkdir(parents=True, exist_ok=True)
        
        # Parallel cloning with semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        clone_tasks = []
        
        logger.debug(f"Creating {len(repositories)} parallel clone tasks")
        for repo in repositories:
            task = self._clone_single_repo_with_semaphore(
                repo, org_clone_dir, semaphore
            )
            clone_tasks.append(task)
        
        # Execute all cloning operations in parallel
        logger.debug(f"Executing {len(clone_tasks)} clone tasks in parallel")
        clone_results = await asyncio.gather(*clone_tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        successful_count = 0
        failed_count = 0
        
        for i, result in enumerate(clone_results):
            if isinstance(result, Exception):
                logger.error(f"Clone task failed for {repositories[i].name}: {result}")
                processed_results.append({
                    'success': False,
                    'repo_name': repositories[i].name,
                    'error': str(result),
                    'local_path': None,
                    'org_clone_dir': org_clone_dir
                })
                failed_count += 1
            else:
                processed_results.append(result)
                if result['success']:
                    successful_count += 1
                else:
                    failed_count += 1
        
        logger.info(f"Parallel cloning completed: {successful_count} successful, {failed_count} failed")
        return processed_results
    
    async def _clone_single_repo_with_semaphore(
        self, 
        repo: Any, 
        clone_dir: Path, 
        semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        """Clone single repository with concurrency control"""
        async with semaphore:
            try:
                repo_url = repo.clone_url or repo.url
                repo_name = repo.name
                clone_path = clone_dir / repo_name
                
                # Clone with minimal depth
                process = await asyncio.create_subprocess_exec(
                    'git', 'clone', '--depth', '1', repo_url, str(clone_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return {
                        'success': True,
                        'repo_name': repo_name,
                        'local_path': clone_path,
                        'error': None,
                        'org_clone_dir': clone_dir
                    }
                else:
                    return {
                        'success': False,
                        'repo_name': repo_name,
                        'local_path': None,
                        'error': stderr.decode(),
                        'org_clone_dir': clone_dir
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'repo_name': repo.name,
                    'local_path': None,
                    'error': str(e),
                    'org_clone_dir': clone_dir
                }
    
    async def cleanup_cloned_repositories(self, clone_results: List[Dict[str, Any]]) -> None:
        """Clean up cloned repositories after analysis"""
        # Get unique parent directories to remove
        parent_dirs = set()
        for clone_info in clone_results:
            if clone_info.get('org_clone_dir'):
                parent_dirs.add(clone_info['org_clone_dir'])
        
        # Remove parent directories
        for parent_dir in parent_dirs:
            await self._cleanup_directory(parent_dir)
    
    async def cleanup_single_clone(self, clone_path: Path) -> None:
        """Clean up a single cloned repository"""
        if clone_path and clone_path.exists():
            await self._cleanup_directory(clone_path.parent)
    
    async def _cleanup_directory(self, directory: Path) -> None:
        """Clean up a directory with Windows-safe approach"""
        try:
            if directory.exists():
                # Windows-safe cleanup: handle readonly files in .git
                import stat
                import os
                
                def handle_remove_readonly(func, path, exc):
                    """Handle readonly files during cleanup"""
                    if os.path.exists(path):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                
                shutil.rmtree(directory, onerror=handle_remove_readonly)
                logger.debug(f"Cleaned up directory: {directory}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {directory}: {e}")
    
    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        if repo_url.startswith(("http://", "https://", "git@")):
            return repo_url.split("/")[-1].replace(".git", "")
        else:
            return Path(repo_url).name
    
    def get_kept_clones_info(self, clone_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get information about kept clones for user display"""
        successful_clones = [c for c in clone_results if c['success']]
        if not successful_clones:
            return {'parent_dir': None, 'repo_count': 0}
        
        # Get parent directory from first successful clone
        parent_dir = successful_clones[0]['org_clone_dir']
        repo_count = len(successful_clones)
        
        return {
            'parent_dir': parent_dir,
            'repo_count': repo_count
        }