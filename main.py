from music_agent.cd_agent import cd_agent

def main():
    print("CD Agent CLI")
    print("Type 'exit' to quit.")
    print("-" * 40)

    while True:
        user_input = input("You: ")
        if user_input.lower() in ("exit", "quit"):
            break

        response = cd_agent.run(user_input)
        print("Agent:", response)


if __name__ == "__main__":
    main()
