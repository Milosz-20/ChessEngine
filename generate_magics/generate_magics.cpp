#include <iostream>
#include <vector>
#include <random>
#include <fstream>
#include <iomanip>
#include <cstdint>

// --- TYPES & CONSTANTS ---
typedef uint64_t U64;

const U64 FILE_A = 0x0101010101010101ULL;
const U64 FULL_BOARD = 0xFFFFFFFFFFFFFFFFULL;

// --- BITWISE HELPERS ---

// Count bits (Population Count)
int count_bits(U64 b) {
    int count = 0;
    while (b) {
        count++;
        b &= b - 1;
    }
    return count;
}

// Random Number Generator (Sparse optimization)
// Magic numbers usually have few bits set, so we AND random numbers together
U64 random_u64() {
    static std::mt19937_64 gen(123456); // Seed
    static std::uniform_int_distribution<U64> dist;
    return dist(gen);
}

U64 random_sparse_u64() {
    return random_u64() & random_u64() & random_u64();
}

// --- MASK GENERATORS ---

U64 get_rook_mask(int square) {
    U64 mask = 0;
    int rank = square / 8;
    int file = square % 8;

    for (int r = rank + 1; r < 7; r++) mask |= (1ULL << (r * 8 + file));
    for (int r = rank - 1; r > 0; r--) mask |= (1ULL << (r * 8 + file));
    for (int f = file + 1; f < 7; f++) mask |= (1ULL << (rank * 8 + f));
    for (int f = file - 1; f > 0; f--) mask |= (1ULL << (rank * 8 + f));

    return mask;
}

U64 get_bishop_mask(int square) {
    U64 mask = 0;
    int rank = square / 8;
    int file = square % 8;
    int r, f;

    for (r = rank + 1, f = file + 1; r < 7 && f < 7; r++, f++) mask |= (1ULL << (r * 8 + f));
    for (r = rank + 1, f = file - 1; r < 7 && f > 0; r++, f--) mask |= (1ULL << (r * 8 + f));
    for (r = rank - 1, f = file + 1; r > 0 && f < 7; r--, f++) mask |= (1ULL << (r * 8 + f));
    for (r = rank - 1, f = file - 1; r > 0 && f > 0; r--, f--) mask |= (1ULL << (r * 8 + f));

    return mask;
}

// --- ATTACK GENERATORS (ON THE FLY) ---

U64 rook_attacks_on_the_fly(int square, U64 blockers) {
    U64 attacks = 0;
    int rank = square / 8;
    int file = square % 8;
    int r, f;

    for (r = rank + 1; r < 8; r++) {
        attacks |= (1ULL << (r * 8 + file));
        if ((1ULL << (r * 8 + file)) & blockers) break;
    }
    for (r = rank - 1; r >= 0; r--) {
        attacks |= (1ULL << (r * 8 + file));
        if ((1ULL << (r * 8 + file)) & blockers) break;
    }
    for (f = file + 1; f < 8; f++) {
        attacks |= (1ULL << (rank * 8 + f));
        if ((1ULL << (rank * 8 + f)) & blockers) break;
    }
    for (f = file - 1; f >= 0; f--) {
        attacks |= (1ULL << (rank * 8 + f));
        if ((1ULL << (rank * 8 + f)) & blockers) break;
    }
    return attacks;
}

U64 bishop_attacks_on_the_fly(int square, U64 blockers) {
    U64 attacks = 0;
    int rank = square / 8;
    int file = square % 8;
    int r, f;

    for (r = rank + 1, f = file + 1; r < 8 && f < 8; r++, f++) {
        attacks |= (1ULL << (r * 8 + f));
        if ((1ULL << (r * 8 + f)) & blockers) break;
    }
    for (r = rank + 1, f = file - 1; r < 8 && f >= 0; r++, f--) {
        attacks |= (1ULL << (r * 8 + f));
        if ((1ULL << (r * 8 + f)) & blockers) break;
    }
    for (r = rank - 1, f = file + 1; r >= 0 && f < 8; r--, f++) {
        attacks |= (1ULL << (r * 8 + f));
        if ((1ULL << (r * 8 + f)) & blockers) break;
    }
    for (r = rank - 1, f = file - 1; r >= 0 && f >= 0; r--, f--) {
        attacks |= (1ULL << (r * 8 + f));
        if ((1ULL << (r * 8 + f)) & blockers) break;
    }
    return attacks;
}

// --- MAGIC FINDER LOGIC ---

// Helper to get all occupancy variations for a mask
std::vector<U64> generate_occupancies(U64 mask) {
    std::vector<U64> occupancies;
    U64 subset = 0;
    do {
        occupancies.push_back(subset);
        subset = (subset - mask) & mask;
    } while (subset != 0);
    return occupancies;
}

struct MagicResult {
    U64 mask;
    U64 magic;
    int shift;
};

MagicResult find_magic_number(int square, bool is_rook) {
    U64 mask = is_rook ? get_rook_mask(square) : get_bishop_mask(square);
    int n_bits = count_bits(mask);

    // Pre-calculate all variations and their correct attacks
    std::vector<U64> occupancies = generate_occupancies(mask);
    std::vector<U64> attacks;
    attacks.reserve(occupancies.size());

    for (U64 occ : occupancies) {
        if (is_rook) attacks.push_back(rook_attacks_on_the_fly(square, occ));
        else attacks.push_back(bishop_attacks_on_the_fly(square, occ));
    }

    int size = 1 << n_bits;
    int shift = 64 - n_bits;

    // Arrays for testing (dynamic allocation to prevent stack overflow on large tables)
    std::vector<U64> used_table(size);
    std::vector<int> used_flags(size); // Using int as a generation counter
    int generation = 0;

    while (true) {
        U64 magic_candidate = random_sparse_u64();

        // Skip obviously bad numbers (not enough entropy)
        if (count_bits((mask * magic_candidate) & 0xFF00000000000000ULL) < 6) continue;

        generation++;
        bool fail = false;

        for (size_t i = 0; i < occupancies.size(); i++) {
            int idx = (int)((occupancies[i] * magic_candidate) >> shift);

            if (used_flags[idx] != generation) {
                // Empty slot, fill it
                used_flags[idx] = generation;
                used_table[idx] = attacks[i];
            } else if (used_table[idx] != attacks[i]) {
                // Collision with different attack set = FAIL
                fail = true;
                break;
            }
        }

        if (!fail) {
            return { mask, magic_candidate, shift };
        }
    }
}

// --- MAIN ---

int main() {
    std::vector<MagicResult> rook_magics;
    std::vector<MagicResult> bishop_magics;

    std::cout << "--- C++ Magic Number Generator ---" << std::endl;
    std::cout << "Generating Rooks..." << std::endl;

    for (int sq = 0; sq < 64; sq++) {
        std::cout << "Square " << sq << "/63\r" << std::flush;
        rook_magics.push_back(find_magic_number(sq, true));
    }

    std::cout << "\nGenerating Bishops..." << std::endl;
    for (int sq = 0; sq < 64; sq++) {
        std::cout << "Square " << sq << "/63\r" << std::flush;
        bishop_magics.push_back(find_magic_number(sq, false));
    }

    // --- SAVE TO JSON ---
    std::cout << "\nSaving to magic_numbers.json..." << std::endl;
    std::ofstream out("magic_numbers.json");

    out << "{\n";

    // Write Rooks
    out << "  \"rook\": [\n";
    for (size_t i = 0; i < rook_magics.size(); i++) {
        out << "    {\"mask\": " << rook_magics[i].mask
            << ", \"magic\": " << rook_magics[i].magic
            << ", \"shift\": " << rook_magics[i].shift << "}";
        if (i < rook_magics.size() - 1) out << ",";
        out << "\n";
    }
    out << "  ],\n";

    // Write Bishops
    out << "  \"bishop\": [\n";
    for (size_t i = 0; i < bishop_magics.size(); i++) {
        out << "    {\"mask\": " << bishop_magics[i].mask
            << ", \"magic\": " << bishop_magics[i].magic
            << ", \"shift\": " << bishop_magics[i].shift << "}";
        if (i < bishop_magics.size() - 1) out << ",";
        out << "\n";
    }
    out << "  ]\n";
    out << "}\n";

    out.close();
    std::cout << "Done." << std::endl;

    return 0;
}