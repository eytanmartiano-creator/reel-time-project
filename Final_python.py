# -*- coding: utf-8 -*-
"""
Analyse d'ordonnancement temps réel - Sujet Final IPSA 2026
Auteur : Eytan Martiano & Gemini
"""
import time
import random
import ctypes
import matplotlib.pyplot as plt

# --- 1. MESURE DU WCET (τ1) ---
def task_1():
    """ Calcule le produit de deux grands nombres aléatoires """
    a = random.getrandbits(1024)
    b = random.getrandbits(1024)
    start = time.perf_counter()
    _ = a * b
    return time.perf_counter() - start

# Échantillonnage pour obtenir Min, Max, Q1, Q2, Q3 [cite: 4]
execution_times = sorted([task_1() for _ in range(1000)])
min_t, max_t = execution_times[0], execution_times[-1]
q1 = execution_times[int(len(execution_times) * 0.25)]
q2 = execution_times[int(len(execution_times) * 0.50)]
q3 = execution_times[int(len(execution_times) * 0.75)]

print(f"Statistiques τ1: Min={min_t:.6f}, Max (WCET C1)={max_t:.6f}")
print(f"Quartiles: Q1={q1:.6f}, Q2={q2:.6f}, Q3={q3:.6f}\n")

# --- 2. DÉFINITION DES TÂCHES ET UTILISATION ---
C1 = max_t * 1e4  # Facteur d'échelle pour la simulation
# [Capacité Ci, Période Ti] selon le tableau fourni 
tasks_def = [
    [C1, 10], [3, 10], [2, 20], [2, 20], [2, 40], [2, 40], [3, 80]
]

def verifier_utilisation(tasks):
    U = sum(Ci / Ti for Ci, Ti in tasks)
    status = "ordonnançable" if U <= 1 else "NON ordonnançable"
    print(f"Utilisation totale U = {U:.4f} -> Système {status} \n")
    return U

verifier_utilisation(tasks_def)

# --- 3. GÉNÉRATION DES JOBS (HYPERPÉRIODE = 80ms) ---
hyper_periode = 80 # [cite: 14]
jobs_list = []
for i, (Ci, Ti) in enumerate(tasks_def):
    for r_i in range(0, hyper_periode, Ti):
        jobs_list.append({
            'id': f"τ{i+1}", 'id_int': i+1, 'C': Ci, 'r': r_i, 'd': r_i + Ti
        })

# --- 4. INTERFACE C (DLL) ---
class JobC(ctypes.Structure):
    _fields_ = [("id", ctypes.c_int), ("c", ctypes.c_float), 
                ("r", ctypes.c_float), ("d", ctypes.c_float)]

try:
    lib = ctypes.CDLL('./projet.dll')
    lib.resoudre_ordonnancement.argtypes = [
        ctypes.POINTER(JobC), ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.c_int
    ]
except:
    print("Erreur: Assurez-vous que projet.dll est compilé et présent.")

# --- 5. FONCTION DE SIMULATION ---
def simulation(jobs_in, allow_tau5_miss):
    jobs_r = sorted([j.copy() for j in jobs_in], key=lambda x: x['r'])
    planning, temps_actuel, total_wait = [], 0, 0
    
    while jobs_r:
        # Fenêtre glissante de 8 jobs pour le backtracking en C 
        fenetre = jobs_r[:8]
        n = len(fenetre)
        c_jobs = (JobC * n)(*[JobC(j['id_int'], j['C'], j['r'], j['d']) for j in fenetre])
        indices = (ctypes.c_int * n)()
        
        lib.resoudre_ordonnancement(c_jobs, n, indices, allow_tau5_miss)
        
        for i in range(min(3, n)): # On fixe les 3 premiers résultats
            job = fenetre[indices[i]]
            start = max(temps_actuel, job['r'])
            end = start + job['C']
            wait = start - job['r']
            
            planning.append({'id': job['id'], 'start': start, 'end': end, 'd': job['d'], 'wait': wait})
            total_wait += wait
            temps_actuel = end
            # Retrait du job traité
            jobs_r = [j for j in jobs_r if not (j['id'] == job['id'] and j['r'] == job['r'])]
            
    return planning, total_wait

# --- 6. EXÉCUTION ET COMPARAISON ---
plan1, wait1 = simulation(jobs_list, 0) # Modèle 1 : Strict 
plan2, wait2 = simulation(jobs_list, 1) # Modèle 2 : τ5 Flexible

print(f"Résultat Modèle 1 (Strict) : Attente totale = {wait1:.4f} ms")
print(f"Résultat Modèle 2 (τ5 flexible) : Attente totale = {wait2:.4f} ms")

# --- 7. VISUALISATION ---
def plot_gantt(planning, title):
    fig, ax = plt.subplots(figsize=(12, 4))
    colors = {'τ1': 'red', 'τ2': 'blue', 'τ3': 'green', 'τ4': 'orange', 'τ5': 'purple', 'τ6': 'brown', 'τ7': 'pink'}
    for j in planning:
        ax.broken_barh([(j['start'], j['end']-j['start'])], (10, 5), facecolors=colors[j['id']], edgecolor='black')
        if j['end'] > j['d']: # Indicateur visuel d'échec de deadline
            ax.text(j['start'], 16, '!', color='red', weight='bold')
    ax.set_title(title)
    ax.set_xlabel("Temps (ms)")
    plt.tight_layout()
    plt.show()

plot_gantt(plan1, "Modèle 1 : Strict (Zéro Deadline Miss)")
plot_gantt(plan2, "Modèle 2 : τ5 peut rater sa Deadline")


# Correction : on utilise (fin - début) pour avoir la durée d'exécution
total_execution = sum(j['end'] - j['start'] for j in plan1)
idle_time = hyper_periode - total_execution

print(f"Total Workload (Sum of Ci): {total_execution:.4f} ms")
print(f"Total Idle Time: {idle_time:.4f} ms")

uu=total_execution/80
print(f"Utilisation U = {uu:.4f}")