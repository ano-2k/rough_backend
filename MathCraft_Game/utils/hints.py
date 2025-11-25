# utils/hint.py

import math

# Constants migrated from Games.jsx
NUMBER_HINT_POOL = {
    # A pool of three unique hints for each single-digit solution (0 through 9)
    0: [
        "The absolute value is the Additive Identity—it represents 'nothing'.",
        "It is the only integer that is neither positive nor negative.",
        "Multiplying any number by this value always results in itself.",
    ],
    1: [
        "The absolute value is the Multiplicative Identity—it leaves numbers unchanged when multiplied.",
        "It is the first counting number and the only number exactly equal to its reciprocal.",
        "It is the result of any non-zero number raised to the power of zero.",
    ],
    2: [
        "It is the smallest and the only even prime number.",
        "The number represents the base of the binary system.",
        "It is the first number in the Fibonacci sequence that's not 1 or 0.",
    ],
    3: [
        "It is the smallest odd prime number.",
        "Its square root, is an irrational number used in geometry.",
        "Any number whose digits sum up to a multiple of this number is divisible by it.",
    ],
    4: [
        "It is the smallest composite number.",
        "The number is both a perfect square.",
        "It is the number of sides on a standard square or legs on a house cat.",
    ],
    5: [
        "It is a prime number associated with the Pentagon and the Golden Ratio.",
        "This number is one of the only two prime numbers that ends in a '5'.",
        "It is the number of sides on a standard pentagon or points on a star.",
    ],
    6: [
        "It is the smallest positive Perfect Number (equal to the sum of its proper divisors).",
        "It is the only number that is both the sum and the product of the first three positive integers.",
        "This number is highly composite, being divisible by 1, 2, and 3.",
    ],
    7: [
        "It is considered a 'Magical' or 'Lucky' prime number in many cultures.",
        "The number represents the days of the week or the colors of the rainbow.",
        "Dividing 1 by this number yields a repeating decimal with a six-digit pattern.",
    ],
    8: [
        "It is the smallest Perfect Cube greater than 1 .",
        "The number represents the legs of a spider or the sides of an octagon.",
        "In the binary system, this value is represented as '1000'.",
    ],
    9: [
        "It is the largest single-digit composite number.",
        "The number is the square of the smallest odd prime.",
        "Any number divisible by this number will also have its digits sum up to a multiple of this number.",
    ],
}

def is_prime(x):
    """Helper function to check for primality."""
    if x <= 1: return False
    for i in range(2, int(math.sqrt(x)) + 1):
        if x % i == 0:
            return False
    return True

def generate_hint(solution_str: str, rotation_index: int) -> str:
    """
    Generates a hint for the given solution based on number properties.
    """
    try:
        n = int(solution_str)
    except ValueError:
        return "Input error: The system failed to interpret the solution."

    abs_n = abs(n)
    sign = "NEGATIVE" if n < 0 else "POSITIVE"
    clues = []

    # --- NEW: Priority Clues for single-digit solutions (0-9) ---
    if 0 <= abs_n <= 9:
        pool = NUMBER_HINT_POOL.get(abs_n)
        if pool:
            # Use modulo operator to cycle through the hints in the pool
            return pool[rotation_index % len(pool)]

    # --- 1. Strongest Clues: Powers and Roots (for abs_n > 9) ---
    root = round(math.sqrt(abs_n))
    if root * root == abs_n and abs_n > 1:
        clues.append(f"The absolute value is a Perfect Square (i.e., {root}²).")
    else:
        cube_root = round(abs_n**(1/3))
        if cube_root**3 == abs_n and abs_n > 1:
             clues.append(f"The absolute value is a Perfect Cube (i.e., {cube_root}³).")
        else:
            # Check for higher powers (e.g., power of 4 or 5)
            for p in range(4, 6):
                p_root = round(abs_n**(1/p))
                if round(p_root**p) == abs_n and abs_n > 1 and p_root > 1:
                    clues.append(f"The absolute value is a Perfect Power (specifically, {p_root} raised to the power of {p}).")
                    break

    # --- 2. Sequence Clues (e.g., Triangular) ---
    # Triangular numbers: Check if 8n + 1 is a perfect square.
    if abs_n > 0 and math.sqrt(8 * abs_n + 1).is_integer():
        clues.append("The absolute value is a Triangular Number (it's the sum of consecutive integers from 1 to some number).")

    # --- 3. Prime and Divisibility Clues ---
    if is_prime(abs_n):
      clues.append(f"This number is a {sign} Prime, only divisible by 1 and itself.")
    if not is_prime(abs_n) and abs_n > 1:
      if abs_n % 6 == 0:
        clues.append("The absolute value is a multiple of 6 (it's divisible by both 2 and 3).")
      elif abs_n % 5 == 0:
        clues.append("The number's last digit is 0 or 5. (i.e., it's a multiple of 5).")

    # --- 4. Digit/Magnitude Clues ---
    len_n = len(str(abs_n))
    if len_n > 0:
        clues.append(f"The absolute value is a {len_n}-digit number.")

    sum_digits = sum(int(d) for d in str(abs_n))
    if sum_digits % 9 == 0:
        clues.append("The sum of the digits of the absolute value is a multiple of 9.")
    elif sum_digits % 3 == 0:
        clues.append("The sum of the digits of the absolute value is a multiple of 3.")
    else:
        clues.append(f"The sum of the digits of the absolute value is {sum_digits}.")

    # --- 5. Generic Parity Clue (Last Resort) ---
    parity = "EVEN" if abs_n % 2 == 0 else "ODD"
    clues.append(f"The solution is a {sign} {parity} number.")

    if clues:
        # For multi-digit numbers, we return the strongest single clue (the first one)
        return clues[0]

    return "The sequence follows a linear or recursive pattern. Focus on the differences or ratios between terms."