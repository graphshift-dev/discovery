"""
Simple GraphShift initialization.
Just handles user setup - no complex abstractions.
"""

import shutil
import yaml
from pathlib import Path


def get_user_config_file():
    """Get path to user's GraphShift config file"""
    return Path.home() / ".graphshift" / "config.yaml"


def is_initialized():
    """Check if user has initialized GraphShift"""
    return get_user_config_file().exists()


def copy_templates_to_user_dir(base_dir):
    """Copy templates and resources from package to user's base directory"""
    templates_dir = Path(base_dir) / "templates"
    resources_dir = Path(base_dir) / "resources"
    templates_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy HTML templates
    template_files = ['single_repo_report.html', 'organization_report.html']
    for template_file in template_files:
        try:
            # Try package installation first
            try:
                import importlib.resources as pkg_resources
                with pkg_resources.path('templates', template_file) as p:
                    package_template = str(p)
            except (ImportError, ModuleNotFoundError):
                try:
                    # Fallback to old pkg_resources
                    import pkg_resources
                    package_template = pkg_resources.resource_filename(
                        'templates', template_file
                    )
                except ImportError:
                    # Fallback for development environment
                    package_template = Path(__file__).parent.parent / 'templates' / template_file
            
            if Path(package_template).exists():
                user_template_path = templates_dir / template_file
                shutil.copy2(package_template, user_template_path)
                print(f"Copied template: {template_file}")
                
        except Exception as e:
            print(f"Could not copy template {template_file}: {e}")
    
    # Copy logo
    try:
        # Try package installation first
        try:
            import importlib.resources as pkg_resources
            with pkg_resources.path('resources', 'graphshift-logo.png') as p:
                package_logo = str(p)
        except (ImportError, ModuleNotFoundError):
            try:
                # Fallback to old pkg_resources
                import pkg_resources
                package_logo = pkg_resources.resource_filename(
                    'resources', 'graphshift-logo.png'
                )
            except ImportError:
                # Fallback for development environment
                package_logo = Path(__file__).parent.parent / 'resources' / 'graphshift-logo.png'
        
        if Path(package_logo).exists():
            user_logo_path = resources_dir / 'graphshift-logo.png'
            shutil.copy2(package_logo, user_logo_path)
            print(f"Copied logo: graphshift-logo.png")
        else:
            raise FileNotFoundError(f"Logo not found at: {package_logo}. Initialization failed.")
            
    except Exception as e:
        raise RuntimeError(f"Could not copy logo: {e}")
    
    # Copy config file (user-editable)
    try:
        config_dir = Path(base_dir) / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Try package installation first
        try:
            import importlib.resources as pkg_resources
            with pkg_resources.path('config', 'config.yaml') as p:
                package_config = str(p)
        except (ImportError, ModuleNotFoundError):
            try:
                # Fallback to old pkg_resources
                import pkg_resources
                package_config = pkg_resources.resource_filename(
                    'config', 'config.yaml'
                )
            except ImportError:
                # Fallback for development environment
                package_config = Path(__file__).parent.parent / 'config' / 'config.yaml'
        
        if Path(package_config).exists():
            user_config_path = config_dir / 'config.yaml'
            shutil.copy2(package_config, user_config_path)
            print(f"Copied config: config.yaml")
            print(f"Edit your configuration at: {user_config_path}")
        else:
            raise FileNotFoundError(f"Config not found at: {package_config}")
            
    except Exception as e:
        print(f"Warning: Could not copy config file: {e}")
    
    # Copy README (optional - not critical if it fails)
    try:
        # Try package installation first
        try:
            import importlib.resources as pkg_resources
            # README should be at the package root
            with pkg_resources.files().joinpath('README.md').open('r', encoding='utf-8') as readme_src:
                readme_content = readme_src.read()
        except (ImportError, ModuleNotFoundError, FileNotFoundError):
            try:
                # Fallback to old pkg_resources
                import pkg_resources
                readme_content = pkg_resources.resource_string('', 'README.md').decode('utf-8')
            except Exception:
                # Fallback for development environment
                readme_path = Path(__file__).parent.parent / 'README.md'
                if readme_path.exists():
                    readme_content = readme_path.read_text(encoding='utf-8')
                else:
                    readme_content = None
        
        if readme_content:
            user_readme_path = Path(base_dir) / 'README.md'
            user_readme_path.write_text(readme_content, encoding='utf-8')
            print(f"Copied README.md")
        
    except Exception:
        # README copy is not critical, continue without it
        pass


def save_user_config(base_directory):
    """Save user configuration"""
    user_config_file = get_user_config_file()
    user_config_file.parent.mkdir(parents=True, exist_ok=True)
    
    config = {
        'base_directory': str(Path(base_directory).resolve())
    }
    
    with open(user_config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False)


def initialize_graphshift(base_directory=None):
    """Initialize GraphShift with user's base directory"""
    print("GraphShift needs a working directory.")
    
    # Get base directory from user
    if not base_directory:
        # Use platform-appropriate default directory
        try:
            import appdirs
            default_base = appdirs.user_data_dir("GraphShift", "GraphShift")
        except ImportError:
            # Fallback for development environment
            import os
            if os.name == 'nt':  # Windows
                default_base = Path.home() / "AppData" / "Local" / "GraphShift"
            else:  # Unix-like
                default_base = Path.home() / ".local" / "share" / "GraphShift"
        
        user_input = input(f"Working directory [{default_base}]: ").strip()
        base_directory = user_input if user_input else default_base
    
    base_path = Path(base_directory).resolve()
    print(f"Setting up GraphShift at: {base_path}")
    
    # Create basic directory structure
    (base_path / "reports").mkdir(parents=True, exist_ok=True)
    (base_path / "logs").mkdir(parents=True, exist_ok=True)
    (base_path / "temp").mkdir(parents=True, exist_ok=True)
    (base_path / "clones").mkdir(parents=True, exist_ok=True)
    
    # Copy templates
    copy_templates_to_user_dir(base_path)
    
    # Save config
    save_user_config(base_path)
    
    print(f"\n✅ GraphShift initialized!")
    print(f"📊 Reports will be saved to: {base_path / 'reports'}")
    
    return True


def ensure_initialized():
    """Ensure GraphShift is initialized before running analysis"""
    if is_initialized():
        return True
    
    print("GraphShift needs to be initialized first.")
    return initialize_graphshift()