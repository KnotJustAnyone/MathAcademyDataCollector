import requests #For interfacing with websites
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from dateutil import parser
import teacher_data #A file with all the credentials, a blank template is in the repository

debug_mode = False

#localize imported data
class_ids = teacher_data.class_IDs
cookies = teacher_data.cookies

#UPDATE - Represents last digit of year
semester = 6

#Headers for the web requests
ma_headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)`1 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept":"text/html,application/json"
}

#Set the directories
data_dir = Path(__file__).resolve().parent/"data"
data_dir.mkdir(exist_ok=True)
rosters_dir = data_dir/"rosters"
rosters_dir.mkdir(exist_ok=True)
scores_dir = data_dir/"scores"
scores_dir.mkdir(exist_ok=True)
tasks_dir = data_dir/"task_data"
tasks_dir.mkdir(exist_ok=True)

def normalize_name(name):
    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        return f"{first} {last}"
    else:
        return name

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
        student = student[0].find_all("div")
        student_name = normalize_name(student[0].get_text(strip=True))
        xp_url = f"https://www.mathacademy.com/students/{student_id}/settings/xp-goals"
        xp_response = requests.get(xp_url,headers=ma_headers,cookies=cookies)
        xp_soup = BeautifulSoup(xp_response.text, "lxml")
        xp_table = xp_soup.find(id = "xpGoals")
        xp_data = [row.find('input').get('value') for row in xp_table.find_all("tr")[1].find_all("td")]
        roster[student_name]=[student_id,sum(int(xp) for xp in xp_data)]
    json.dump(roster, open(rosters_dir/("MA_Roster_"+str(grade)+".json"),"w"), indent = 4)
    

#Pulls the data from the activity page of a student
def pull_math_academy_assignment_data(grade = None, student = None):
    if grade == None:
        for grade_level in class_ids:
            pull_math_academy_assignment_data(grade_level, student)
        return
    class_id = class_ids[grade]
    if debug_mode:
        print(f"class_id = {class_id}")
    pull_math_academy_roster(grade)
    roster = json.load(open(rosters_dir/("MA_Roster_"+str(grade)+".json"),"r"))
    if student == None:
        for name in roster:
            pull_math_academy_assignment_data(grade, name[0])
            print(f"Pulled {name[0]} assignment data")
        return
    url = f"https://mathacademy.com/classes/{class_id}/students/{roster[student][0]}/activity"
    response = requests.get(url,headers=ma_headers,cookies=cookies)
    if response.status_code != 200:
        print(f"Response Code Problem: {response.status_code}")
        exit()
    soup = BeautifulSoup(response.text, "lxml")
    tables = soup.find_all('table')
    task_table = None
    for table in tables:
        if len(table.find_all('tr')) > 20:
            task_table = table
    if not task_table:
        print("Error, no table long enough to be task table")
        exit()
    task_rows = task_table.find_all('tr')
    tasks = process_task_list(task_rows) #loads all currently visible tasks
    try: #Loads old tasks in case they fell off the bottom of the site
        with open(tasks_dir/(student+"_Task_List.json"),'r') as file:
            prior_tasks = json.load(file)
    except FileNotFoundError:
        prior_tasks = {}
    for task in prior_tasks:
        if task not in tasks:
            tasks[task] = prior_tasks[task]
    with open(tasks_dir/(student+"_Task_List.json"),'w') as file:
        json.dump(tasks,file, indent = 4)

#Adds tasks from the task_rows to tasks, breaking at the new year.
def process_task_list(task_rows):
    tasks = {}
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
    return tasks

def weekly_total_xp(student_name):
    start_date = datetime(2026,8,17) #Represents one week before, so week 0 is all of summer
    today = datetime.today()
    with open(tasks_dir/(student_name+"_Task_List.json"),'r') as file:
        tasks = json.load(file)
    xp_totals = [0 for week in range(1+(today-start_date).days//7)]
    print(today-start_date)
    for task in tasks:
        date = parser.parse(task['date'])
        if date > datetime.today():
            date = date.replace(year = 2025)
        week = (date-start_date).days//7
        if week < 0:
            week = 0
        xp_totals[week] += task['points']
    return xp_totals

def get_xp_totals(grade=None):
    if grade == None:
        for grade in class_ids:
            get_xp_totals(grade)
        return
    roster = json.load(open(rosters_dir/("MA_Roster_"+str(grade)+".json"),"r"))
    scores = dict()
    for student in roster:
        try:
            scores[student] = weekly_total_xp(student)
        except ValueError:
            print(student)
    json.dump(scores, open(scores_dir/("MA_Scores_"+str(grade)+".json"),"w"), indent = 4)

