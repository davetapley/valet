import csv
import argparse
from ortools.constraint_solver import pywrapcp

parser = argparse.ArgumentParser()
parser.add_argument('--vets', action='store_true')
parser.add_argument('num_slots', type=int)
args = parser.parse_args()

with open('responses.csv') as responses_csv:
    responses = csv.reader(responses_csv)

    emails = {}
    names = {}
    consecutive_shifts = {}
    available_shifts = {}

    vets = []
    splits = []

    for row in responses:
        n = responses.line_num - 1
        emails[n] = row[1]
        names[n] = row[2]

        if 'Yes' in row[3]:
            vets.append(n)

        if 'One' not in row[4]:
            splits.append(n)

        available_shifts[n] = set()
        if 'Early' in row[5]: available_shifts[n].update([0, 1])
        if 'Late' in row[5]:  available_shifts[n].update([2, 3])
        if 'Early' in row[6]: available_shifts[n].update([4, 5])
        if 'Late' in row[6]:  available_shifts[n].update([6, 7])
        if 'Early' in row[7]: available_shifts[n].update([8, 9])
        if 'Late' in row[7]:  available_shifts[n].update([10, 11])

num_people = len(emails)
print(f"%num_people people")

for n in range(num_people):
    name = names[n]
    avail = available_shifts[n]
    split = True if n in splits else False
    print(f"{n} is {name} {split} {avail}")

solver = pywrapcp.Solver("schedule_shifts")

num_shifts = 12
num_slots = args.num_slots

slots = {}

for shift in range(num_shifts):
    for slot in range(num_slots):
        slots[(shift, slot)] = solver.IntVar(0, num_people - 1, f"slots({shift}, {slot})")

slots_flat = [slots[(shift, slot)] for shift in range(num_shifts) for slot in range(num_slots)]

works_shift = {}
for shift in range(num_shifts):
    for person in range(num_people):
        works_shift[(shift, person)] = solver.BoolVar(f"works_shift({shift}, {person})")

for shift in range(num_shifts):
    for person in range(num_people):
        solver.Add(works_shift[(shift, person)] == solver.Max([slots[(shift, slot)] == person for slot in range(num_slots)]))

for shift in range(num_shifts):
    # Different people in each slot in a shift
    solver.Add(solver.AllDifferent([slots[(shift, slot)] for slot in range(num_slots)]))

    # At least one veteran
    if args.vets:
        solver.Add(solver.Sum(works_shift[(shift, vet)] for vet in vets ) > 0)

    # Split shift requests
    if shift not in [3, 7, 11]: # don't care if end of day shift
        for split in splits:
            adj = [shift, shift+1]
            solver.Add(solver.Sum(works_shift[(n, split)] for n in adj) < 2)

    # Availability
    for person in range(num_people):
        if shift not in available_shifts[person]:
            solver.Add(works_shift[(shift, person)] == False)

for person in range(num_people):
    # Max two shifts per person
    solver.Add(solver.Sum([works_shift[(shift, person)] for shift in range(num_shifts)]) < 3)

#Friends
for shift in range(num_shifts):
    solver.Add(works_shift[(shift, 1)] == works_shift[(shift, 2)])
    solver.Add(works_shift[(shift, 7)] == works_shift[(shift, 5)])
    solver.Add(works_shift[(shift, 7)] == works_shift[(shift, 6)])

# Create the decision builder.
db = solver.Phase(slots_flat, solver.CHOOSE_FIRST_UNBOUND, solver.ASSIGN_MIN_VALUE)
# Create the solution collector.
solution = solver.Assignment()
solution.Add(slots_flat)
collector = solver.FirstSolutionCollector(solution)

solver.Solve(db, [collector])
print("Solutions found:", collector.SolutionCount())
print("Time:", solver.WallTime(), "ms")

if collector.SolutionCount() > 0:
    for shift in range(num_shifts):
        for slot in range(num_slots):
            person = collector.Value(0, slots[shift, slot])
            name = names[person]
            vet = ' (vet)' if person in vets else ''
            print(F"{shift} {slot} {person} {name} {vet}")

