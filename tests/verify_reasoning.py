import sys
import os
from pathlib import Path

# Add src to path robustly
SRC_PATH = str(Path(__file__).parent.parent / "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from hcode.agent.reasoning import ReasoningParser
from hcode.config.reasoning_prompts import ReasoningPromptBuilder

def main():
    print("Verifying Reasoning Prompts...")
    
    parser = ReasoningParser()
    builder = ReasoningPromptBuilder()
    
    # 1. Test Standard Template
    print("\n[Test 1] Standard Template Parsing")
    standard_prompt = builder._standard_thinking_template()
    # Simulate a filled-out response
    mock_response = standard_prompt.replace("<what is the situation/request>", "User wants to fix a bug") \
                                   .replace("<what is implied but not stated>", "Needs to be done quickly") \
                                   .replace("<step 1>", "Check logs") \
                                   .replace("<step 2>", "Apply fix") \
                                   .replace("<option A>", "Fix A") \
                                   .replace("<option B>", "Fix B") \
                                   .replace("<potential issues>", "None") \
                                   .replace("<what to do>", "Apply Fix A") \
                                   .replace("<why>", "It is safer") \
                                   .replace("<specific tool call or action>", "edit_tool")

    parsed = parser.parse(mock_response)
    
    if parsed.perception.observation == "User wants to fix a bug":
        print("[OK] Standard Perception Parsed")
    else:
        print(f"[FAIL] Standard Perception Mismatch: {parsed.perception.observation}")

    if "Check logs" in parsed.analysis.decomposition:
        print("[OK] Standard Analysis Parsed")
    else: # Fallback check for newlines logic
         print(f"[WARN] Analysis decomposition: {parsed.analysis.decomposition}")

    if parsed.decision.decision == "Apply Fix A":
        print("[OK] Standard Decision Parsed")
    else:
        print(f"[FAIL] Standard Decision Mismatch: {parsed.decision.decision}")


    # 2. Test Deep Template
    print("\n[Test 2] Deep Template Parsing")
    deep_prompt = builder._deep_thinking_template()
    # Minimal fill for deep
    mock_deep = deep_prompt.replace("<detailed observation>", "Complex crash in system") \
                           .replace("<important components/files>", "Core agent") \
                           .replace("<what is the root problem>", "Memory leak") \
                           .replace("<what are we assuming>", "Linux env") \
                           .replace("<what are the limits>", "Low RAM") \
                           .replace("<breakdown of steps>", "1. Trace\n2. Patch") \
                           .replace("<what depends on what>", "A depends on B") \
                           .replace("<alternatives considered>", "Restart") \
                           .replace("<proposed solution>", "Fix leak") \
                           .replace("<why it will work>", "Proven fix") \
                           .replace("<why it might fail>", "Race condition") \
                           .replace("<list of files>", "main.py") \
                           .replace("<any API breaks>", "None") \
                           .replace("<potential unintended consequences>", "None") \
                           .replace("<final choice>", "Fix leak") \
                           .replace("<reasoning>", "Best long term") \
                           .replace("<plan B>", "Rollback") \
                           .replace("<summary of changes>", "Patch memory") \
                           .replace("<immediate risks>", "Downtime") \
                           .replace("<pre-flight checks>", "Check syntax") \
                           .replace("<how to verify success>", "Run valgrind")

    parsed_deep = parser.parse(mock_deep)
    
    # Check a few key phases
    if parsed_deep.perception.observation == "Complex crash in system":
        print("[OK] Deep Perception Parsed")
    else:
        print(f"[FAIL] Deep Perception: {parsed_deep.perception.observation}")

    if parsed_deep.comprehension.core_understanding == "Memory leak":
        print("[OK] Deep Comprehension Parsed")
    else:
        print(f"[FAIL] Deep Comprehension: {parsed_deep.comprehension.core_understanding}")

    if parsed_deep.verification.validation_steps: 
        print(f"[OK] Deep Verification Parsed: {parsed_deep.verification.validation_steps}")
    else:
        print(f"[FAIL] Deep Verification Empty: {parsed_deep.verification}")
        
    # 3. Test Quick Template (NEW)
    print("\n[Test 3] Quick Template Parsing")
    quick_prompt = builder._quick_thinking_template()
    mock_quick = quick_prompt.replace("<brief situation>", "User wants simple check") \
                             .replace("<main points>", "Easy task") \
                             .replace("<low/medium/high>", "low") \
                             .replace("<immediate next step>", "Run check") \
                             .replace("0.0-1.0", "0.9")

    parsed_quick = parser.parse(mock_quick)
    
    if parsed_quick.perception.observation == "User wants simple check":
        print("[OK] Quick Perception Parsed")
    else:
        print(f"[FAIL] Quick Perception: {parsed_quick.perception.observation}")
        
    if "Run check" in parsed_quick.decision.action_items or "Run check" in parsed_quick.decision.decision:
        print("[OK] Quick Decision Parsed") # 'Action:' maps to decision phase usually
    else:
         print(f"[FAIL] Quick decision not found from 'Action:' field")

    print("\nVerification Complete.")

if __name__ == "__main__":
    main()
