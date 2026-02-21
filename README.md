# Chess Engine

A Python-based chess engine implementation using **Bitboards** for efficient board representation and move generation.

## Overview

- **Bitboard Representation**: The entire board state is stored using 64-bit integers, allowing for efficient parallel operations.
- **Magic Bitboards**: Sliding piece attacks (Rook and Bishop) are calculated using Magic Bitboards, a technique that allows for constant-time lookups.
- **Pre-computed Tables**: Movement patterns for non-sliding pieces (King, Knight) and other static data are pre-calculated to minimize runtime overhead.

## Getting Started

To run the engine and see a demonstration of move generation:

```bash
python main.py
```

The project includes a C++ component for generating magic numbers, which are used to optimize sliding piece attacks. These are pre-computed and stored in `magic_numbers.json`.
