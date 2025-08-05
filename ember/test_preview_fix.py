import re

# Test the improved preview conversion function
def create_preview_walkthrough_improved(content: str) -> str:
    """Improved version to handle component link conversion issues"""
    
    # Multiple patterns to catch different variations
    patterns = [
        # Standard pattern: [[component:1:2:name|display]]
        (r'\[\[component:([^:\]]+):([^:\]]+):([^|\]]+)\|([^\]]+)\]\]', lambda m: f'[**{m.group(4)}**](#component-{m.group(1)}-{m.group(2)}-{m.group(3).lower()})'),
        
        # Pattern without component name: [[component:1:2:|display]]
        (r'\[\[component:([^:\]]+):([^:\]]+):\|([^\]]+)\]\]', lambda m: f'[**{m.group(3)}**](#component-{m.group(1)}-{m.group(2)})'),
        
        # Any remaining [[component:...]] patterns
        (r'\[\[component:([^\]]+)\]\]', lambda m: f'[**{m.group(1).split("|")[-1] if "|" in m.group(1) else m.group(1)}**](#component-link)'),
    ]
    
    result = content
    conversion_count = 0
    
    for pattern, replacement_func in patterns:
        matches = list(re.finditer(pattern, result))
        if matches:
            print(f"Found {len(matches)} matches for pattern: {pattern}")
            for match in matches[:3]:  # Show first 3 matches
                print(f"  Match: {match.group(0)}")
                print(f"  Groups: {match.groups()}")
        
        # Apply replacement
        new_result = re.sub(pattern, replacement_func, result)
        if new_result != result:
            conversion_count += len(matches)
            result = new_result
    
    print(f"Total conversions: {conversion_count}")
    return result

# Test with some sample content
test_content = """
This uses [[component:1:1:pandas_import|pandas library]] for data.
The [[component:3:1:VectorStore|VectorStore class]] handles storage.
Also [[component:2:2:clean_text|clean_text function]] processes text.
Some [[component:4:3:|configuration variable]] might have empty names.
"""

print("=== TESTING IMPROVED PREVIEW CONVERSION ===")
print("Original content:")
print(test_content)
print("\nConverted content:")
converted = create_preview_walkthrough_improved(test_content)
print(converted)