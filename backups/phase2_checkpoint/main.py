from engine.clarification_runner import run


def main():
    print("Slate808 v1 - Stepwise Engine")
    print("Type 'exit' to quit\n")

    while True:
        user_input = input("Enter request: ").strip()

        if user_input.lower() == "exit":
            print("Goodbye.")
            break

        result = run(user_input)

        print("\n==============================")
        print(result)
        print("==============================\n")


if __name__ == "__main__":
    main()