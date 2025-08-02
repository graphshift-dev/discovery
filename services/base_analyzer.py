"""
Pure Base Analyzer - handles only JAR analysis operations.
Clean separation following the ideal architecture diagram.
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseAnalyzer:
    """
    Pure base analyzer focused solely on JAR analysis.
    
    Follows the ideal architecture - no cloning, no path decisions,
    just pure analysis of local directories.
    """
    
    def __init__(self, config: Dict[str, Any], memory_overrides: Optional[Dict[str, str]] = None):
        """Initialize base analyzer with JAR configuration"""
        self.config = config
        self.memory_overrides = memory_overrides or {}
        
        # JAR configuration
        jar_config = config.get("graphshift", {}).get("jar", {})
        self.jar_path = Path(jar_config.get("path", "gs-analyzer.jar"))
        
        # Defensive programming - ensure defaults are strings
        default_memory = jar_config.get("memory", "2g")
        default_initial_memory = jar_config.get("initial_memory", "512m")
        
        # Safety check - if config contains dicts, use hardcoded defaults
        self.default_memory = default_memory if isinstance(default_memory, str) else "2g"
        self.default_initial_memory = default_initial_memory if isinstance(default_initial_memory, str) else "512m"
        
        logger.debug(f"Initialized with memory: {self.default_memory}, initial: {self.default_initial_memory}")
    
    async def analyze_directory(
        self,
        directory_path: str,
        target_jdk: str = "21",
        scope: str = "all-deprecations"
    ) -> Optional[Dict[str, Any]]:
        """
        Pure directory analysis using JAR.
        
        Args:
            directory_path: Local directory to analyze
            target_jdk: Target JDK version
            scope: Analysis scope
            
        Returns:
            Raw JSON from JAR or None if failed
        """
        try:
            # Validate directory exists
            dir_path = Path(directory_path)
            if not dir_path.exists() or not dir_path.is_dir():
                logger.error(f"Directory does not exist: {directory_path}")
                return None
            
            # Get memory settings - handle both parameter name formats
            memory = (self.memory_overrides.get("memory") or 
                     self.memory_overrides.get("heap_size") or 
                     self.default_memory)
            initial_memory = (self.memory_overrides.get("initial_memory") or 
                             self.memory_overrides.get("initial_heap") or 
                             self.default_initial_memory)
            
            logger.debug(f"Using memory: {memory}, initial: {initial_memory}")
            
            # Build JAR command
            output_file = f"temp_analysis_{target_jdk}_{scope}.json"
            cmd = [
                'java',
                f'-Xmx{memory}',
                f'-Xms{initial_memory}',
                '-Xss4m',
                '-jar', str(self.jar_path),
                '-d', str(dir_path),
                '-t', target_jdk,
                '--scope', scope,
                '-o', output_file
            ]
            
            logger.debug(f"Running JAR analysis: {' '.join(cmd)}")
            
            # Execute JAR
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Read the output file
                output_path = Path('oss/outputs') / output_file
                if output_path.exists():
                    with open(output_path, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                    output_path.unlink()  # Clean up temp file
                    
                    logger.debug(f"JAR analysis completed for {directory_path}")
                    return result
                else:
                    logger.error("JAR completed but output file not found")
                    return None
            else:
                logger.error(f"JAR analysis failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"JAR execution failed: {e}")
            return None
    
    def get_memory_info(self) -> str:
        """Get memory configuration for display"""
        # Use same logic as JAR execution for consistency
        memory = (self.memory_overrides.get("memory") or 
                 self.memory_overrides.get("heap_size") or 
                 self.default_memory)
        initial_memory = (self.memory_overrides.get("initial_memory") or 
                         self.memory_overrides.get("initial_heap") or 
                         self.default_initial_memory)
        
        return f"{memory} memory, {initial_memory} initial"