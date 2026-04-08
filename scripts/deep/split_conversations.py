import json
import os

INPUT_FILE = "/home/vishal/garuda/scripts/deep/conversations.json"   # update if needed
OUTPUT_DIR = "/home/vishal/garuda/scripts/deep/excerpts"

MAX_MESSAGES_PER_FILE = 20  # keep small chunks


def extract_clean_messages(mapping):
    cleaned = []

    for node_id, node in mapping.items():
        msg = node.get("message")
        if not msg:
            continue

        fragments = msg.get("fragments", [])

        for frag in fragments:
            ftype = frag.get("type")
            content = frag.get("content")

            # Keep ONLY useful parts
            if ftype in ["REQUEST", "RESPONSE"]:
                if content and len(content.strip()) > 5:
                    cleaned.append({
                        "type": ftype,
                        "content": content.strip()
                    })

            # Skip SEARCH (too heavy)
            # Skip long logs automatically
    return cleaned


def split_into_chunks(messages, chunk_size):
    for i in range(0, len(messages), chunk_size):
        yield messages[i:i + chunk_size]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    file_count = 0

    for conv_index, conv in enumerate(data):
        title = conv.get("title", f"conversation_{conv_index}")
        mapping = conv.get("mapping", {})

        messages = extract_clean_messages(mapping)

        if not messages:
            continue

        chunks = list(split_into_chunks(messages, MAX_MESSAGES_PER_FILE))

        for i, chunk in enumerate(chunks):
            output_file = os.path.join(
                OUTPUT_DIR,
                f"{title.replace(' ', '_')}_{conv_index}_{i}.json"
            )

            with open(output_file, "w", encoding="utf-8") as out:
                json.dump({
                    "topic": title,
                    "chunk_id": i,
                    "messages": chunk
                }, out, indent=2)

            file_count += 1

    print(f"\n? Done. Created {file_count} smaller files in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()