#include <algorithm>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int T, N;
    long long L;
    if (!(std::cin >> T >> N >> L)) return 2;
    if (T < 0 || T > 25 || N <= 0 || L <= 0) return 3;

    std::vector<uint32_t> row_mask(N);
    std::vector<int> arity(N);
    std::vector<std::vector<int>> rows_by_type(T);
    std::vector<long long> linear_weight(T, 0);

    for (int r = 0; r < N; ++r) {
        uint32_t mask;
        int k;
        std::cin >> mask >> k;
        if (!std::cin || k <= 0) return 4;
        row_mask[r] = mask;
        arity[r] = k;
        if (__builtin_popcount(mask) != k) return 5;
        if (L % k != 0) return 6;
        long long unit = L / k;
        for (int t = 0; t < T; ++t) {
            if ((mask >> t) & 1U) {
                rows_by_type[t].push_back(r);
                linear_weight[t] += unit;
            }
        }
    }

    const uint64_t total_masks = 1ULL << T;
    const long long NEG = std::numeric_limits<long long>::min() / 4;
    std::vector<long long> best(T + 1, NEG);
    std::vector<uint32_t> best_mask(T + 1, 0);
    std::vector<uint8_t> selected_per_row(N, 0);

    uint32_t prev_gray = 0;
    int selected_types = 0;
    int fully_covered = 0;
    long long linear = 0;

    best[0] = 0;
    best_mask[0] = 0;

    for (uint64_t i = 1; i < total_masks; ++i) {
        uint32_t gray = static_cast<uint32_t>(i ^ (i >> 1));
        uint32_t diff = gray ^ prev_gray;
        int bit = __builtin_ctz(diff);
        bool turned_on = (gray & diff) != 0;

        if (turned_on) {
            ++selected_types;
            linear += linear_weight[bit];
            for (int r : rows_by_type[bit]) {
                uint8_t before = selected_per_row[r]++;
                if (before + 1 == arity[r]) ++fully_covered;
            }
        } else {
            --selected_types;
            linear -= linear_weight[bit];
            for (int r : rows_by_type[bit]) {
                uint8_t before = selected_per_row[r]--;
                if (before == arity[r]) --fully_covered;
            }
        }

        long long scaled = linear + L * static_cast<long long>(fully_covered);
        if (scaled > best[selected_types] ||
            (scaled == best[selected_types] && gray < best_mask[selected_types])) {
            best[selected_types] = scaled;
            best_mask[selected_types] = gray;
        }
        prev_gray = gray;
    }

    std::cout << "T " << T << "\n";
    std::cout << "N " << N << "\n";
    std::cout << "L " << L << "\n";
    for (int k = 0; k <= T; ++k) {
        std::cout << "BEST " << k << " " << best[k] << " " << best_mask[k] << "\n";
    }
    return 0;
}
