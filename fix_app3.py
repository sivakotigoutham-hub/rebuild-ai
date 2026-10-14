with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Find the enquiry button section (lines 644-651 in 1-indexed, which is 643-650 in 0-indexed)
# and move them to indent 28 (inside with col2:)
# Current lines 644-651 (0-indexed: 643-650):
# 644: # Enquiry button
# 645: recipient_name = get_user_name()
# 646: if st.button(
# 647:     f"Send Enquiry ->
# 648:     key=f"enquire_{listing['id']}_{abs(hash((listing['id'], request.get('material_type', ''))))}",
# 649:     use_container_width=True,
# 650: )

# We need to change the indent of these lines from 32 to 28
for i in range(643, 651):  # 0-indexed, lines 644-651
    if i < len(lines):
        line = lines[i]
        # Check if this line has indent 32 and is part of the enquiry section
        stripped = line.lstrip(' ')
        if stripped and len(line) - len(stripped) == 32:
            # Check if it's the enquiry button section
            if any(keyword in stripped for keyword in ['# Enquiry', 'recipient_name', 'if st.button', 'f"Send']):
                # Change indent from 32 to 28
                new_indent = ' ' * 28
                lines[i] = new_indent + stripped
                print(f'Fixed line {i+1}: changed indent from 32 to 28')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('Applied indent fix for enquiry section')