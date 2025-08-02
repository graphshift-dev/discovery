"""
Health Service - Handles all health check functionality.
Clean separation: commands.py delegates health logic to this service.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class HealthService:
    """
    Single responsibility: Perform system health checks.
    Commands.py delegates all health logic to this service.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize health service with configuration"""
        self.config = config
    
    def perform_health_check(self, verbose: bool = False) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.
        
        Args:
            verbose: Include detailed information
            
        Returns:
            Health check results
        """
        logger.info("Starting system health check")
        
        health_results = {
            'overall_status': 'healthy',
            'checks': [],
            'warnings': [],
            'errors': []
        }
        
        # Check Java installation
        java_check = self._check_java_installation()
        health_results['checks'].append(java_check)
        if not java_check['passed']:
            health_results['errors'].append(java_check['message'])
            health_results['overall_status'] = 'unhealthy'
        
        # Check JAR analyzer
        jar_check = self._check_jar_analyzer()
        health_results['checks'].append(jar_check)
        if not jar_check['passed']:
            health_results['errors'].append(jar_check['message'])
            health_results['overall_status'] = 'unhealthy'
        
        # Check configuration
        config_check = self._check_configuration()
        health_results['checks'].append(config_check)
        if not config_check['passed']:
            health_results['warnings'].append(config_check['message'])
            if health_results['overall_status'] == 'healthy':
                health_results['overall_status'] = 'warning'
        
        # Check memory settings
        memory_check = self._check_memory_settings()
        health_results['checks'].append(memory_check)
        if not memory_check['passed']:
            health_results['warnings'].append(memory_check['message'])
            if health_results['overall_status'] == 'healthy':
                health_results['overall_status'] = 'warning'
        
        # Check network connectivity (if verbose)
        if verbose:
            network_check = self._check_network_connectivity()
            health_results['checks'].append(network_check)
            if not network_check['passed']:
                health_results['warnings'].append(network_check['message'])
                if health_results['overall_status'] == 'healthy':
                    health_results['overall_status'] = 'warning'
        
        logger.info(f"Health check completed: {health_results['overall_status']}")
        return health_results
    
    def _check_java_installation(self) -> Dict[str, Any]:
        """Check Java installation and version"""
        try:
            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Java version is typically in stderr
                version_output = result.stderr or result.stdout
                return {
                    'name': 'Java Installation',
                    'passed': True,
                    'message': f'Java is installed: {version_output.split()[0] if version_output else "Unknown version"}',
                    'details': version_output.strip()
                }
            else:
                return {
                    'name': 'Java Installation',
                    'passed': False,
                    'message': 'Java is not properly installed or not in PATH',
                    'details': result.stderr
                }
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {
                'name': 'Java Installation',
                'passed': False,
                'message': f'Java check failed: {str(e)}',
                'details': str(e)
            }
    
    def _check_jar_analyzer(self) -> Dict[str, Any]:
        """Check JAR analyzer availability"""
        try:
            jar_config = self.config.get("graphshift", {}).get("jar", {})
            jar_path = Path(jar_config.get("path", "gs-analyzer.jar"))
            
            if jar_path.exists():
                return {
                    'name': 'JAR Analyzer',
                    'passed': True,
                    'message': f'JAR analyzer found at: {jar_path}',
                    'details': f'File size: {jar_path.stat().st_size} bytes'
                }
            else:
                return {
                    'name': 'JAR Analyzer',
                    'passed': False,
                    'message': f'JAR analyzer not found at: {jar_path}',
                    'details': 'Please ensure gs-analyzer.jar is in the correct location'
                }
                
        except Exception as e:
            return {
                'name': 'JAR Analyzer',
                'passed': False,
                'message': f'JAR analyzer check failed: {str(e)}',
                'details': str(e)
            }
    
    def _check_configuration(self) -> Dict[str, Any]:
        """Check configuration validity"""
        try:
            graphshift_config = self.config.get('graphshift', {})
            
            if not graphshift_config:
                return {
                    'name': 'Configuration',
                    'passed': False,
                    'message': 'GraphShift configuration section missing',
                    'details': 'config.yaml should contain a "graphshift" section'
                }
            
            # Check required sections
            required_sections = ['analysis', 'jar']
            missing_sections = [section for section in required_sections if section not in graphshift_config]
            
            if missing_sections:
                return {
                    'name': 'Configuration',
                    'passed': False,
                    'message': f'Missing configuration sections: {", ".join(missing_sections)}',
                    'details': 'Please check your config.yaml file'
                }
            
            return {
                'name': 'Configuration',
                'passed': True,
                'message': 'Configuration loaded successfully',
                'details': f'Sections found: {list(graphshift_config.keys())}'
            }
                
        except Exception as e:
            return {
                'name': 'Configuration',
                'passed': False,
                'message': f'Configuration check failed: {str(e)}',
                'details': str(e)
            }
    
    def _check_memory_settings(self) -> Dict[str, Any]:
        """Check memory settings"""
        try:
            jar_config = self.config.get("graphshift", {}).get("jar", {})
            memory = jar_config.get("memory", "2g")
            initial_memory = jar_config.get("initial_memory", "512m")
            
            return {
                'name': 'Memory Settings',
                'passed': True,
                'message': f'Memory configured: {memory} heap, {initial_memory} initial',
                'details': f'Heap: {memory}, Initial: {initial_memory}'
            }
            
        except Exception as e:
            return {
                'name': 'Memory Settings',
                'passed': False,
                'message': f'Memory settings check failed: {str(e)}',
                'details': str(e)
            }
    
    def _check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity for remote analysis"""
        try:
            import urllib.request
            import socket
            
            # Test GitHub connectivity
            socket.setdefaulttimeout(5)
            urllib.request.urlopen('https://api.github.com', timeout=5)
            
            return {
                'name': 'Network Connectivity',
                'passed': True,
                'message': 'Network connectivity is available',
                'details': 'GitHub API is accessible'
            }
            
        except Exception as e:
            return {
                'name': 'Network Connectivity',
                'passed': False,
                'message': f'Network connectivity issue: {str(e)}',
                'details': 'Remote analysis may not work properly'
            }
    
    def format_health_results(self, health_results: Dict[str, Any], verbose: bool = False) -> str:
        """Format health results for display"""
        lines = []
        
        # Overall status
        status = health_results['overall_status'].upper()
        lines.append(f"System Health: {status}")
        lines.append("=" * 40)
        
        # Individual checks
        for check in health_results['checks']:
            status_icon = "✓" if check['passed'] else "✗"
            lines.append(f"{status_icon} {check['name']}: {check['message']}")
            
            if verbose and 'details' in check:
                lines.append(f"  Details: {check['details']}")
        
        # Summary
        if health_results['errors']:
            lines.append("\nErrors:")
            for error in health_results['errors']:
                lines.append(f"  • {error}")
        
        if health_results['warnings']:
            lines.append("\nWarnings:")
            for warning in health_results['warnings']:
                lines.append(f"  • {warning}")
        
        return "\n".join(lines)