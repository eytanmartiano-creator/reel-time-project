import subprocess
import re
import numpy as np
import matplotlib.pyplot as plt
from itertools import groupby, permutations, product, islice

FILE_C = "main.c"
EXE_NAME = "mesure_wcet.exe"


def get_wcet_ns():
    result = subprocess.run(["./" + EXE_NAME], capture_output=True, text=True, check=True)
    match = re.search(r"WCET of the multiplication:\s*([0-9]+)\s*ns", result.stdout)
    return int(match.group(1)) if match else 100


def utilization(task_matrix):
    U = sum(C / T for C, T in task_matrix)
    status = "Schedulable ✅" if U <= 1 else "NOT schedulable ❌"
    return U, status


# --- STATISTIQUES ---
measurements_ns = [get_wcet_ns() for _ in range(100)]
C1_max_ns = max(measurements_ns)
C1_min_ns = min(measurements_ns)
Q1, Q2, Q3 = np.percentile(measurements_ns, [25, 50, 75])

print("--- 1. Statistics for Task 1 ---")
print(f"Max : {C1_max_ns} ns")
print(f"Min : {C1_min_ns} ns")
print(f"Q1  : {Q1} ns | Q2 : {Q2} ns | Q3 : {Q3} ns")

# --- PARAMÈTRES ---
C1_ms = C1_max_ns / 1e6  # ns → ms
hyperperiod = 80

task_matrix = np.array([
    [C1_ms, 10], [3, 10], [2, 20], [2, 20], [2, 40], [2, 40], [3, 80]
])

u_val, u_status = utilization(task_matrix)
print(f"\n--- 2. Theoretical Analysis ---")
print(f"U = {u_val:.4f} | {u_status}")


# --- GÉNÉRATION DES JOBS sous forme de tuples (name, C, T, release, deadline) ---
def generate_jobs(task_matrix, hp=80):
    job_list = []
    for i, (C, T) in enumerate(task_matrix):
        for release in range(0, hp, int(T)):
            name = f"τ{i+1}-{release}"
            deadline = release + T
            job_list.append((name, C, T, release, deadline))
    return sorted(job_list, key=lambda j: j[3])  # tri par release


# --- GÉNÉRATION DES ORDONNANCEMENTS ---
def generate_schedules(job_list, max_results=100):
    sorted_jobs = sorted(job_list, key=lambda j: j[3])
    groups = [list(g) for _, g in groupby(sorted_jobs, key=lambda j: j[3])]
    perm_groups = [permutations(g) for g in groups]
    raw = islice(product(*perm_groups), max_results)
    return [sum(sched, ()) for sched in raw]


# --- TEMPS DE RÉPONSE ---
def compute_response_times(schedules):
    worst_case_list = []
    cumulative_list = []

    for seq in schedules:
        rt_values = []
        total = 0
        prev_rt = 0
        prev_arr = 0

        for job in seq:
            name, exec_time, period, arrival, deadline = job
            if not rt_values:
                rt = exec_time
            else:
                rt = exec_time + max(prev_rt - (arrival - prev_arr), 0)
            rt_values.append(rt)
            prev_rt = rt
            prev_arr = arrival
            total += rt

        worst_case_list.append(max(rt_values))
        cumulative_list.append(total)

    return worst_case_list, cumulative_list


# --- VÉRIFICATION DES DEADLINES ---
def check_deadline_violations(seq):
    clock = 0
    violations = []

    for job in seq:
        name, exec_time, period, arrival, deadline = job
        start = max(clock, arrival)
        finish = start + exec_time
        if finish > deadline:
            violations.append((name, finish, deadline, finish - deadline))
        clock = finish

    return len(violations) == 0, violations

# --- SÉLECTION DU MEILLEUR ORDONNANCEMENT ---
def select_optimal_schedule(candidates, hp):
    wcrt_per_seq, total_rt_per_seq = compute_response_times(candidates)
    violation_counts = [len(check_deadline_violations(seq)[1]) for seq in candidates]
    fewest_violations = min(violation_counts)
    shortlist = [ {  'idx': i,
            'violations': violation_counts[i],
            'wcrt': wcrt_per_seq[i],
            'total_rt': total_rt_per_seq[i]}
        for i in range(len(candidates))
        if violation_counts[i] == fewest_violations]
    
    optimal_idx = min(shortlist, key=lambda x: x['total_rt'])['idx']
    optimal_seq = candidates[optimal_idx]
    job_details = []
    prev_rt, prev_arr, acc_rt, acc_wait = 0, 0, 0, 0

    for i, job in enumerate(optimal_seq):
        name, exec_time, period, arrival, deadline = job
        rt = exec_time if i == 0 else exec_time + max(prev_rt - (arrival - prev_arr), 0)
        job_details.append({'name': name, 'rt': rt})
        prev_rt, prev_arr = rt, arrival
        acc_rt += rt
        acc_wait += rt - exec_time

    passed, violations = check_deadline_violations(optimal_seq)
    idle = hp - sum(job[1] for job in optimal_seq)

    return {'optimal_seq':   optimal_seq,
        'optimal_idx':   optimal_idx,
        'shortlist':     shortlist,
        'wcrt':          wcrt_per_seq[optimal_idx],
        'total_rt':      total_rt_per_seq[optimal_idx],
        'violations_count': violation_counts[optimal_idx],
        'job_details':   job_details,
        'acc_rt':        acc_rt,
        'acc_wait':      acc_wait,
        'passed':        passed,
        'violations':    violations,
        'idle':          idle,
    }


# --- EXÉCUTION ---
job_list   = generate_jobs(task_matrix, hp=hyperperiod)
candidates = generate_schedules(job_list, max_results=100)
result     = select_optimal_schedule(candidates, hyperperiod)

optimal_seq = result['optimal_seq']
optimal_idx = result['optimal_idx']

# --- Résumé ---
print(f"\nTotal Response Time : {result['acc_rt']:.2f} ms")
print(f"Total Waiting Time  : {result['acc_wait']:.2f} ms")
# --- Idle Time Analysis ---
total_workload = sum(job[1] for job in optimal_seq)   # job[1] = exec_time (C)
idle_time = hyperperiod - total_workload

print(f"\n--- Idle Time Analysis ---")
print(f"Total Workload : {total_workload:.4f} ms")
print(f"Idle Time      : {idle_time:.4f} ms")
print(f"Real CPU Load  : {(total_workload / hyperperiod) * 100:.2f}%")


# --- Comparaison des schedules ---
print("\nSchedule comparison (violations | WCRT | total RT):")
for entry in result['shortlist'][:8]:
    print(f"  #{entry['idx']:>3} — {entry['violations']} violations | "
          f"WCRT = {entry['wcrt']:.2f} ms | total RT = {entry['total_rt']:.2f} ms")

print(f"\nOptimal schedule → #{optimal_idx} | "
      f"{result['violations_count']} violations | "
      f"WCRT = {result['wcrt']:.2f} ms | "
      f"total RT = {result['total_rt']:.2f} ms")
print(f"Execution order : {[job[0] for job in optimal_seq]}")

# --- Détail RT par job ---
for detail in result['job_details']:
    print(f"  {detail['name']} : RT = {detail['rt']:.2f} ms")

# --- Violations ---
if result['passed']:
    print("\nAll deadlines respected ✅")
else:
    print("\nDeadline violations ❌:")
    for name, finish, deadline, overrun in result['violations']:
        print(f"  {name} — finish = {finish:.2f}, deadline = {deadline:.2f}, overrun = {overrun:.2f} ms")



def draw_gantt(optimal_seq, candidates, hyperperiod=80):
    fig, axes = plt.subplots(
        len(set(j[0].split('-')[0] for j in optimal_seq)),
        1, figsize=(14, 8), sharex=True
    )
    fig.patch.set_facecolor('#FAFAFA')

    COLORS = {
        'τ1': '#185FA5', 'τ2': '#0F6E56', 'τ3': '#993C1D',
        'τ4': '#854F0B', 'τ5': '#534AB7', 'τ6': '#993556', 'τ7': '#5F5E5A'
    }

    task_ids = list(dict.fromkeys(j[0].split('-')[0] for j in optimal_seq))
    rows = {tid: [] for tid in task_ids}

    clock = 0
    for job in optimal_seq:
        name, C, T, arrival, deadline = job
        tid = name.split('-')[0]
        start = max(clock, arrival)
        finish = start + C
        missed = finish > deadline
        rows[tid].append({'name': name, 'start': start, 'finish': finish,
                          'deadline': deadline, 'missed': missed})
        clock = finish

    for ax, tid in zip(axes, task_ids):
        ax.set_facecolor('#F8F8F8')
        ax.set_yticks([])
        ax.set_ylabel(tid, rotation=0, labelpad=20, va='center', fontsize=11)
        ax.set_xlim(0, hyperperiod)
        ax.set_ylim(0, 1)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.spines['bottom'].set_color('#E0E0E0')
        ax.xaxis.grid(True, linestyle='--', alpha=0.4, color='#CCCCCC')

        for b in rows[tid]:
            ec = '#E24B4A' if b['missed'] else COLORS[tid]
            lw = 1.5 if b['missed'] else 0
            ax.barh(0.5, b['finish'] - b['start'], left=b['start'],
                    height=0.55, color=COLORS[tid], edgecolor=ec, linewidth=lw,
                    align='center', zorder=3)
            ax.text((b['start'] + b['finish']) / 2, 0.5, b['name'],
                    ha='center', va='center', fontsize=8,
                    color='white', fontweight='bold', zorder=4)
            ax.axvline(b['deadline'], color='#CCCCCC' if not b['missed'] else '#E24B4A',
                       linewidth=0.8, linestyle='-', zorder=2)

    axes[-1].set_xlabel("Time (ms)", fontsize=10)
    fig.suptitle("Gantt — Optimal schedule", fontsize=12, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig("gantt.png", dpi=150, bbox_inches='tight')
    plt.show()

draw_gantt(optimal_seq, candidates, hyperperiod)