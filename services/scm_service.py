"""
SCM Service - Universal Source Control Management abstraction
Supports GitHub (cloud + enterprise), GitLab, and Bitbucket
"""

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import aiohttp

logger = logging.getLogger('graphshift.scm')

@dataclass
class Repository:
    """Universal repository information"""
    name: str
    full_name: str
    url: str
    clone_url: str
    language: Optional[str]
    size: int
    description: Optional[str]
    default_branch: str = "main"
    provider: str = "unknown"  # github, gitlab, bitbucket

class SCMProvider(ABC):
    """Abstract base class for SCM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session = None
        
    @abstractmethod
    async def list_org_repos(self, org_name: str, max_repos: int = 100) -> Tuple[List[Repository], Optional[str]]:
        """List repositories for an organization"""
        pass
    
    @abstractmethod
    async def get_repo_info(self, owner: str, repo: str) -> Tuple[Optional[Repository], Optional[str]]:
        """Get information about a specific repository"""
        pass
    
    @abstractmethod
    def parse_repo_url(self, repo_url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse repository URL to extract owner and repo name"""
        pass
    
    def filter_java_repos(self, repos: List[Repository]) -> List[Repository]:
        """Filter repositories to only include Java projects"""
        java_repos = []
        
        for repo in repos:
            # Check if language is Java or contains Java-related keywords
            if repo.language and 'java' in repo.language.lower():
                java_repos.append(repo)
            elif repo.description:
                desc_lower = repo.description.lower()
                java_keywords = ['java', 'spring', 'maven', 'gradle', 'jvm', 'kotlin']
                if any(keyword in desc_lower for keyword in java_keywords):
                    java_repos.append(repo)
        
        # Note: Filtering complete - ready for analysis
        return java_repos

class GitHubProvider(SCMProvider):
    """GitHub provider (supports both cloud and enterprise)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_base_url = config.get('api_base_url', 'https://api.github.com')
        self.rate_limit_threshold = config.get('rate_limit_threshold', 100)
        self.max_concurrent_requests = config.get('max_concurrent_requests', 10)
        
        # Get token from config (user must specify it)
        self.token = config.get('token')
        if not self.token:
            raise ValueError("GitHub token is required in config.yaml under scm.github.token")
        
        self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
    
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GraphShift-OSS/1.0.0',
            'Authorization': f'token {self.token}'
        }
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str) -> Tuple[Optional[Any], Optional[str]]:
        """Make a GitHub API request with rate limiting"""
        async with self._semaphore:
            try:
                url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
                logger.debug(f"GitHub API request: {url}")
                
                async with self.session.get(url) as response:
                    # Check rate limits
                    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                    if remaining < self.rate_limit_threshold:
                        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                        current_time = int(datetime.now().timestamp())
                        wait_time = max(0, reset_time - current_time)
                        
                        if wait_time > 0:
                            logger.warning(f"GitHub rate limit approaching. Waiting {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                    
                    if response.status == 200:
                        data = await response.json()
                        return data, None
                    elif response.status == 404:
                        return None, f"Not found: {endpoint}"
                    elif response.status == 403:
                        return None, "GitHub API rate limit exceeded or access denied"
                    else:
                        error_text = await response.text()
                        return None, f"GitHub API error {response.status}: {error_text}"
                        
            except asyncio.TimeoutError:
                return None, "GitHub API request timed out"
            except Exception as e:
                return None, f"GitHub API request failed: {str(e)}"
    
    async def list_org_repos(self, org_name: str, max_repos: int = 100) -> Tuple[List[Repository], Optional[str]]:
        """List repositories for a GitHub organization"""
        try:
            repos = []
            page = 1
            per_page = min(100, max_repos)  # GitHub API max is 100 per page
            
            while len(repos) < max_repos:
                endpoint = f"orgs/{org_name}/repos?type=public&sort=updated&per_page={per_page}&page={page}"
                data, error = await self._make_request(endpoint)
                
                if error:
                    return [], error
                
                if not data:  # Empty response means no more pages
                    break
                
                for repo_data in data:
                    if len(repos) >= max_repos:
                        break
                    
                    repo = Repository(
                        name=repo_data['name'],
                        full_name=repo_data['full_name'],
                        url=repo_data['html_url'],
                        clone_url=repo_data['clone_url'],
                        language=repo_data.get('language'),
                        size=repo_data.get('size', 0),
                        description=repo_data.get('description'),
                        default_branch=repo_data.get('default_branch', 'main'),
                        provider='github'
                    )
                    repos.append(repo)
                
                # If we got less than per_page results, we're done
                if len(data) < per_page:
                    break
                
                page += 1
            
            # Note: This is the fetched count, not the total org count
            return repos, None
            
        except Exception as e:
            return [], f"Failed to list GitHub organization repositories: {str(e)}"
    
    async def get_repo_info(self, owner: str, repo: str) -> Tuple[Optional[Repository], Optional[str]]:
        """Get information about a specific GitHub repository"""
        endpoint = f"repos/{owner}/{repo}"
        data, error = await self._make_request(endpoint)
        
        if error:
            return None, error
        
        repo_info = Repository(
            name=data['name'],
            full_name=data['full_name'],
            url=data['html_url'],
            clone_url=data['clone_url'],
            language=data.get('language'),
            size=data.get('size', 0),
            description=data.get('description'),
            default_branch=data.get('default_branch', 'main'),
            provider='github'
        )
        
        return repo_info, None
    
    def parse_repo_url(self, repo_url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse GitHub repository URL to extract owner and repo name"""
        try:
            # Handle various GitHub URL formats
            # https://github.com/owner/repo
            # https://github.com/owner/repo.git
            # git@github.com:owner/repo.git
            
            if 'github.com' not in repo_url:
                return None, None
            
            if repo_url.startswith('git@'):
                # SSH format: git@github.com:owner/repo.git
                parts = repo_url.split(':')[-1].replace('.git', '').split('/')
            else:
                # HTTPS format: https://github.com/owner/repo(.git)
                parts = repo_url.replace('.git', '').split('/')[-2:]
            
            if len(parts) >= 2:
                owner, repo = parts[-2], parts[-1]
                return owner, repo
            
            return None, None
            
        except Exception:
            return None, None

class GitLabProvider(SCMProvider):
    """GitLab provider (placeholder for future implementation)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_base_url = config.get('api_base_url', 'https://gitlab.com/api/v4')
        self.token = config.get('token')
        if not self.token:
            raise ValueError("GitLab token is required in config.yaml under scm.gitlab.token")
    
    async def list_org_repos(self, org_name: str, max_repos: int = 100) -> Tuple[List[Repository], Optional[str]]:
        """List repositories for a GitLab group"""
        # TODO: Implement GitLab API integration
        return [], "GitLab integration not yet implemented"
    
    async def get_repo_info(self, owner: str, repo: str) -> Tuple[Optional[Repository], Optional[str]]:
        """Get information about a specific GitLab repository"""
        # TODO: Implement GitLab API integration
        return None, "GitLab integration not yet implemented"
    
    def parse_repo_url(self, repo_url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse GitLab repository URL to extract owner and repo name"""
        # TODO: Implement GitLab URL parsing
        return None, None

class BitbucketProvider(SCMProvider):
    """Bitbucket provider (placeholder for future implementation)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_base_url = config.get('api_base_url', 'https://api.bitbucket.org/2.0')
        self.username = config.get('username')
        self.app_password = config.get('app_password')
        if not (self.username and self.app_password):
            raise ValueError("Bitbucket username and app_password are required in config.yaml")
    
    async def list_org_repos(self, org_name: str, max_repos: int = 100) -> Tuple[List[Repository], Optional[str]]:
        """List repositories for a Bitbucket workspace"""
        # TODO: Implement Bitbucket API integration
        return [], "Bitbucket integration not yet implemented"
    
    async def get_repo_info(self, owner: str, repo: str) -> Tuple[Optional[Repository], Optional[str]]:
        """Get information about a specific Bitbucket repository"""
        # TODO: Implement Bitbucket API integration
        return None, "Bitbucket integration not yet implemented"
    
    def parse_repo_url(self, repo_url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse Bitbucket repository URL to extract owner and repo name"""
        # TODO: Implement Bitbucket URL parsing
        return None, None

class SCMService:
    """Universal SCM service that supports multiple providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scm_config = config.get('graphshift', {}).get('scm', {})
        self.providers = {}
        

        # Initialize available providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize SCM providers based on configuration"""
        # GitHub provider
        if 'github' in self.scm_config:
            try:
                self.providers['github'] = GitHubProvider(self.scm_config['github'])
                logger.info("GitHub provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub provider: {e}")
        
        # GitLab provider
        if 'gitlab' in self.scm_config:
            try:
                self.providers['gitlab'] = GitLabProvider(self.scm_config['gitlab'])
                logger.info("GitLab provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GitLab provider: {e}")
        
        # Bitbucket provider
        if 'bitbucket' in self.scm_config:
            try:
                self.providers['bitbucket'] = BitbucketProvider(self.scm_config['bitbucket'])
                logger.info("Bitbucket provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Bitbucket provider: {e}")
        
        if not self.providers:
            logger.warning("No SCM providers configured. Only local analysis will be available.")
    
    def detect_provider(self, repo_url: str) -> Optional[str]:
        """Detect SCM provider from repository URL"""
        if 'github.com' in repo_url or 'github' in repo_url:
            return 'github'
        elif 'gitlab.com' in repo_url or 'gitlab' in repo_url:
            return 'gitlab'
        elif 'bitbucket.org' in repo_url or 'bitbucket' in repo_url:
            return 'bitbucket'
        return None
    
    async def list_org_repos(self, org_name: str, provider: str = 'github', max_repos: int = 100) -> Tuple[List[Repository], Optional[str]]:
        """List repositories for an organization using specified provider"""
        if provider not in self.providers:
            return [], f"Provider '{provider}' not configured or not supported"
        
        async with self.providers[provider] as scm_provider:
            return await scm_provider.list_org_repos(org_name, max_repos)
    
    async def get_repo_info(self, repo_url: str) -> Tuple[Optional[Repository], Optional[str]]:
        """Get repository information from URL"""
        provider = self.detect_provider(repo_url)
        if not provider or provider not in self.providers:
            return None, f"Unsupported or unconfigured provider for URL: {repo_url}"
        
        scm_provider = self.providers[provider]
        owner, repo = scm_provider.parse_repo_url(repo_url)
        
        if not owner or not repo:
            return None, f"Could not parse repository URL: {repo_url}"
        
        async with scm_provider:
            return await scm_provider.get_repo_info(owner, repo)
    
    def filter_java_repos(self, repos: List[Repository]) -> List[Repository]:
        """Filter repositories to only include Java projects"""
        if not repos:
            return []
        
        # Use the first provider's filter method (they're all the same)
        provider = list(self.providers.values())[0]
        return provider.filter_java_repos(repos)

def create_scm_service(config: Dict[str, Any]) -> SCMService:
    """Factory function to create SCM service"""
    return SCMService(config) 