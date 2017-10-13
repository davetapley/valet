import csv
from ortools.constraint_solver import pywrapcp

with open('responses.csv') as responses_csv:

    responses = csv.reader(responses_csv)

    emails = {}
    names = {}
    consecutive_shifts = {}
    available_shifts = {}

    vets = []

    for row in responses:
        n = responses.line_num - 1
        emails[n] = row[1]
        names[n] = row[2]
        consecutive_shifts[n] = 'One' in row[4]

        if 'Yes' in row[3]:
            vets.append(n)

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
    email = emails[n]
    consecutive_shift = consecutive_shifts[n]
    avail = available_shifts[n]
    print(f"{n} is {email} {consecutive_shift} {avail}")

solver = pywrapcp.Solver("schedule_shifts")

num_shifts = 12
num_slots = 2

slots = {}

for shift in range(num_shifts):
    for slot in range(num_slots):
        slots[(shift, slot)] = solver.IntVar(0, num_people - 1, f"slots({shift}, {slot})")

slots_flat = [slots[(shift, slot)] for shift in range(num_shifts) for slot in range(num_slots)]

works_shift = {}
works_slot = {}
for shift in range(num_shifts):
    for person in range(num_people):
        works_shift[(shift, person)] = solver.BoolVar(f"works_shift({shift}, {person})")
        for slot in range(num_slots):
                works_slot[(shift, slot, person)] = solver.BoolVar(f"works_slot({shift}, {slot}, {person})")

for shift in range(num_shifts):
    for person in range(num_people):
        solver.Add(works_shift[(shift, person)] == solver.Max([slots[(shift, slot)] == person for slot in range(num_slots)]))
        for slot in range(num_slots):
            solver.Add(works_slot[(shift, slot, person)] == solver.Max([slots[(shift, slot)] == person]))

for shift in range(num_shifts):
    # Different people in each slot in a shift
    solver.Add(solver.AllDifferent([slots[(shift, slot)] for slot in range(num_slots)]))

    # At least one veteran
    solver.Add(solver.Sum(works_shift[(shift, vet)] for vet in vets ) > 0)

for person in range(num_people):
    # Max two shifts per person
    solver.Add(solver.Sum([works_slot[(shift, slot, person)] for shift in range(num_shifts) for slot in range(num_slots)]) < 3)

# Consecutive shifts
#for shift in range(num_shifts):
#    for slot in range(num_slots):
#        for person in range(num_people):
#            if shift < num_shifts - 1:
#                solver.Add(works_shift[(shift, person)] == works_shift[(shift + 1, person)])

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
            name = names[collector.Value(0, slots[shift, slot])]
            print(F"{shift} {slot} {name}")
