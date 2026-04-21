#include <stdio.h>
#include <stdlib.h>
#include <float.h>

/* --- STRUCTURE DES DONNÉES --- */
// Doit correspondre exactement à la structure définie dans le script Python
typedef struct {
    int id;    // Identifiant de la tâche (ex: 1 pour tau1)
    float c;   // Capacité (Temps d'exécution mesuré ou simulé)
    float r;   // Date de réveil (Release time / Activation)
    float d;   // Échéance (Deadline relative au début de la période)
} Job;

// Variable globale pour stocker le record du temps d'attente minimal
float global_min_waiting_time = FLT_MAX;

/**
 * Fonction récursive d'exploration (Backtracking)
 * Explore les permutations de jobs pour minimiser l'attente totale.
 */
void explorer(int* courant_ordre, int nb_faits, float temps_actuel, float attente_cumulee, Job* jobs, int n, int* meilleur_ordre, int allow_tau5_miss) {

    /* --- OPTIMISATION 1 : ÉLAGAGE (PRUNING) ---
       Si l'attente actuelle dépasse déjà notre meilleur score, on arrête d'explorer cette branche. */
    if (attente_cumulee >= global_min_waiting_time) {
        return;
    }

    /* --- CONDITION DE FIN ---
       Si tous les jobs ont été placés dans l'ordre d'exécution. */
    if (nb_faits == n) {
        global_min_waiting_time = attente_cumulee;
        for (int i = 0; i < n; i++) {
            meilleur_ordre[i] = courant_ordre[i];
        }
        return;
    }

    // Parcours des jobs disponibles
    for (int i = 0; i < n; i++) {

        // Vérifier si le job i est déjà dans la séquence actuelle
        int deja_present = 0;
        for (int j = 0; j < nb_faits; j++) {
            if (courant_ordre[j] == i) {
                deja_present = 1;
                break;
            }
        }

        if (!deja_present) {
            // Calcul du timing pour ce job
            float debut = (temps_actuel > jobs[i].r) ? temps_actuel : jobs[i].r;
            float fin = debut + jobs[i].c;
            float attente_job = debut - jobs[i].r;

            /* --- OPTIMISATION 2 : RESPECT DES DEADLINES ---
               On vérifie si le job finit avant sa deadline.
               Si allow_tau5_miss est activé, on autorise tau5 (id 5) à dépasser. */
            int respecte_deadline = (fin <= jobs[i].d);
            if (allow_tau5_miss && jobs[i].id == 5) {
                respecte_deadline = 1;
            }

            if (respecte_deadline) {
                // On avance dans la récursion
                courant_ordre[nb_faits] = i;
                explorer(courant_ordre, nb_faits + 1, fin, attente_cumulee + attente_job, jobs, n, meilleur_ordre, allow_tau5_miss);
            }
        }
    }
}

/**
 * POINT D'ENTRÉE PRINCIPAL POUR PYTHON
 * Cette fonction est celle appelée par ctypes.
 */
__declspec(dllexport) void resoudre_ordonnancement(Job* jobs, int n, int* meilleur_ordre, int allow_tau5_miss) {
    // Réinitialisation du record pour chaque nouvel appel de fenêtre
    global_min_waiting_time = FLT_MAX;

    // Allocation dynamique du tableau de travail
    int* courant_ordre = (int*)malloc(n * sizeof(int));

    if (courant_ordre != NULL) {
        // Initialisation de l'ordre par défaut (au cas où aucune solution parfaite n'est trouvée)
        for(int i=0; i<n; i++) meilleur_ordre[i] = i;

        // Lancement de la recherche d'optimisation
        explorer(courant_ordre, 0, 0.0, 0.0, jobs, n, meilleur_ordre, allow_tau5_miss);

        free(courant_ordre);
    }
}
