// Base template for C++ competitive programming
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <queue>
#include <map>
#include <set>
#include <numeric> // For std::iota
#include <limits>  // For std::numeric_limits

// Using common names for convenience
using namespace std;

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

// The main logic function to be filled by AI
void solve() {
    // Read input
    int n;
    std::cin >> n;

    // TODO: AI will implement the solution logic here
    
    // Print output
    std::cout << n << std::endl;
}

int main() {
    fast_io();
    
    // Uncomment for multiple test cases
    // int t;
    // std::cin >> t;
    // while (t--) {
    //     solve();
    // }

    solve();

    return 0;
}