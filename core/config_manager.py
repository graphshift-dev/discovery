import logging
import logging.config
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Optional yaml import
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger("core.config_manager")

class ConfigManager:
    """Enhanced configuration manager for OSS/PRO feature management"""
    
    # PRO-only features (disabled in OSS)
    PRO_FEATURES = {
        "enable_dependency_analysis",
        "enable_rag_corpus", 
        "enable_ai_fallback",
        "enable_graph_database",
        "enable_multi_tenant"
    }
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.config_path: Optional[str] = None
        self.logging_configured = False
    
    def load_config(self, config_path: str) -> Tuple[bool, Optional[str]]:
        """Load configuration from YAML file with environment overrides"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                return False, f"Config file not found: {config_path}"
            
            if not HAS_YAML:
                # Fallback to minimal default configuration if YAML is not available
                logger.warning("PyYAML not installed. Using minimal default configuration.")
                self.config = self._get_minimal_config()
            else:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
            
            self.config_path = config_path
            
            # Apply environment variable overrides
            self._apply_environment_overrides()
            
            # Setup logging first (before other log messages)
            self.setup_logging()
            

            
            # Validate PRO features are disabled in OSS
            self._validate_oss_config()
            
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to load config: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides for Docker deployment"""
        
        # GitHub token override
        github_token = os.getenv('GRAPHSHIFT_GITHUB_TOKEN')
        if github_token:
            if 'graphshift' not in self.config:
                self.config['graphshift'] = {}
            if 'scm' not in self.config['graphshift']:
                self.config['graphshift']['scm'] = {}
            self.config['graphshift']['scm']['token'] = github_token
        
        # Log level override
        log_level = os.getenv('GRAPHSHIFT_LOG_LEVEL')
        if log_level:
            if 'logging' not in self.config:
                self.config['logging'] = {}
            self.config['logging']['level'] = log_level.upper()
        
        # Data directory overrides (for Docker or custom deployment)
        data_dir = os.getenv('GRAPHSHIFT_DATA_DIR')
        if data_dir:
            paths = self.config.get('graphshift', {}).get('paths', {})
            paths['logs'] = f"{data_dir}/logs"
            paths['output_base'] = f"{data_dir}/output"
            paths['output_details'] = f"{data_dir}/output/details"
            paths['snapshots'] = f"{data_dir}/output/summaries"
            paths['temp_dir'] = f"{data_dir}/temp"
            paths['quarantine_dir'] = f"{data_dir}/quarantine"
            
            # Update logging path too
            if 'logging' not in self.config:
                self.config['logging'] = {}
            self.config['logging']['file'] = f"{data_dir}/logs/graphshift.log"
    
    def setup_logging(self) -> None:
        """Setup logging configuration from config file"""
        if self.logging_configured:
            return
            
        try:
            logging_config = self.config.get("logging", {})
            
            # Default logging configuration
            default_config = {
                "level": "INFO",
                "file": "./data/logs/graphshift.log", 
                "max_size_mb": 10,
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "loggers": {}
            }
            
            # Merge with user config
            final_config = {**default_config, **logging_config}
            
            # Ensure log directory exists
            log_file = Path(final_config["file"])
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Configure root logger
            root_level = getattr(logging, final_config["level"].upper(), logging.INFO)
            
            # Create formatters
            formatter = logging.Formatter(final_config["format"])
            
            # File handler with rotation
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=final_config["max_size_mb"] * 1024 * 1024,
                backupCount=final_config["backup_count"]
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(root_level)
            
            # Console handler (only for DEBUG level or if no file logging)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.ERROR)  # Only errors to console by default
            
            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(root_level)
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)
            
            # Configure service-specific loggers
            service_loggers = final_config.get("loggers", {})
            for logger_name, level_str in service_loggers.items():
                service_logger = logging.getLogger(logger_name)
                service_level = getattr(logging, level_str.upper(), logging.INFO)
                service_logger.setLevel(service_level)
            
            self.logging_configured = True
            
        except Exception as e:
            # Fallback to basic logging if configuration fails
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            logger.error(f"Failed to setup logging configuration: {e}")
            self.logging_configured = True
    
    def get_feature_flag(self, feature_name: str) -> bool:
        """Get feature flag value (fail-safe: False for missing flags)"""
        try:
            features = self.config.get("graphshift", {}).get("features", {})
            return features.get(feature_name, False)
        except Exception:
            return False
    
    def get_path(self, path_name: str) -> Optional[str]:
        """Get path configuration with directory creation"""
        try:
            paths = self.config.get("graphshift", {}).get("paths", {})
            path = paths.get(path_name)
            
            # Ensure directory exists for writable paths
            if path and path_name in ['logs', 'output_base', 'output_details', 'snapshots', 'temp_dir', 'quarantine_dir']:
                Path(path).mkdir(parents=True, exist_ok=True)
            
            return path
        except Exception:
            return None
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get service-specific configuration"""
        try:
            services = self.config.get("services", {})
            return services.get(service_name, {})
        except Exception:
            return {}
    
    def get_kb_config(self) -> Dict[str, Any]:
        """Get knowledge base configuration"""
        return self.config.get("graphshift", {}).get("knowledge_base", {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return self.config.get("graphshift", {}).get("performance", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get("logging", {})
    
    def is_pro_feature(self, feature_name: str) -> bool:
        """Check if a feature is PRO-only"""
        return feature_name in self.PRO_FEATURES
    
    def _validate_oss_config(self) -> None:
        """Validate that PRO features are disabled in OSS"""
        features = self.config.get("graphshift", {}).get("features", {})
        
        for pro_feature in self.PRO_FEATURES:
            if features.get(pro_feature, False):
                logger.warning(f"PRO feature '{pro_feature}' is enabled but this is OSS version - disabling")
                features[pro_feature] = False
    
    def _get_minimal_config(self) -> Dict[str, Any]:
        """Get minimal default configuration when YAML is not available"""
        return {
            "graphshift": {
                "version": "1.0.0",
                "analysis": {
                    "clone_from_git": True,
                    "local_repo": False,
                    "stream_from_web": False,
                    "clone_dir": "./graphshift-temp",
                    "cleanup_after_analysis": True,
                    "max_concurrent_repos": 5,
                    "max_concurrent_requests": 10,
                    "large_repo_threshold": 1000,
                },
                "jar": {
                    "memory": {
                        "heap_size": "2g",
                        "initial_heap": "512m"
                    },
                    "timeout_seconds": 600,
                    "chunking": {}
                },
                "paths": {
                                "output_base": "./outputs",
            "logs": "./data/logs"
                },
                "features": {},
                "messaging": {}
            },
            "logging": {
                "level": "INFO", 
                "file": "./data/logs/graphshift.log"
            }
        }
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get the full configuration"""
        return self.config.copy()

# Global instance
_config_manager = ConfigManager()

def get_config_manager() -> ConfigManager:
    """Get global config manager instance"""
    return _config_manager
