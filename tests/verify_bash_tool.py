
import asyncio
import sys
import os
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add src to path AT THE BEGINNING
src_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, src_path)

import hcode.tools.bash_tools
from hcode.tools.bash_tools import BashTool

async def main():
    print(f"Loaded BashTool from: {hcode.tools.bash_tools.__file__}")
    print("Verifying BashTool Windows Capability...")
    
    # Mock confirmation display to avoid interactive prompt and encoding issues
    mock_confirmation = MagicMock()
    mock_confirmation.show_command_confirmation.return_value = True
    
    with patch('hcode.ui.confirmation_display.get_confirmation_display', return_value=mock_confirmation):
        tool = BashTool(root_dir=os.getcwd())
        
        # Test ls -> dir
        print("\n--- Testing 'ls' ---")
        # We use a simple command that produces output
        result = await tool.execute(command="ls")
        
        print(f"Success: {result.success}")
        if result.success:
            print("Output prefix:")
            print(result.output[:200])
            if "Volume in drive" in result.output or "Directory of" in result.output:
                 print("✅ Output looks like 'dir' output")
            else:
                 print("⚠️ Output doesn't clearly look like 'dir', check manually")
        else:
            print(f"Error: {result.error}")
            
        # Test cp (dummy) translation
        print("\n--- Testing 'cp' translation (dry run check) ---")
        translated = tool._translate_command("cp src/foo.py dest/bar.py")
        print(f"Original: cp src/foo.py dest/bar.py")
        print(f"Translated: {translated}")
        expected = "copy src\\foo.py dest\\bar.py"
        if translated == expected:
            print("✅ Translation verified")
        else:
            print(f"❌ Translation failed. Expected: {expected}")
            
        # Test rm -rf translation
        print("\n--- Testing 'rm -rf' translation ---")
        translated = tool._translate_command("rm -rf temp_dir")
        print(f"Original: rm -rf temp_dir")
        print(f"Translated: {translated}")
        expected = "rmdir /s /q temp_dir"
        if translated == expected:
            print("✅ Translation verified")
        else:
            print(f"❌ Translation failed. Expected: {expected}")

if __name__ == "__main__":
    # Force utf-8 for stdout if possible
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        
    asyncio.run(main())
