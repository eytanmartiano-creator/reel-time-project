import subprocess
import re
import ctypes
import os
import numpy as np
import matplotlib.pyplot as plt

FILE_C = "main.c"
DLL_NAME = "projet.dll"
EXE_NAME = "mesure_wcet.exe"

def preparer_environnement():
    subprocess.run(["gcc", FILE_C, "-o", EXE_NAME, "-mconsole"], check=True)
    subprocess.run(["gcc", "-shared", "-o", DLL_NAME, FILE_C], check=True)

def get_wcet_ns():
    result = subprocess.run(["./" + EXE_NAME], capture_output=True, text=True, check=True)
    match = re.search(r"WCET of the multiplication:\s*([0-9]+)\s*ns", result.stdout)
    return int(match.group(1)) if match else 500000

def Utilization(M):
    m, n = np.shape(M)
    U = 0
    for i in range(m):
        Ci, Ti = M[i]
        U += Ci / Ti
    if U <= 1:
        S = "Is it schedulable"
    else:
        S = "It's NOT schedulable"
    return U, S

preparer_environnement()

# --- ANALYSE STATISTIQUE INITIALE ---
measurements_ns = [get_wcet_ns() for _ in range(100)]
C1_max_ns = max(measurements_ns)

print(f"--- 1. Statistics for Task 1 ---")
print(f"Max: {C1_max_ns} ns")

# --- ANALYSE THÉORIQUE ---
C1_ms = C1_max_ns / 1e6
M = np.array([
    [C1_ms, 10], [3, 10], [2, 20], [2, 20], [2, 40], [2, 40], [3, 80]
])

u_val, status = Utilization(M)
print(f"\n--- 2. Theoretical Analysis ---")
print(f"U = {u_val:.4f} | {status}")

# --- CHARGEMENT DLL ---
current_dir = os.path.dirname(os.path.abspath(__file__))
dll_path = os.path.join(current_dir, DLL_NAME)
try:
    if os.name == 'nt':
        os.add_dll_directory(current_dir)
        gcc_path = subprocess.check_output(["where", "gcc"]).decode().split('\n')[0].strip()
        os.add_dll_directory(os.path.dirname(gcc_path))
    lib = ctypes.CDLL(dll_path, winmode=0)
except:
    lib = ctypes.WinDLL(dll_path)

class JobC(ctypes.Structure):
    _fields_ = [("id", ctypes.c_int), ("c", ctypes.c_float), ("r", ctypes.c_float), ("d", ctypes.c_float)]

lib.resoudre_ordonnancement.argtypes = [ctypes.POINTER(JobC), ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.c_int]

def simulation(allow_tau5_miss):
    hp = 80
    jobs_list = []
    for i in range(len(M)):
        Ci, Ti = M[i]
        for r_i in range(0, hp, int(Ti)):
            jobs_list.append({'id': f"τ{i+1}", 'id_int': i+1, 'C': Ci, 'r': r_i, 'd': r_i + Ti})
    
    jobs_r = sorted(jobs_list, key=lambda x: x['r'])
    planning, temps_actuel, total_wait = [], 0, 0
    
    while jobs_r:
        fenetre = jobs_r[:8]
        n_jobs = len(fenetre)
        c_jobs = (JobC * n_jobs)(*[JobC(j['id_int'], j['C'], j['r'], j['d']) for j in fenetre])
        indices = (ctypes.c_int * n_jobs)()
        lib.resoudre_ordonnancement(c_jobs, n_jobs, indices, allow_tau5_miss)
        
        for i in range(min(3, n_jobs)):
            job = fenetre[indices[i]]
            start = max(temps_actuel, job['r'])
            planning.append({'id': job['id'], 'start': start, 'end': start + job['C']})
            temps_actuel = start + job['C']
            total_wait += (start - job['r'])
            jobs_r = [j for j in jobs_r if not (j['id'] == job['id'] and j['r'] == job['r'])]
            
    return planning, total_wait

# --- FONCTION RECAP ---
def print_recap(plan, title):
    print(f"\n--- Execution Order ({title}) ---")
    order = " -> ".join([j['id'] for j in plan])
    print(order)

# --- EXÉCUTION ---
plan_strict, wait_strict = simulation(0)
plan_flex, wait_flex = simulation(1)

# Affichage du récapitulatif à l'écrit
print_recap(plan_strict, "STRICT")
print_recap(plan_flex, "FLEXIBLE")

# --- ANALYSE IDLE TIME ---
hp = 80
total_workload = sum(j['end'] - j['start'] for j in plan_strict)
idle_time = hp - total_workload

print(f"\n--- 3. Idle Time Analysis ---")
print(f"Total Workload: {total_workload:.4f} ms")
print(f"Idle Time: {idle_time:.4f} ms")
print(f"Real CPU Load: {(total_workload/hp)*100:.2f}%")

# --- GRAPHIQUES ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
colors = {'τ1':'red', 'τ2':'blue', 'τ3':'green', 'τ4':'orange', 'τ5':'purple', 'τ6':'brown', 'τ7':'pink'}

def draw_gantt(ax, plan, title):
    for j in plan:
        ax.broken_barh([(j['start'], j['end']-j['start'])], (10, 5), facecolors=colors[j['id']], edgecolor='black')
        ax.text(j['start'] + (j['end']-j['start'])/2, 12.5, j['id'], color='white', ha='center', va='center', fontsize=7)
    ax.set_title(title)
    ax.set_yticks([])

draw_gantt(ax1, plan_strict, "Gantt STRICT")
draw_gantt(ax2, plan_flex, "Gantt FLEXIBLE")
plt.xlabel("Time (ms)")
plt.tight_layout()
plt.show()