import re
def detect_volcano_name(text):
    text_low = text.lower()

    # Detect volcano name in the text
    match = re.search(r"(gunung|gn|g|mount|mt)\s+([a-zA-Z\-]+)", text_low)

    if match:
        volcano_name = match.group(2)  # extract only the name, e.g., "sinabung"
    else:
        return None  # no volcano found

    # Generate the code from the volcano name
    n = volcano_name.strip().upper()
    n = re.sub(r"[^A-Z]", "", n)

    return n[:3]