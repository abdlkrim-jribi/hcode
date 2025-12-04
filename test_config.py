"""
Simple validation test for configuration YAML files.
"""

import yaml
from pathlib import Path


def test_agents_yaml():
    """Test agents.yaml structure and values"""
    print("Testing agents.yaml...")
    
    filepath = Path("config/agents.yaml")
    if not filepath.exists():
        print(f"[FAIL] {filepath} not found")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Check temperature section
    assert 'temperature' in data, "Missing 'temperature' section"
    assert data['temperature']['default'] == 0.7
    assert data['temperature']['autonomous'] == 0.5
    assert data['temperature']['coding'] == 0.7
    assert data['temperature']['exploration'] == 1.0
    assert data['temperature']['focused'] == 0.5
    print("[PASS] Temperature values correct")
    
    # Check max_tokens section
    assert 'max_tokens' in data, "Missing 'max_tokens' section"
    assert data['max_tokens']['default'] == 4096
    assert data['max_tokens']['provider_max'] == 16384
    assert data['max_tokens']['thinking']['quick'] == 1000
    assert data['max_tokens']['thinking']['medium'] == 2500
    assert data['max_tokens']['thinking']['deep'] == 4000
    assert data['max_tokens']['thinking']['focused'] == 800
    assert data['max_tokens']['thinking']['comprehensive'] == 3000
    print("[PASS] Max tokens values correct")
    
    # Check max_iterations
    assert 'max_iterations' in data
    assert data['max_iterations'] == 50
    print("[PASS] Max iterations correct")
    
    print("[PASS] agents.yaml is valid\n")
    return True


def test_safety_yaml():
    """Test safety.yaml structure and values"""
    print("Testing safety.yaml...")
    
    filepath = Path("config/safety.yaml")
    if not filepath.exists():
        print(f"[FAIL] {filepath} not found")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Check dangerous_commands
    assert 'dangerous_commands' in data
    assert 'filesystem' in data['dangerous_commands']
    assert 'system' in data['dangerous_commands']
    assert 'remote_execution' in data['dangerous_commands']
    
    # Count total dangerous commands
    total = sum(len(cmds) for cmds in data['dangerous_commands'].values())
    print(f"[PASS] Found {total} dangerous commands")
    
    # Check confirmation_patterns
    assert 'confirmation_patterns' in data
    assert 'destructive' in data['confirmation_patterns']
    assert 'version_control' in data['confirmation_patterns']
    
    # Check specific values
    assert "rm -rf /" in data['dangerous_commands']['filesystem']
    assert "git push --force" in data['confirmation_patterns']['version_control']
    print("[PASS] Safety patterns correct")
    
    # Check sandbox setting
    assert 'enable_sandbox' in data
    assert data['enable_sandbox'] == True
    print("[PASS] Sandbox enabled")
    
    print("[PASS] safety.yaml is valid\n")
    return True


def test_file_operations_yaml():
    """Test file_operations.yaml structure and values"""
    print("Testing file_operations.yaml...")
    
    filepath = Path("config/file_operations.yaml")
    if not filepath.exists():
        print(f"[FAIL] {filepath} not found")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Check limits
    assert 'limits' in data
    assert data['limits']['max_file_size_bytes'] == 10485760  # 10MB
    assert data['limits']['max_lines_per_read'] == 2000
    assert data['limits']['max_files_per_operation'] == 100
    print("[PASS] File limits correct")
    
    # Check encoding
    assert 'encoding' in data
    assert data['encoding']['default'] == "utf-8"
    assert 'fallbacks' in data['encoding']
    assert len(data['encoding']['fallbacks']) >= 3
    print("[PASS] Encoding settings correct")
    
    # Check binary_extensions
    assert 'binary_extensions' in data
    assert 'executables' in data['binary_extensions']
    assert 'images' in data['binary_extensions']
    assert '.exe' in data['binary_extensions']['executables']
    assert '.jpg' in data['binary_extensions']['images']
    
    # Count total extensions
    total_exts = sum(len(exts) for exts in data['binary_extensions'].values())
    print(f"[PASS] Found {total_exts} binary extensions")
    
    # Check ignored_patterns
    assert 'ignored_patterns' in data
    assert 'version_control' in data['ignored_patterns']
    assert 'python_cache' in data['ignored_patterns']
    assert '.git' in data['ignored_patterns']['version_control']
    assert '__pycache__' in data['ignored_patterns']['python_cache']
    
    # Count total patterns
    total_patterns = sum(len(pats) for pats in data['ignored_patterns'].values())
    print(f"[PASS] Found {total_patterns} ignored patterns")
    
    print("[PASS] file_operations.yaml is valid\n")
    return True


def main():
    """Run all tests"""
    print("=" * 70)
    print("Configuration YAML Validation Test")
    print("=" * 70)
    print()
    
    tests = [
        test_agents_yaml,
        test_safety_yaml,
        test_file_operations_yaml,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except AssertionError as e:
            print(f"[FAIL] Assertion failed: {e}\n")
            results.append(False)
        except Exception as e:
            print(f"[FAIL] Test crashed: {e}\n")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] All configuration files are valid!")
        print("\nThe configuration system is working correctly:")
        print("  - agents.yaml: 5 temperature settings, 7 token limits")
        print("  - safety.yaml: 12 dangerous commands, multiple confirmation patterns")
        print("  - file_operations.yaml: File limits, encodings, binary extensions, ignored patterns")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
