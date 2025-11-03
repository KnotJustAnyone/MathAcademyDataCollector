import requests
import os
import json
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse
from datetime import datetime
from dateutil import parser
import teacher_data #A file with all the credentials, a blank template is in the repository

canvas_domain = "https://pasadena.instructure.com"
course_domain = f"{canvas_domain}/api/v1/courses"

access_token = teacher_data.access_token
course_ids = teacher_data.course_ids
sitework_group_ids = teacher_data.sitework_group_ids
class_ids = teacher_data.class_IDs
cookies = teacher_data.cookies

#UPDATE
semester = 5

canvas_headers = {"Authorization": f"Bearer {access_token}"}
ma_headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)`1 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept":"text/html,application/json"
}

#Prints the Group IDS to use for the new Assignment creation
def assignment_group_ids(grade): 
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
    json.dump(roster, open('canvas_roster_'+str(grade)+'.json','w'), indent=4)

#Converts Last, First format of name to First Last
#MA uses Last, First. Canvas uses First Last
def normalize_name(name):
    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        return f"{first} {last}"
    else:
        return name

#Creates a weekly homework assignment with a specified index, date, and number of points
#Date is actually the day after it is meant to be due because of time change
def create_homework_assignment(grade, weekNumber, date, points):
    course_id = course_ids[grade]
    url = f'{course_domain}/{course_id}/assignments'
    payload = {
        "assignment": {
            "name": "Weekly XP " + str(weekNumber),
            "description": "Weekly Assignment Made using API.",
            "submission_types":["none"],
            "points_possible": points,
            "grading_type": "points",
            "due_at": date+"T06:59:00Z",
            "published": True,
            "post_to_sis": True,
            "assignment_group_id": sitework_group_ids[grade]
        }
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

#Returns an array of assignment dictionaries with keys
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
        file = open('canvas_scores_'+str(grade)+'.json','r')
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
    json.dump(all_scores, open('canvas_scores_'+str(grade)+'.json','w'), indent = 4)

#Creates and saves to a JSON file a dictionary of name:student_id
def pull_math_academy_roster(grade):
    if grade == None:
        for grade_level in class_ids:
            pull_math_academy_roster(grade_level)
        return
    class_id = class_ids[grade]
    url = f"https://mathacademy.com/classes/{class_id}"
    response = requests.get(url,headers=ma_headers,cookies=cookies)
    soup = BeautifulSoup(response.text, "lxml")
    table = soup.find(id = "students")
    data = [row.find_all("td") for row in table.find_all("tr")]
    roster = {}
    for student in data[1:]:
        student_url = student[0].find('a').get('href')
        parts = urlparse(student_url).path.split('/')
        student_id = parts[-2]
        student_name = normalize_name(student[0].get_text(strip=True))
        roster[student_name]=student_id
    json.dump(roster, open("MA_Roster_"+str(grade)+".json","w"), indent = 4)
    

#Pulls the data from the activity page of a student
def pull_math_academy_assignment_data(grade = None, student = None):
    if grade == None:
        for grade_level in class_ids:
            pull_math_academy_assignment_data(grade_level, student)
        return
    class_id = class_ids[grade]
    roster = json.load(open("MA_Roster_"+str(grade)+".json","r"))
    if student == None:
        for name in roster:
            pull_math_academy_assignment_data(grade, name)
            print(f"Pulled {name} assignment data")
        return
    url = f"https://mathacademy.com/classes/{class_id}/students/{roster[student]}/activity"
    response = requests.get(url,headers=ma_headers,cookies=cookies)
    soup = BeautifulSoup(response.text, "lxml")
    task_table = soup.find_all('table')[5]
    task_rows = task_table.find_all('tr')
    tasks = {}
    try: #We need to load old tasks so they aren't forgotten/hidden
        with open(student+"_Task_List.json",'r') as file:
            prior_tasks = json.load(file)
    except FileNotFoundError:
        prior_tasks = {}
    date = None
    for task_row in task_rows:
        if task_row.find(class_='dateHeader') != None:
            new_date = task_row.find(class_='dateHeader').text.split('\n')[2].strip()
            if date != None and parser.parse(date) < parser.parse(new_date):
                break
            else:
                date = task_row.find(class_='dateHeader').text.split('\n')[2].strip()
        elif date != None:
            task_id = task_row.get('id').split('-')[1]
            if '/' in task_row.find(class_='taskPointsColumn').text:
                points = int(task_row.find(class_='taskPointsColumn').text.strip().split('/')[0])
            else:
                points = int(task_row.find(class_='taskPointsColumn').text.strip().split(' ')[0])
            tasks[task_id] = {'points':points, 'date':date}
    for task in prior_tasks:
        if task not in tasks:
            tasks[task] = prior_tasks[task]
    with open(student+"_Task_List.json",'w') as file:
        json.dump(tasks,file, indent = 4)

#In Progress
#Computes points per week and updates them
def update_xp_scores(grade = None, canvas_id = None, with_refresh = True, update_after = True):
    if grade == None:
        for grade in course_ids:
            update_xp_scores(grade, canvas_id, with_refresh, update_after)
        return
    if canvas_id == None:
        print(f"Updating {grade}th grade class")
        for canvas_id in canvas_roster[grade]:
            update_xp_scores(grade, canvas_id, with_refresh, False)
            print(f"{canvas_roster[grade][canvas_id]} updated")
        if update_after:
            save_canvas_scores(grade)
            print("Saved Scores Updated")
        return
    course_id = course_ids[grade]
    name = canvas_roster[grade][canvas_id]
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
        if (len(assignment['name']) > 10 and
            assignment['name'][:10] == 'Weekly XP '):
            week = int(assignment['name'][10:])
            assignment_id = str(assignment['id'])
            if (week not in exceptions and
                week in points.keys() and
                needs_update(prior_scores[assignment_id],points[week])):
                homeworks.append(assignment)   
    for assignment in homeworks:
        week = int(assignment['name'][10:])
        assignment_id = str(assignment['id'])
        if (week < len(points) and
            needs_update(prior_scores[assignment_id],points[week])):
            if prior_scores[assignment_id] == None:
                update = 'y'
            else:
                update = input(f"Update {name} score in week {week} from { prior_scores[assignment_id]} to {points[week]}? (y/n)")
            if update == 'y':
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
                    print(f"Updated {assignment_id} - {name}:{prior_scores[assignment_id]}->{points[week]}")
    if update_after:
        save_canvas_scores(grade)
        print("Saved Scores Updated")
    

#XP beyond 200 is supposed to count half, so points beyond 5 are half
def apply_extra_credit_discount(points):
    for week in range(len(points)):
        if points[week] > 5:
            points[week] = 5+(points[week]-5)/2
    return

#Looks at the list of tasks and determines the number of xp in each week
def weekly_total_xp(student_name):
    start_date = datetime(2025,8,11) #Represents one week before, so week 0 is all of summer
    today = datetime.today()
    with open(student_name+"_Task_List.json",'r') as file:
        tasks = json.load(file)
    xp_totals = [0 for week in range(1+(today-start_date).days//7)]
    for task in tasks.values():
        date = parser.parse(task['date'])
        if date > datetime.today():
            date = date.replace(year = 2024)
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

#Loads data which is called for multiple times at file run
try:
    canvas_roster = {}
    for grade in course_ids:
        with open(f'canvas_roster_{grade}.json','r') as file:
            canvas_roster[grade] = json.load(file)
except FileNotFoundError:
    update_canvas_roster(None)
try:
    canvas_scores = {}
    for grade in course_ids:
        with open(f'canvas_scores_{grade}.json','r') as file:
            canvas_scores[grade] = json.load(file)
except FileNotFoundError:
    save_canvas_scores(None)

