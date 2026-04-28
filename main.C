#include <stdio.h>
#include <stdlib.h>
#include <float.h>
#include <time.h>

void task_1(double a, double b) {
    // 'volatile' prevents the compiler from optimizing out the unused result
    for (int i = 0; i < 1000; i++) { volatile double res = a * b; }
}

int main(int argc, char **argv) {
    srand(time(NULL));
    struct timespec start, end;
    long long wcet = 0;
    double a = (double)rand() / RAND_MAX * 1e6;  // ← double, pas long long
    double b = (double)rand() / RAND_MAX * 1e6;
    
    for (int i = 0; i < 1000; i++) {
        clock_gettime(CLOCK_MONOTONIC, &start);
        task_1(a, b);
        clock_gettime(CLOCK_MONOTONIC, &end);
        
        long long diff = (end.tv_sec - start.tv_sec) * 1e9 + (end.tv_nsec - start.tv_nsec);
        if (diff > wcet) wcet = diff; // Retain the Worst-Case Execution Time
    }
    printf("WCET of the multiplication: %lld ns\n", wcet);
    return 0;
}