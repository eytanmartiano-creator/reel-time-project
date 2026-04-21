// ordonnanceur.h
#ifndef ORDONNANCEUR_H
#define ORDONNANCEUR_H

typedef struct {
    int id;    // ID de la tâche (1, 2, 3...)
    float c;   // Temps d'exécution (Ci)
    float r;   // Date d'arrivée (Release time)
    float d;   // Deadline (Di)
} Job;

// Déclaration de la fonction principale
// jobs: tableau d'entrée, n: nombre de jobs,
// resultat_ordre: tableau où on va écrire l'ordre optimal
void resoudre_ordonnancement(Job* jobs, int n, int* resultat_ordre, int allow_tau5_miss);

#endif
