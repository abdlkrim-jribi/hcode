
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path AT THE BEGINNING
src_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, src_path)

from hcode.tools.file_tools import EditTool, WriteTool

async def main():
    print("Verifying EditTool Fuzzy Matching...")
    
    # Setup test file
    test_file = Path("temp_fuzzy_test.py").absolute()
    
    # Create test content with specific indentation and spacing
    content = """def my_function():
    x  =  10
    return True
"""
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)
        
    try:
        tool = EditTool(root_dir=os.getcwd())
        
        # Test 1: Indentation Mismatch + Flexible Whitespace
        print("\n--- Testing Fuzzy Match (Indentation + Spacing) ---")
        # User provides different indentation AND single spaces
        # File has: "    x  =  10"
        old_target = "  x = 10" 
        new_target = "    x = 20"
        
        result = await tool.execute(
            file_path=str(test_file),
            old_string=old_target,
            new_string=new_target
        )
        
        print(f"Success: {result.success}")
        if result.success:
            print(f"Output: {result.output}")
            if "Used fuzzy matching" in result.output:
                print("✅ Correctly reported fuzzy matching usage")
            else:
                print("⚠️ Did not explicitly report fuzzy matching (check logic)")
                
            # Verify file content
            with open(test_file, "r") as f:
                new_content = f.read()
            if "x = 20" in new_content:
                print("✅ Content updated successfully")
            else:
                print("❌ Content update failed")
        else:
            print(f"❌ Failed: {result.error}")
            
    finally:
        # Cleanup
        if test_file.exists():
            os.remove(test_file)

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
