import random

# List of words to choose from
words = ["python", "hangman", "programming", "developer", "computer", "keyboard", "monitor"]

def hangman():
    # Choose a random word
    word = random.choice(words)
    guessed_letters = set()
    attempts = 6
    word_letters = list(word)
    word_length = len(word_letters)
    guessed_word = ["_"] * word_length

    print("Welcome to Hangman!")
    print(f"You have {attempts} attempts to guess the word.")

    while attempts > 0 and "_" in guessed_word:
        print("\nCurrent word:", " ".join(guessed_word))
        guess = input("Guess a letter: ").lower()

        if len(guess) != 1 or not guess.isalpha():
            print("Please enter a single letter.")
            continue

        if guess in guessed_letters:
            print("You already guessed this letter.")
            continue

        guessed_letters.add(guess)

        if guess in word_letters:
            for i, letter in enumerate(word_letters):
                if letter == guess:
                    guessed_word[i] = guess
            print("Correct guess!")
        else:
            attempts -= 1
            print(f"Wrong guess! You have {attempts} attempts left.")

    if "_" not in guessed_word:
        print(f"\nCongratulations! You guessed the word: {word}")
    else:
        print(f"\nGame over! The word was: {word}")

# Start the game
hangman()