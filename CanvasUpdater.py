import requests #For interfacing with websites
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from dateutil import parser
import teacher_data #A file with all the credentials, a blank template is in the repository
from MathAcademyScoreExtractor import pull_math_academy_roster, pull_math_academy_assignment_data, process_task_list

debug_mode = False

#urls
canvas_domain = "https://pasadena.instructure.com"
course_domain = f"{canvas_domain}/api/v1/courses"

#localize imported data
access_token = teacher_data.access_token
course_ids = teacher_data.course_ids
sitework_group_ids = teacher_data.sitework_group_ids

#UPDATE - Represents last digit of year
semester = 6

#Headers for the web requests
canvas_headers = {"Authorization": f"Bearer {access_token}"}

#Set the directories
data_dir = Path(__file__).resolve().parent/"data"
data_dir.mkdir(exist_ok=True)
rosters_dir = data_dir/"rosters"
rosters_dir.mkdir(exist_ok=True)
tasks_dir = data_dir/"task_data"
tasks_dir.mkdir(exist_ok=True)

#Properties sharted by all weekly homework assaignments
assaignment_template = {
            "description": "Weekly Assignment Made using API.",
            "submission_types":["none"],
            "points_possible": 0,
            "grading_type": "points",
            "published": True,
            "post_to_sis": True,
        }

#Prints the Group IDS to use for new Assignment creation
def assignment_group_ids(grade = None): 
    if grade == None:
        for grade_level in course_ids:
            assignment_group_ids(grade_level)
        return
    course_id = course_ids[grade]
    url = f'{course_domain}/{course_id}/assignment_groups'
    groups = requests.get(url, headers=canvas_headers).json()
    print(groups)

#Stores a dictionary of students enrolled on canvas
# as user id: name
def update_canvas_roster(grade):
    if grade == None:
        for grade_level in course_ids:
            update_canvas_roster(grade_level)
        return
    course_id = course_ids[grade]
    url = f'{course_domain}/{course_id}/enrollments'
    params = {
        "type[]": "StudentEnrollment",
        "per_page": 100
    }
    raw_roster = requests.get(url, headers=canvas_headers, params=params).json()
    roster = {student['user_id']: student['user']['name'] for student in raw_roster}
    with open(rosters_dir/('canvas_roster_'+str(grade)+'.json'),'w') as file:
        json.dump(roster, file, indent=4)

#Converts Last, First format of name to First Last
#MA uses Last, First. Canvas uses First Last
def normalize_name(name):
    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        return f"{first} {last}"
    else:
        return name

#Creates a weekly homework assignment with a specified index, date, and number of points
#Date is actually the day after it is meant to be due because of time zone change
def create_homework_assignment(grade, weekNumber, date, points):
    course_id = course_ids[grade]
    url = f'{course_domain}/{course_id}/assignments'
    assignment = assaignment_template
    assignment["name"] = "Weekly XP " + str(weekNumber)
    assignment["points_possible"] = points
    assignment["due_at"] = date+"T06:59:00Z"
    assignment["assignment_group_id"] = sitework_group_ids[grade]
    payload = {
        "assignment": assignment
    }
    response = requests.post(url, headers=canvas_headers, json=payload)

#Will need to replace load_weeks function
#Adds all XP Assignments for the current semester
'''
def create_homework_assignments(grade = None): 
    if grade == None:
        create_homework_assignments(6)
        create_homework_assignments(8)
        return
    assignment_names = [assignment['name'] for
                        assignment in load_assignments(grade)]
    weeks = load_weeks()
    for week in weeks:
        if "Weekly XP " + str(week[0]) not in assignment_names:
            create_homework_assignment(grade, week[0], week[1], week[2])
'''

#Returns a list of assignment dictionaries with keys
# 'id', 'due_at', 'points_possible', 'name'
def load_assignments(grade):
    course_id = course_ids[grade]
    url = f'{course_domain}/{course_id}/assignments'
    params = {"per_page": 100}
    response = requests.get(url, headers=canvas_headers,
                            params=params)
    keys = ['id', 'due_at', 'points_possible', 'name']
    assignments = [{key:assignment[key] for key in keys}
                   for assignment in response.json()]
    return assignments

#Checks if a score is different enough
# to be not a rounding error
def needs_update(n_old,n_new):
    try:
        n = float(n_new)
    except ValueError:
        return False
    try:
        return abs(n-float(n_old)) > 0.001
    except (ValueError, TypeError):
        return True

#Loads the scores that are on canvas from a json file
#Formatted as a nested dictionary
#student id -> assignment id -> score
def load_scores(grade):
    try:
        file = open(data_dir/('canvas_scores_'+str(grade)+'.json'),'r')
        return json.load(file)
    except FileNotFoundError:
        save_canvas_scores(grade)
        load_scores(grade)

#Updates the scores in a json file with the scores from canvas
def save_canvas_scores(grade):
    course_id = course_ids[grade]
    all_scores = {}
    assignment_list = load_assignments(grade)
    assignment_ids = [assignment['id'] for assignment in assignment_list]
    for assignment_id in assignment_ids:
        url = f"{course_domain}/{course_id}/assignments/{assignment_id}/submissions"
        params = {"per_page": 100}
        response = requests.get(url, headers=canvas_headers, params=params)
        submissions = response.json()
        for submission in submissions:
            student_id = submission.get('user_id')
            score = submission.get('score', 0)
            if student_id not in all_scores:
                all_scores[student_id] = {}
            all_scores[student_id][assignment_id] = score
    json.dump(all_scores, open(data_dir/('canvas_scores_'+str(grade)+'.json'),'w'), indent = 4)    

#In Progress
#Computes points per week and updates them
def update_xp_scores(grade = None, canvas_id = None, with_refresh = True, update_after = True):
    if grade == None:
        for grade in course_ids:
            if debug_mode:
                print(f"grade = {grade}")
            update_xp_scores(grade, canvas_id, with_refresh, update_after)
        return
    if canvas_id == None:
        print(f"Updating {grade}th grade class")
        for canvas_id in canvas_roster[grade]:
            if debug_mode:
                print(f"canvas_id = {canvas_id}")
            update_xp_scores(grade, canvas_id, with_refresh, False)
            print(f"{canvas_roster[grade][canvas_id]} updated")
        if update_after:
            save_canvas_scores(grade)
            print("Saved Scores Updated")
        return
    name = canvas_roster[grade][canvas_id]
    if debug_mode:
        print(f"name = {name}")
    if with_refresh:
        pull_math_academy_assignment_data(grade, name)
    xp_totals = weekly_total_xp(name)
    #Ignore current week, 40 xp is 1 point
    points = {week:xp_totals[week]/40 for week in range(len(xp_totals)-1)}
    apply_extra_credit_discount(points)
    prior_scores = canvas_scores[grade][canvas_id]
    assignments = load_assignments(grade)
    homeworks = []
    exceptions = xp_update_exceptions(canvas_id)
    for assignment in assignments:
        if (len(assignment['name']) > 10 and assignment['name'][:10] == 'Weekly XP '):
            week = int(assignment['name'][10:])
            assignment_id = str(assignment['id'])
            if (week not in exceptions and
                week in points.keys() and
                needs_update(prior_scores[assignment_id],points[week])):
                homeworks.append(assignment)
    push_update_to_canvas(homeworks, prior_scores, grade, canvas_id, points)
    if update_after:
        save_canvas_scores(grade)
        print("Saved Scores Updated")

#updates the scores which need to be based on the prior_scores and points
def push_update_to_canvas(homeworks, prior_scores, grade, canvas_id, points):
    course_id =  course_ids[grade]
    for assignment in homeworks:
        week = int(assignment['name'][10:])
        assignment_id = str(assignment['id'])
        if (week < len(points) and
            needs_update(prior_scores[assignment_id],points[week])):
            name = canvas_roster[grade][canvas_id]
            if (prior_scores[assignment_id] == None or
                input(f"Update {name} score in week {week} from { prior_scores[assignment_id]}"+
                      f"to {points[week]}? (y/n)") == 'y'):
                url = f"{course_domain}/{course_id}/assignments/{assignment_id}/submissions/{canvas_id}"
                response = requests.put(url, headers=canvas_headers, json={
                    "submission": {
                        "posted_grade": str(points[week]),
                        "grade": str(points[week])
                    }
                })
                if response.status_code != 200:
                    print(f"Failed To Update {name} - {assignment_id}:{response.text}")
                else:
                    print(f"Updated {assignment['name']} - {name}:{prior_scores[assignment_id]}->{points[week]}")

#XP beyond 200 is supposed to count half, so points beyond 5 are half
def apply_extra_credit_discount(points):
    for week in range(len(points)):
        if points[week] > 5:
            points[week] = 5+(points[week]-5)/2
    return

#Looks at the list of tasks and determines the number of xp in each week
def weekly_total_xp(student_name):
    start_date = datetime(2025,12,29) #Represents one week before, so week 0 is all of summer
    today = datetime.today()
    with open(tasks_dir/(student_name+"_Task_List.json"),'r') as file:
        tasks = json.load(file)
    xp_totals = [0 for _ in range(1+(today-start_date).days//7)]
    for task in tasks.values():
        date = parser.parse(task['date'])
        if date > datetime.today():
            date = date.replace(year = 2025)
        week = (date-start_date).days//7
        if week < 0:
            week = 0
        xp_totals[week] += task['points']
    return xp_totals

#Exceptions to the Update due to special circumstances such as being not yet enrolled
def xp_update_exceptions(canvas_id = None):
    try:
        with open("update_exceptions.json",'r') as file:
            exceptions = json.load(file)
    except:
        exceptions = {}
    if canvas_id == None:
        return exceptions
    elif canvas_id not in exceptions.keys():
        return []
    else:
        return exceptions[canvas_id]

#Identifies students who did a disproportianate amount of xp
#Returns the statistics (average and variance) and a list of students who are outside range
#Does not work for grade 10
def flag_students_week_xp(grade = None, z_squared_cutoff = 3):
    if grade == None:
        flagged_ids = {}
        stats = {}
        for grade_level in course_ids:
            stats[grade_level], flagged_ids[grade_level] = flag_students_week_xp(grade_level)
        return stats, flagged_ids
    this_week_xps = {}
    for canvas_id, student_name in canvas_roster[grade].items():
        this_week_xps[canvas_id] = weekly_total_xp(student_name)[-2]
    stats = {}
    stats['average'] = sum(this_week_xps.values())/len(this_week_xps)
    average = stats['average']
    stats['variance'] = sum([(xp-average)**2 for xp in this_week_xps.values()])/len(this_week_xps)
    flagged_ids =[]
    for student in this_week_xps:
        if (this_week_xps[student]-average)**2 > z_squared_cutoff*stats['variance']:
            flagged_ids.append(student)
    return stats, flagged_ids

#In development: meant to get all weeks each student was outside the range
def flag_students_weeks_xp(grade = None, z_squared_cutoff = 3):
    if grade == None:
        flagged_ids = {}
        stats = {}
        for grade_level in course_ids:
            stats[grade_level], flagged_ids[grade_level] = flag_students_weeks_xp(grade_level)
        return stats, flagged_ids
    week_xps = {}
    for canvas_id, student_name in canvas_roster[grade].items():
        week_xps[canvas_id] = weekly_total_xp(student_name)[1:-1]
    stats = {'averages':{},'variances':{}}
    for week in range(len(next(iter(week_xps.values())))):
        stats['averages'][week] = sum([week_xps[canvas_id][week] for canvas_id in week_xps])/len(week_xps)
    for week in range(len(next(iter(week_xps.values())))):
        average = stats['averages'][week]
        stats['variances'][week] = sum([(week_xps[canvas_id][week]-average)**2 for canvas_id in week_xps])/len(week_xps)
    flagged_ids = {}
    for week in stats['averages']:
        flagged_ids[week] = {}
        for student in week_xps:
            if (week_xps[student][week]-stats['averages'][week])**2 > z_squared_cutoff*stats['variances'][week]:
                flagged_ids[week][student] = week_xps[student][week]
    return stats, flagged_ids

#Loads data which is called for multiple times at file run
try:
    canvas_roster = {}
    for grade in course_ids:
        with open(rosters_dir/f'canvas_roster_{grade}.json','r') as file:
            canvas_roster[grade] = json.load(file)
except FileNotFoundError:
    update_canvas_roster(None)
canvas_scores = {}
for grade in course_ids:
    canvas_scores[grade]=load_scores(grade)

def prompt_to_update_scores():
    prompt = ("Update XP Scores?\n"+
            "0) Update none\n" +
            "1) Update 6 and 8\n"+
            "6) Update grade 6\n"+
            "8) Update grade 8\n"+
            "10) Update grade 10 (In Progress)\n")
    try:
        grade = int(input(prompt))
    except:
        print("Not a valid input")
        grade = 0
    if grade == 1: #update all
        start_time = time.perf_counter()
        update_xp_scores()
        end_time = time.perf_counter()
        elapsed_time = end_time-start_time
        print(f"Time to completion: {elapsed_time:.6f} seconds")
    elif grade == 10:
        pull_math_academy_assignment_data(grade)
        roster = json.load(open(rosters_dir/("MA_Roster_"+str(grade)+".json"),"r"))
        for name in roster:
            xp_totals = weekly_total_xp(name)
            points = {week:xp_totals[week]/40 for week in range(len(xp_totals)-1)}
            apply_extra_credit_discount(points)
            total_points = sum(points.values())-points[0]-points[max(points.keys())]
            print(name, total_points)
    elif grade > 0:
        start_time = time.perf_counter()
        update_xp_scores(grade)
        end_time = time.perf_counter()
        elapsed_time = end_time-start_time
        print(f"Time to completion: {elapsed_time:.6f} seconds")

prompt_to_update_scores()

prompt = ("Flag Students?\n"+
          "1) Annomolous xp this week\n"+
          "2) Annomolous xp all weeks\n")
flags = input(prompt)
if flags == '1':
    stats, flagged_students = flag_students_week_xp()
    for grade_level in flagged_students:
        print(f"Average: {stats[grade_level]['average']}\n"+
              f"Standard Deviation: {stats[grade_level]['variance']**(0.5)}")
        for canvas_id in flagged_students[grade_level]:
            name = canvas_roster[grade_level][canvas_id]
            print(f"{canvas_roster[grade_level][canvas_id]}: {weekly_total_xp(name)[-2]} xp")
if flags == '2':
    stats, flagged_students = flag_students_weeks_xp()
    for grade_level in flagged_students:
        for week in flagged_students[grade_level]:
            print(f"Week {week+1} Average: {stats[grade_level]['averages'][week]}\n"+
                  f"Week {week+1} Standard Deviation: {stats[grade_level]['variances'][week]**(0.5)}")
            for canvas_id in flagged_students[grade_level][week]:
                name = canvas_roster[grade_level][canvas_id]
                print(f"{canvas_roster[grade_level][canvas_id]}: {flagged_students[grade_level][week][canvas_id]}")
