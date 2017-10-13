import csv
import argparse
from collections import defaultdict
from ortools.constraint_solver import pywrapcp

parser = argparse.ArgumentParser()
parser.add_argument('--vets', action='store_true')
parser.add_argument('--splits', action='store_true')
parser.add_argument('shift_size', type=int)
args = parser.parse_args()
shift_size = args.shift_size

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

        if 'Two' in row[4]:
            splits.append(n)

        available_shifts[n] = set()
        if 'Early' in row[5]: available_shifts[n].update([0, 1])
        if 'Late' in row[5]:  available_shifts[n].update([2, 3])
        if 'Early' in row[6]: available_shifts[n].update([4, 5])
        if 'Late' in row[6]:  available_shifts[n].update([6, 7])
        if 'Early' in row[7]: available_shifts[n].update([8, 9])
        if 'Late' in row[7]:  available_shifts[n].update([10, 11])

for n in range(len(names)):
    name = names[n]
    avail = available_shifts[n]
    split = True if n in splits else False
    print(f"{n} is {name} {split} {avail}")


solver = pywrapcp.Solver("schedule_shifts")

num_people = len(emails)
num_slots = num_people
num_shifts = 12

print(f"{num_people} people, {shift_size} at a time, for {num_shifts} shifts")

### VARIABLES ###
slots = {}

for person in range(num_people):
    for shift in range(num_shifts):
        slots[(person, shift)] = solver.IntVar(0, num_slots - 1, f"slots({person}, {shift})")

slots_flat = [slots[(person, shift)] for person in range(num_people) for shift in range(num_shifts)]

people = {}
for slot in range(num_slots):
    for shift in range(num_shifts):
        people[(slot, shift)] = solver.IntVar(0, num_people - 1, f"people({slot}, {shift})")

# Set relationships between slots and people.
for shift in range(num_shifts):
    people_for_shift = [people[(slot, shift)] for slot in range(num_slots)]

    for person in range(num_people):
      s = slots[(person, shift)]
      solver.Add(s.IndexOf(people_for_shift) == person)

# Make assignments different on each shift
for shift in range(num_shifts):
    solver.Add(solver.AllDifferent([slots[(person, shift)] for person in range(num_people)]))

    # Don't care if multiple people in slot 0
    solver.Add(solver.AllDifferent([people[(slot, shift)] for slot in range(1, num_slots)]))

works_shift = {}
for person in range(num_people):
    for shift in range(num_shifts):
        works_shift[(person, shift)] = solver.BoolVar(F"works_shift({person}, {shift})")

for person in range(num_people):
    for shift in range(num_shifts):
        solver.Add(works_shift[(person, shift)] == (slots[(person, shift)] < shift_size))

# Availability
for person in range(num_people):
 for shift in range(num_shifts):
     if shift not in available_shifts[person]:
         solver.Add(works_shift[(person, shift)] == False)

# At least one veteran
if args.vets:
    for shift in range(num_shifts):
        solver.Add(solver.Sum(works_shift[(vet, shift)] for vet in vets ) > 0)

for person in range(num_people):
    # Max two shifts per person
    solver.Add(solver.MemberCt(solver.Sum([works_shift[(person, shift)] for shift in range(num_shifts)]), [0, 2]))

#Friends
for shift in range(num_shifts):
    solver.Add(works_shift[(1, shift)] == works_shift[(2, shift)])
    solver.Add(works_shift[(7, shift)] == works_shift[(6, shift)])
    solver.Add(works_shift[(7, shift)] == works_shift[(5, shift)])

if args.splits:
    # Split shift requests
    for split in splits:
        for shift in range(num_shifts):
            if shift not in [3, 7, 11]: # don't care if end of day shift
                adj = [shift, shift+1]
                solver.Add(solver.Sum(slots[(split, n)] < shift_size for n in [shift, shift+1]) < 2)

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
    people_with_shift = defaultdict(set)

    print('#### SHIFTS ####')
    for shift in range(num_shifts):
        print(F"Shift {shift}")
        for person in range(num_people):
            slot = collector.Value(0, slots[(person, shift)])
            if slot < shift_size:
                people_with_shift[person].add((shift))
                name = names[person]
                vet = ' *' if person in vets else ''
                print(F"    {person} {name}{vet}")

    print()
    print('#### PEOPLE WORKING ####')
    print(F"{len(people_with_shift)} working:")
    for person, shifts in people_with_shift.items():
        name = names[person]
        vet = ' *' if person in vets else ''
        print(F"{person} {name}{vet} {shifts}")

    print()
    print('#### PEOPLE NOT WORKING ####')
    people_without_shift = set(range(num_people-1)) - people_with_shift.keys()
    print(F"{len(people_without_shift)} not working:")
    for person in people_without_shift:
        name = names[person]
        print(name)
