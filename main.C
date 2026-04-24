#include <stdio.h>
#include <stdlib.h>
#include <float.h>
#include <time.h>

typedef struct {
    int id;
    float c;
    float r;
    float d;
} Job;

float global_min_waiting_time = FLT_MAX;

void explorer(int* courant_ordre, int nb_faits, float temps_actuel, float attente_cumulee, Job* jobs, int n, int* meilleur_ordre, int allow_tau5_miss) {
    if (attente_cumulee >= global_min_waiting_time) return;
    if (nb_faits == n) {
        global_min_waiting_time = attente_cumulee;
        for (int i = 0; i < n; i++) meilleur_ordre[i] = courant_ordre[i];
        return;
    }
    for (int i = 0; i < n; i++) {
        int deja_present = 0;
        for (int j = 0; j < nb_faits; j++) { if (courant_ordre[j] == i) { deja_present = 1; break; } }
        if (!deja_present) {
            float debut = (temps_actuel > jobs[i].r) ? temps_actuel : jobs[i].r;
            float fin = debut + jobs[i].c;
            float attente_job = debut - jobs[i].r;
            int respecte_deadline = (fin <= jobs[i].d);
            if (allow_tau5_miss && jobs[i].id == 5) respecte_deadline = 1;
            if (respecte_deadline) {
                courant_ordre[nb_faits] = i;
                explorer(courant_ordre, nb_faits + 1, fin, attente_cumulee + attente_job, jobs, n, meilleur_ordre, allow_tau5_miss);
            }
        }
    }
}

__declspec(dllexport) void resoudre_ordonnancement(Job* jobs, int n, int* meilleur_ordre, int allow_tau5_miss) {
    global_min_waiting_time = FLT_MAX;
    int* courant_ordre = (int*)malloc(n * sizeof(int));
    if (courant_ordre != NULL) {
        for(int i=0; i<n; i++) meilleur_ordre[i] = i;
        explorer(courant_ordre, 0, 0.0, 0.0, jobs, n, meilleur_ordre, allow_tau5_miss);
        free(courant_ordre);
    }
}

void task_1(double a, double b) {
    for (int i = 0; i < 100000; i++) { volatile double res = a * b; }
}

int main(int argc, char **argv) {
    srand(time(NULL));
    struct timespec start, end;
    long long wcet = 0;
    double a = (double)rand() / RAND_MAX * 1000000.0;
    double b = (double)rand() / RAND_MAX * 1000000.0;
    for (int i = 0; i < 1000; i++) {
        clock_gettime(CLOCK_MONOTONIC, &start);
        task_1(a, b);
        clock_gettime(CLOCK_MONOTONIC, &end);
        long long diff = (end.tv_sec - start.tv_sec) * 1e9 + (end.tv_nsec - start.tv_nsec);
        if (diff > wcet) wcet = diff;
    }
    printf("WCET of the multiplication: %lld ns\n", wcet);
    return 0;
}