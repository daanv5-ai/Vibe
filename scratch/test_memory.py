from memory import init_db, save_memory, get_memories, get_memories_as_text

def test_memory():
    print("Initializing DB...")
    init_db()
    
    user_id = 12345
    print(f"Saving memory for user {user_id}...")
    save_memory(user_id, "preference", "coffee", "Black with no sugar")
    save_memory(user_id, "fact", "location", "Amsterdam")
    
    print("Retrieving memories...")
    memories = get_memories(user_id)
    for m in memories:
        print(f" - {m['category']}: {m['key']} = {m['value']}")
    
    print("\nFormatted memory block for prompt:")
    print(get_memories_as_text(user_id))

if __name__ == "__main__":
    test_memory()
