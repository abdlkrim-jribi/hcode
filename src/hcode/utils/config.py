"""Configuration management for Hcode.

Loads settings from .hcoderc files and environment variables.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
try:
    from dotenv import load_dotenv
    env_path = Path.cwd() / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        parent_env = Path.cwd().parent / '.env'
        if parent_env.exists():
            load_dotenv(parent_env)
except ImportError:
    pass
MODEL_SIZE_MAP = {'anthropic': {'small': 'claude-3-haiku-20240307', 'mid': 'claude-3-5-sonnet-20241022', 'big': 'claude-3-opus-20240229'}, 'openai': {'small': 'gpt-4o-mini', 'mid': 'gpt-4o', 'big': 'gpt-4-turbo'}}
OPENAI_COMPATIBLE_MODELS = {'cerebras': {'small': 'llama3.1-8b', 'mid': 'llama3.1-70b', 'big': 'llama3.1-70b'}, 'ollama': {'small': 'llama3:8b', 'mid': 'llama3:70b', 'big': 'llama3:70b'}, 'lmstudio': {'small': 'llama-3.1-8b', 'mid': 'llama-3.1-70b', 'big': 'llama-3.1-70b'}}
DEFAULT_CONFIG = {'providers': {'anthropic': {'api_key_env': 'ANTHROPIC_API_KEY', 'default_model': 'claude-3-5-sonnet-20241022', 'max_tokens': 4000, 'temperature': 0.3}, 'openai': {'api_key_env': 'OPENAI_API_KEY', 'base_url_env': 'OPENAI_BASE_URL', 'default_model': 'gpt-4o', 'max_tokens': 4000, 'temperature': 0.3}}, 'preferences': {'primary_provider': 'auto', 'fallback_enabled': True, 'cost_optimization': 'balanced', 'prefer_streaming': True, 'max_cost_per_request': 1.0}, 'tools': {'linter': 'auto', 'formatter': 'auto', 'test_runner': 'auto'}, 'safety': {'confirm_destructive': True, 'auto_backup': True, 'backup_retention_days': 7}}

def find_config_file() -> Optional[Path]:
    """find_config_file description.

Args:
    None

Returns:
    description

Raises:
    Exception description"""
    current = Path.cwd()
    for directory in [current] + list(current.parents):
        config_file = directory / '.hcoderc'
        if config_file.exists():
            return config_file
    home_config = Path.home() / '.hcode' / 'config.yaml'
    if home_config.exists():
        return home_config
    return None

def load_config(config_path: Optional[str]=None) -> Dict[str, Any]:
    """load_config description.

Args:
    config_path: description

Returns:
    description

Raises:
    Exception description"""
    config = DEFAULT_CONFIG.copy()
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = find_config_file()
    if config_file and config_file.exists():
        with open(config_file, 'r') as f:
            user_config = yaml.safe_load(f)
            if user_config:
                config = deep_merge(config, user_config)
    config = apply_env_overrides(config)
    return config

def deep_merge(base: Dict, override: Dict) -> Dict:
    """deep_merge description.

Args:
    base: description
    override: description

Returns:
    description

Raises:
    Exception description"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def get_model_for_size(provider: str, size: str, base_url: Optional[str]=None) -> str:
    """get_model_for_size description.

Args:
    provider: description
    size: description
    base_url: description

Returns:
    description

Raises:
    Exception description"""
    size = size.lower()
    if provider == 'openai' and base_url:
        base_url_lower = base_url.lower()
        for compat_provider, models in OPENAI_COMPATIBLE_MODELS.items():
            if compat_provider in base_url_lower:
                return models.get(size, models.get('mid'))
    if provider in MODEL_SIZE_MAP:
        return MODEL_SIZE_MAP[provider].get(size, MODEL_SIZE_MAP[provider].get('mid'))
    return MODEL_SIZE_MAP.get('openai', {}).get('mid', 'gpt-4o')

def apply_env_overrides(config: Dict) -> Dict:
    """apply_env_overrides description.

Args:
    config: description

Returns:
    description

Raises:
    Exception description"""
    for provider in ['anthropic', 'openai']:
        provider_config = config.get('providers', {}).get(provider, {})
        api_key_env = provider_config.get('api_key_env')
        if api_key_env:
            if api_key_env.startswith('sk-') or len(api_key_env) > 50:
                config['providers'][provider]['api_key'] = api_key_env
            else:
                actual_key = os.getenv(api_key_env)
                if actual_key:
                    config['providers'][provider]['api_key'] = actual_key
        base_url_env = provider_config.get('base_url_env')
        if base_url_env:
            if base_url_env.startswith('http'):
                config['providers'][provider]['base_url'] = base_url_env
            else:
                actual_url = os.getenv(base_url_env)
                if actual_url:
                    config['providers'][provider]['base_url'] = actual_url
    if os.getenv('ANTHROPIC_API_KEY'):
        config['providers']['anthropic']['api_key'] = os.getenv('ANTHROPIC_API_KEY')
    if os.getenv('OPENAI_API_KEY'):
        config['providers']['openai']['api_key'] = os.getenv('OPENAI_API_KEY')
    openai_base_url = os.getenv('OPENAI_BASE_URL')
    if openai_base_url:
        config['providers']['openai']['base_url'] = openai_base_url
    model_size = os.getenv('HCODE_MODEL_SIZE')
    if model_size:
        config['providers']['anthropic']['default_model'] = get_model_for_size('anthropic', model_size)
        config['providers']['openai']['default_model'] = get_model_for_size('openai', model_size, openai_base_url)
    if os.getenv('ANTHROPIC_MODEL'):
        config['providers']['anthropic']['default_model'] = os.getenv('ANTHROPIC_MODEL')
    if os.getenv('OPENAI_MODEL'):
        config['providers']['openai']['default_model'] = os.getenv('OPENAI_MODEL')
    if os.getenv('HCODE_MODEL'):
        model = os.getenv('HCODE_MODEL')
        config['providers']['anthropic']['default_model'] = model
        config['providers']['openai']['default_model'] = model
    if os.getenv('HCODE_PROVIDER'):
        config['preferences']['primary_provider'] = os.getenv('HCODE_PROVIDER')
    if os.getenv('HCODE_OPTIMIZE_COST'):
        config['preferences']['cost_optimization'] = os.getenv('HCODE_OPTIMIZE_COST')
    return config

def save_config(config: Dict[str, Any], config_path: Optional[str]=None):
    """save_config description.

Args:
    config: description
    config_path: description

Returns:
    description

Raises:
    Exception description"""
    if config_path:
        path = Path(config_path)
    else:
        path = Path.cwd() / '.hcoderc'
    with open(path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def create_default_config(path: Optional[str]=None):
    """create_default_config description.

Args:
    path: description

Returns:
    description

Raises:
    Exception description"""
    target_path = Path(path) if path else Path.cwd() / '.hcoderc'
    if target_path.exists():
        print(f'Config file already exists at {target_path}')
        return
    save_config(DEFAULT_CONFIG, str(target_path))
    print(f'Created default config at {target_path}')

def get_project_instructions() -> Optional[str]:
    """get_project_instructions description.

Args:
    None

Returns:
    description

Raises:
    Exception description"""
    instructions_file = Path.cwd() / '.hcode-instructions'
    if instructions_file.exists():
        with open(instructions_file, 'r') as f:
            return f.read()
    return None

def validate_config(config: Dict[str, Any]) -> tuple[bool, list[str]]:
    """validate_config description.

Args:
    config: description

Returns:
    description

Raises:
    Exception description"""
    errors = []
    required_sections = ['providers', 'preferences']
    for section in required_sections:
        if section not in config:
            errors.append(f'Missing required section: {section}')
    if 'providers' in config:
        for provider in ['anthropic', 'openai']:
            if provider in config['providers']:
                provider_config = config['providers'][provider]
                if 'api_key_env' not in provider_config and 'api_key' not in provider_config:
                    errors.append(f'{provider}: No API key or API key env var specified')
    if 'preferences' in config:
        prefs = config['preferences']
        if 'primary_provider' in prefs:
            valid_providers = ['auto', 'anthropic', 'openai']
            if prefs['primary_provider'] not in valid_providers:
                errors.append(f"Invalid primary_provider: {prefs['primary_provider']}")
        if 'cost_optimization' in prefs:
            valid_opts = ['aggressive', 'balanced', 'quality']
            if prefs['cost_optimization'] not in valid_opts:
                errors.append(f"Invalid cost_optimization: {prefs['cost_optimization']}")
    return (len(errors) == 0, errors)